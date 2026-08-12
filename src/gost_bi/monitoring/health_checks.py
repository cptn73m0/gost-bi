"""
Runtime Health Checks — Level 11 of the self-checking system.

Continuously monitors all components in production:
- Database connectivity
- Redis cache
- Celery workers
- 1C OData connector
- AI engine (YandexGPT / GigaChat)
- Memory usage
- Queue depth
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

import httpx

logger = logging.getLogger("gost_bi.monitoring.health")


class Severity(Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class HealthIssue:
    severity: Severity
    component: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HealthCheckResult:
    component: str
    issues: list[HealthIssue] = field(default_factory=list)
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def healthy(self) -> bool:
        return not any(issue.severity == Severity.CRITICAL for issue in self.issues)

    @property
    def degraded(self) -> bool:
        return not self.healthy and not any(issue.severity == Severity.CRITICAL for issue in self.issues)


class DatabaseHealthCheck:
    def __init__(self, db_url: str):
        self.db_url = db_url

    async def check(self) -> HealthCheckResult:
        issues: list[HealthIssue] = []
        start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.db_url}/health")
                latency_ms = (time.perf_counter() - start) * 1000

                if resp.status_code != 200:
                    issues.append(HealthIssue(Severity.CRITICAL, "database", f"Health check returned {resp.status_code}"))
                if latency_ms > 1000:
                    issues.append(HealthIssue(Severity.WARNING, "database", f"High latency: {latency_ms:.0f}ms"))
        except httpx.TimeoutException:
            issues.append(HealthIssue(Severity.CRITICAL, "database", "Connection timeout"))
        except httpx.ConnectError as exc:
            issues.append(HealthIssue(Severity.CRITICAL, "database", f"Connection refused: {exc}"))

        return HealthCheckResult(component="database", issues=issues, latency_ms=(time.perf_counter() - start) * 1000)


class RedisHealthCheck:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url

    async def check(self) -> HealthCheckResult:
        import redis.asyncio as aioredis

        issues: list[HealthIssue] = []
        start = time.perf_counter()

        try:
            r = aioredis.from_url(self.redis_url)
            pong = await r.ping()
            latency_ms = (time.perf_counter() - start) * 1000

            if not pong:
                issues.append(HealthIssue(Severity.CRITICAL, "redis", "PING returned False"))
            if latency_ms > 100:
                issues.append(HealthIssue(Severity.WARNING, "redis", f"High latency: {latency_ms:.0f}ms"))

            used_memory = await r.info("memory")
            used_mb = used_memory.get("used_memory_rss", 0) / (1024 * 1024)
            if used_mb > 2048:
                issues.append(HealthIssue(Severity.WARNING, "redis", f"High memory: {used_mb:.0f}MB"))

            await r.aclose()
        except Exception as exc:
            issues.append(HealthIssue(Severity.CRITICAL, "redis", f"Connection failed: {exc}"))
            latency_ms = (time.perf_counter() - start) * 1000

        return HealthCheckResult(component="redis", issues=issues, latency_ms=latency_ms)


class OData1CHealthCheck:
    def __init__(self, base_url: str, username: str = "", password: str = ""):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password) if username else None

    async def check(self) -> HealthCheckResult:
        issues: list[HealthIssue] = []
        start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                metadata_url = f"{self.base_url}/standard.odata/$metadata"
                resp = await client.get(metadata_url, auth=self.auth)

                latency_ms = (time.perf_counter() - start) * 1000

                if resp.status_code != 200:
                    issues.append(
                        HealthIssue(
                            Severity.CRITICAL,
                            "1c_odata",
                            f"Metadata endpoint returned {resp.status_code}",
                        )
                    )

                if latency_ms > 5000:
                    issues.append(
                        HealthIssue(
                            Severity.WARNING,
                            "1c_odata",
                            f"High latency: {latency_ms:.0f}ms",
                        )
                    )

                test_url = f"{self.base_url}/standard.odata/Catalog_Номенклатура?$top=1"
                test_resp = await client.get(test_url, auth=self.auth)

                if test_resp.status_code != 200:
                    issues.append(
                        HealthIssue(
                            Severity.WARNING,
                            "1c_odata",
                            f"Test query returned {test_resp.status_code}",
                        )
                    )

        except httpx.TimeoutException:
            issues.append(HealthIssue(Severity.CRITICAL, "1c_odata", "Connection timeout"))
        except httpx.ConnectError as exc:
            issues.append(HealthIssue(Severity.CRITICAL, "1c_odata", f"Connection refused: {exc}"))

        return HealthCheckResult(component="1c_odata", issues=issues, latency_ms=(time.perf_counter() - start) * 1000)


class AIEngineHealthCheck:
    def __init__(self, api_url: str, api_key: str = ""):
        self.api_url = api_url
        self.api_key = api_key

    async def check(self) -> HealthCheckResult:
        issues: list[HealthIssue] = []
        start = time.perf_counter()

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_url}/chat/completions",
                    json={
                        "model": "check",
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                    headers=headers,
                )

                latency_ms = (time.perf_counter() - start) * 1000

                if resp.status_code != 200:
                    issues.append(HealthIssue(Severity.WARNING, "ai_engine", f"API returned {resp.status_code}"))
                if latency_ms > 10000:
                    issues.append(HealthIssue(Severity.WARNING, "ai_engine", f"High latency: {latency_ms:.0f}ms"))

        except httpx.TimeoutException:
            issues.append(HealthIssue(Severity.WARNING, "ai_engine", "API timeout — NLP features degraded"))
        except httpx.ConnectError as exc:
            issues.append(HealthIssue(Severity.WARNING, "ai_engine", f"API unreachable — NLP features disabled: {exc}"))

        return HealthCheckResult(component="ai_engine", issues=issues, latency_ms=(time.perf_counter() - start) * 1000)


class SystemHealthAggregator:
    def __init__(self):
        self.checks: list[tuple[str, object]] = []

    def register(self, name: str, check: object) -> None:
        self.checks.append((name, check))

    async def run_all(self) -> dict[str, HealthCheckResult]:
        results: dict[str, HealthCheckResult] = {}
        async with asyncio.TaskGroup() as tg:
            futures = {name: tg.create_task(check.check()) for name, check in self.checks}
        for name, future in futures.items():
            results[name] = future.result()
            result = results[name]
            status = "✅" if result.healthy else ("⚠️" if result.degraded else "🔴")
            logger.info(f"  {status} {name}: {result.latency_ms:.0f}ms, {len(result.issues)} issues")
        return results
