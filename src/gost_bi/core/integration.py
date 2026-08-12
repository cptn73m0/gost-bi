"""
Superset ↔ GOST BI Integration Layer.

Bridges our self-checking system (Levels 0-12) into the Superset runtime.
Hooks into Superset's SQL execution pipeline to validate AI-generated queries.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("gost_bi.core.integration")


class SupersetSQLInterceptor:
    """
    Intercepts SQL execution in Superset and runs GOST BI verification.

    Hooks into: superset.sql_lab.execute_sql_statements
    Validates: syntax, injections, destructive ops before execution.
    """

    def __init__(self) -> None:
        self._original_execute: Callable[..., Any] | None = None
        self.enabled: bool = True

    def install(self) -> None:
        try:
            from superset.sql_lab import sqllab_execution_context

            self._original_execute = sqllab_execution_context.SqlLabExecutionContext.execute
        except ImportError:
            logger.warning("Superset not installed — SQL interceptor skipped")
            return

        from gost_bi.quality.sql_verifier import SQLVerifier

        verifier = SQLVerifier()

        def verified_execute(self_context: Any, *args: Any, **kwargs: Any) -> Any:
            sql = kwargs.get("sql", "") or (args[0] if args else "")

            if sql and self.enabled if hasattr(self, "enabled") else True:
                report = verifier.verify(sql, nlp_input=getattr(self_context, "nlp_input", None))
                report.log()

                if not report.overall_passed:
                    for check in report.checks:
                        if not check.passed:
                            logger.error(f"SQL blocked: [{check.name}] {check.message}")
                    raise RuntimeError(
                        f"GOST BI SQL Verifier blocked query: "
                        f"{'; '.join(c.message for c in report.checks if not c.passed)}"
                    )

            return self._original_execute(self_context, *args, **kwargs) if self._original_execute else None

        sqllab_execution_context.SqlLabExecutionContext.execute = verified_execute
        logger.info("✅ GOST BI SQL interceptor installed in Superset")


class SupersetHealthCheckRegistry:
    """Registers GOST BI health checks into Superset's health endpoint."""

    @staticmethod
    def register(aggregator: Any) -> None:
        try:
            from superset.views.health import Health

            original_check = Health.check

            async def enhanced_check(self: Any) -> dict[str, Any]:
                base = await original_check(self)
                gost_checks = await aggregator.run_all()
                base["gost_bi"] = {
                    component: {
                        "healthy": result.healthy,
                        "latency_ms": result.latency_ms,
                        "issues": len(result.issues),
                    }
                    for component, result in gost_checks.items()
                }
                return base

            Health.check = enhanced_check
            logger.info("✅ GOST BI health checks registered in Superset")

        except ImportError:
            logger.warning("Superset not installed — health check integration skipped")


def install_all_hooks() -> dict[str, bool]:
    """Install all GOST BI hooks into Superset. Returns status for each hook."""
    results: dict[str, bool] = {}

    try:
        SQLInterceptor().install()
        results["sql_interceptor"] = True
    except Exception as exc:
        logger.error(f"SQL interceptor failed: {exc}")
        results["sql_interceptor"] = False

    return results
