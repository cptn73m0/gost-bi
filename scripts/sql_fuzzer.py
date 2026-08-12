"""
SQL Fuzzer — generates random SQL and verifies it doesn't crash the system.

Level 4: Property-based testing extension. Runs in nightly CI.
"""

from __future__ import annotations

import argparse
import logging
import random
import string
import sys
import time
from dataclasses import dataclass

logger = logging.getLogger("gost_bi.quality.sql_fuzzer")


@dataclass
class FuzzResult:
    iteration: int
    sql: str
    passed: bool
    error: str = ""
    duration_ms: float = 0


class SQLFuzzer:
    TABLES = ["users", "orders", "products", "sales", "inventory", "employees", "departments"]
    COLUMNS = {
        "users": ["id", "name", "email", "created_at", "active", "region_id"],
        "orders": ["id", "user_id", "product_id", "amount", "quantity", "date", "status"],
        "products": ["id", "name", "price", "category_id", "in_stock"],
        "sales": ["id", "product_id", "region_id", "revenue", "units", "date"],
        "inventory": ["id", "product_id", "warehouse_id", "quantity", "updated_at"],
        "employees": ["id", "name", "department_id", "salary", "hire_date"],
        "departments": ["id", "name", "manager_id", "budget"],
    }
    AGG_FUNCS = ["COUNT", "SUM", "AVG", "MIN", "MAX"]
    OPERATORS = ["=", ">", "<", ">=", "<=", "!=", "LIKE", "IN", "BETWEEN"]

    def generate_select(self) -> str:
        table = random.choice(self.TABLES)
        cols = self.COLUMNS[table]

        if random.random() < 0.3:
            select_cols = "*"
        elif random.random() < 0.3:
            func = random.choice(self.AGG_FUNCS)
            col = random.choice(cols)
            select_cols = f"{func}({col})"
        else:
            n = random.randint(1, min(3, len(cols)))
            select_cols = ", ".join(random.sample(cols, n))

        sql = f"SELECT {select_cols} FROM {table}"

        if random.random() < 0.4:
            where_clause = self._generate_where(table)
            sql += f" WHERE {where_clause}"

        if random.random() < 0.2 and select_cols != "*":
            group_col = random.choice([c for c in cols if c != "id"])
            sql += f" GROUP BY {group_col}"

        if random.random() < 0.2 and "COUNT" in select_cols or "SUM" in select_cols:
            sql += f" HAVING {random.choice(self.AGG_FUNCS)}({random.choice(cols)}) > {random.randint(1, 1000)}"

        if random.random() < 0.3:
            sql += f" ORDER BY {random.choice(cols)} {'ASC' if random.random() < 0.5 else 'DESC'}"

        if random.random() < 0.3:
            sql += f" LIMIT {random.randint(1, 100)}"

        return sql

    def _generate_where(self, table: str) -> str:
        cols = self.COLUMNS[table]
        col = random.choice(cols)
        op = random.choice(self.OPERATORS)

        if op == "BETWEEN":
            return f"{col} BETWEEN {random.randint(1, 100)} AND {random.randint(101, 1000)}"
        elif op == "IN":
            values = ", ".join(str(random.randint(1, 100)) for _ in range(random.randint(2, 5)))
            return f"{col} IN ({values})"
        elif op == "LIKE":
            return f"{col} LIKE '%{random.choice(string.ascii_lowercase)}%'"
        else:
            if col in ("name", "email", "status"):
                return f"{col} {op} '{random.choice(string.ascii_lowercase)}'"
            return f"{col} {op} {random.randint(1, 1000)}"

    def fuzz(self, iterations: int = 1000, timeout: int = 1800) -> list[FuzzResult]:
        from gost_bi.quality.sql_verifier import SQLVerifier

        verifier = SQLVerifier()
        results: list[FuzzResult] = []
        deadline = time.monotonic() + timeout

        for i in range(iterations):
            if time.monotonic() > deadline:
                logger.warning(f"Timeout reached at iteration {i}/{iterations}")
                break

            sql = self.generate_select()
            start = time.perf_counter()
            report = verifier.verify(sql)
            duration_ms = (time.perf_counter() - start) * 1000

            result = FuzzResult(
                iteration=i,
                sql=sql,
                passed=report.overall_passed,
                error="; ".join(c.message for c in report.checks if not c.passed),
                duration_ms=duration_ms,
            )
            results.append(result)

            if not result.passed:
                logger.error(f"Fuzz failure [{i}]: {sql[:120]} → {result.error}")

        return results


def main() -> int:
    parser = argparse.ArgumentParser(description="SQL Fuzzer — Level 4")
    parser.add_argument("--iterations", type=int, default=1000, help="Number of fuzz iterations")
    parser.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds")
    parser.add_argument("--db", type=str, help="Database URL for EXPLAIN checks")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fuzzer = SQLFuzzer()
    results = fuzzer.fuzz(iterations=args.iterations, timeout=args.timeout)

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    logger.info(f"Fuzzing complete: {total} iterations, {passed} passed, {failed} failed")

    if failed > 0:
        logger.error(f"SQL Fuzzer found {failed} issues — check logs above")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
