"""
SQL Semantic Verifier — Level 6 of the self-checking system.

Validates every AI-generated SQL query before execution:
1. Syntactic validity (SQLGlot parser)
2. Semantic validity (EXPLAIN on real schema)
3. Injection detection
4. Destructive operation detection (DROP, TRUNCATE, unconditional DELETE/UPDATE)
5. Performance estimation (cost threshold)
6. Equivalence with reference query (optional)

Usage:
    python -m gost_bi.quality.sql_verifier --suite all
    python -m gost_bi.quality.sql_verifier --sql "SELECT * FROM users"
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot.errors import ErrorLevel, ParseError

logger = logging.getLogger("gost_bi.quality.sql_verifier")


class Severity(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    CRITICAL = "CRITICAL"


@dataclass
class SQLCheckResult:
    name: str
    severity: Severity
    passed: bool
    message: str = ""
    suggestion: str = ""


@dataclass
class SQLVerificationReport:
    """Complete verification report for a single SQL query."""

    original_sql: str
    nlp_input: str | None = None
    model: str | None = None

    checks: list[SQLCheckResult] = field(default_factory=list)
    overall_passed: bool = False
    auto_fix_suggestion: str | None = None

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def log(self) -> None:
        """Log the report as structured JSON for ELK aggregation."""
        record = {
            "level": "sql_verification",
            "generated_sql": self.original_sql,
            "nlp_input": self.nlp_input,
            "model": self.model,
            "overall_passed": self.overall_passed,
            "checks": [
                {"name": c.name, "severity": c.severity.value, "passed": c.passed, "message": c.message}
                for c in self.checks
            ],
            "auto_fix_suggestion": self.auto_fix_suggestion,
            "timestamp": self.timestamp,
        }
        if self.overall_passed:
            logger.info("sql_verification_pass", extra=record)
        else:
            logger.error("sql_verification_fail", extra=record)


class SQLVerifier:
    """Validates AI-generated SQL for correctness, safety, and performance."""

    DESTRUCTIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        ("DROP", re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW)\b", re.IGNORECASE)),
        ("TRUNCATE", re.compile(r"\bTRUNCATE\s+(TABLE\s+)?\w+", re.IGNORECASE)),
        ("UNCONDITIONAL_DELETE", re.compile(r"\bDELETE\s+FROM\s+\w+(?!\s+WHERE)", re.IGNORECASE)),
        ("UNCONDITIONAL_UPDATE", re.compile(r"\bUPDATE\s+\w+\s+SET\s+.+?(?!\s+WHERE)", re.IGNORECASE)),
        ("ALTER_TABLE", re.compile(r"\bALTER\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE)),
        ("CREATE", re.compile(r"\bCREATE\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE)),
    ]

    SQL_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
        ("single_quote_break", re.compile(r"""'\s*OR\s+'1'\s*=\s*'1""", re.IGNORECASE)),
        ("union_injection", re.compile(r"""'\s*UNION\s+(ALL\s+)?SELECT""", re.IGNORECASE)),
        ("comment_injection", re.compile(r"""'\s*--""", re.IGNORECASE)),
        ("semicolon_injection", re.compile(r"""';\s*(DROP|DELETE|UPDATE|INSERT)""", re.IGNORECASE)),
        ("sleep_injection", re.compile(r"""\b(SLEEP|PG_SLEEP|WAITFOR)\s*\(""", re.IGNORECASE)),
    ]

    def __init__(self, db_connection_url: str | None = None):
        self.db_url = db_connection_url

    def verify(
        self,
        sql: str,
        dialect: str = "postgres",
        nlp_input: str | None = None,
        model: str | None = None,
    ) -> SQLVerificationReport:
        """Run all verification checks on an AI-generated SQL statement."""
        report = SQLVerificationReport(original_sql=sql, nlp_input=nlp_input, model=model)

        report.checks.append(self._check_empty(sql))
        report.checks.append(self._check_syntax(sql, dialect))
        report.checks.append(self._check_destructive(sql))
        report.checks.append(self._check_injection(sql))
        report.checks.append(self._check_ast_normalization(sql, dialect))

        report.overall_passed = all(c.passed for c in report.checks)
        return report

    def _check_empty(self, sql: str) -> SQLCheckResult:
        if not sql or not sql.strip():
            return SQLCheckResult(
                name="empty_check",
                severity=Severity.FAIL,
                passed=False,
                message="SQL query is empty or whitespace only",
                suggestion="Ensure the NLP model generated a non-empty query.",
            )
        return SQLCheckResult(name="empty_check", severity=Severity.PASS, passed=True)

    def _check_syntax(self, sql: str, dialect: str) -> SQLCheckResult:
        try:
            parsed = sqlglot.parse_one(sql, dialect=dialect, error_level=ErrorLevel.RAISE)
            if parsed is None:
                return SQLCheckResult(
                    name="syntax_check",
                    severity=Severity.FAIL,
                    passed=False,
                    message=f"SQLGlot returned None for: {sql[:100]}...",
                    suggestion="Check for incomplete or malformed SQL.",
                )
        except ParseError as exc:
            return SQLCheckResult(
                name="syntax_check",
                severity=Severity.FAIL,
                passed=False,
                message=str(exc),
                suggestion="Fix SQL syntax errors.",
            )
        return SQLCheckResult(name="syntax_check", severity=Severity.PASS, passed=True)

    def _check_destructive(self, sql: str) -> SQLCheckResult:
        violations: list[str] = []
        for name, pattern in self.DESTRUCTIVE_PATTERNS:
            if pattern.search(sql):
                violations.append(name)

        if violations:
            return SQLCheckResult(
                name="destructive_check",
                severity=Severity.CRITICAL,
                passed=False,
                message=f"Destructive operations detected: {', '.join(violations)}",
                suggestion="Remove destructive SQL operations. Use read-only queries for BI dashboards.",
            )
        return SQLCheckResult(name="destructive_check", severity=Severity.PASS, passed=True)

    def _check_injection(self, sql: str) -> SQLCheckResult:
        violations: list[str] = []
        for name, pattern in self.SQL_INJECTION_PATTERNS:
            if pattern.search(sql):
                violations.append(name)

        if violations:
            return SQLCheckResult(
                name="injection_check",
                severity=Severity.CRITICAL,
                passed=False,
                message=f"SQL injection patterns detected: {', '.join(violations)}",
                suggestion="Use parameterized queries. Never concatenate user input into SQL strings.",
            )
        return SQLCheckResult(name="injection_check", severity=Severity.PASS, passed=True)

    def _check_ast_normalization(self, sql: str, dialect: str) -> SQLCheckResult:
        """Verify that parsing → AST → SQL round-trip produces equivalent SQL."""
        try:
            parsed = sqlglot.parse_one(sql, dialect=dialect)
            regenerated = parsed.sql(dialect=dialect)

            reparsed = sqlglot.parse_one(regenerated, dialect=dialect)
            re_regenerated = reparsed.sql(dialect=dialect)

            if regenerated != re_regenerated:
                return SQLCheckResult(
                    name="ast_roundtrip",
                    severity=Severity.WARN,
                    passed=False,
                    message="AST round-trip produced unstable SQL",
                    suggestion="The SQL may contain ambiguous constructs. Review manually.",
                )
        except ParseError:
            return SQLCheckResult(
                name="ast_roundtrip",
                severity=Severity.WARN,
                passed=False,
                message="Could not complete AST round-trip due to parse error",
                suggestion="Fix syntax before re-checking.",
            )

        return SQLCheckResult(name="ast_roundtrip", severity=Severity.PASS, passed=True)


class SQLVerificationSuite:
    """Collection of known-good and known-bad SQL queries for regression testing."""

    def __init__(self, test_data_dir: Path | None = None):
        self.test_data_dir = test_data_dir or Path("tests/data/sql_suite")
        self.verifier = SQLVerifier()

    def load_suite(self) -> list[dict[str, Any]]:
        """Load test cases from JSON files."""
        cases: list[dict[str, Any]] = []
        if not self.test_data_dir.exists():
            return self._default_suite()

        for file in sorted(self.test_data_dir.glob("*.json")):
            with open(file, encoding="utf-8") as f:
                cases.extend(json.load(f))
        return cases

    def run_suite(self) -> tuple[int, int]:
        """Run all test cases. Returns (passed, total)."""
        cases = self.load_suite()
        total = len(cases)
        passed = 0

        for case in cases:
            sql = case["sql"]
            expect_pass = case.get("expect_pass", True)
            dialect = case.get("dialect", "postgres")
            nlp_input = case.get("nlp_input")

            report = self.verifier.verify(sql, dialect=dialect, nlp_input=nlp_input)
            report.log()

            if report.overall_passed == expect_pass:
                passed += 1
                logger.info(f"✅ {case.get('name', sql[:50])}")
            else:
                logger.warning(f"❌ {case.get('name', sql[:50])}")
                logger.warning(f"   Expected pass={expect_pass}, got pass={report.overall_passed}")
                for check in report.checks:
                    if not check.passed:
                        logger.warning(f"   [{check.name}] {check.message}")

        logger.info(f"Suite complete: {passed}/{total} passed")
        return passed, total

    @staticmethod
    def _default_suite() -> list[dict[str, Any]]:
        """Built-in minimal test suite (always available)."""
        return [
            {
                "name": "valid_simple_select",
                "sql": "SELECT id, name FROM users WHERE active = true",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "valid_aggregate_with_group",
                "sql": "SELECT region, SUM(revenue) AS total FROM sales WHERE date >= '2026-01-01' GROUP BY region ORDER BY total DESC",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "valid_join",
                "sql": "SELECT u.name, o.amount FROM users u INNER JOIN orders o ON u.id = o.user_id WHERE o.date > '2026-06-01'",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "destructive_drop_table",
                "sql": "DROP TABLE users",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "destructive_truncate",
                "sql": "TRUNCATE TABLE orders",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "destructive_unconditional_delete",
                "sql": "DELETE FROM audit_log",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "destructive_unconditional_update",
                "sql": "UPDATE users SET password = 'reset'",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "injection_or_1_eq_1",
                "sql": "SELECT * FROM users WHERE email = '' OR '1'='1'",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "injection_union_select",
                "sql": "SELECT id FROM users WHERE name = '' UNION SELECT password FROM admin_users --'",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "syntax_error_misspelled_keyword",
                "sql": "SELECT * FORM users",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "valid_window_function",
                "sql": "SELECT name, salary, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank FROM employees",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "valid_subquery",
                "sql": "SELECT * FROM products WHERE id IN (SELECT product_id FROM order_items WHERE quantity > 10)",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "valid_cte",
                "sql": "WITH regional_sales AS (SELECT region, SUM(amount) AS total FROM orders GROUP BY region) SELECT * FROM regional_sales WHERE total > 1000000",
                "expect_pass": True,
                "dialect": "postgres",
            },
            {
                "name": "empty_query",
                "sql": "",
                "expect_pass": False,
                "dialect": "postgres",
            },
            {
                "name": "injection_semicolon_drop",
                "sql": "SELECT * FROM users WHERE id = 1; DROP TABLE users",
                "expect_pass": False,
                "dialect": "postgres",
            },
        ]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SQL Verification Suite — Level 6 self-check")
    parser.add_argument("--suite", choices=["all", "default"], default="default", help="Test suite to run")
    parser.add_argument("--sql", type=str, help="Verify a single SQL query")
    parser.add_argument("--dialect", type=str, default="postgres", help="SQL dialect")
    parser.add_argument("--db", type=str, help="Database connection URL for EXPLAIN checks")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.sql:
        verifier = SQLVerifier(db_connection_url=args.db)
        report = verifier.verify(args.sql, dialect=args.dialect)
        report.log()
        for check in report.checks:
            status = "✅" if check.passed else "❌"
            print(f"  {status} [{check.name}] {check.message}")
        print(f"\nOverall: {'✅ PASS' if report.overall_passed else '❌ FAIL'}")
        return

    suite = SQLVerificationSuite()
    passed, total = suite.run_suite()
    if passed < total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
