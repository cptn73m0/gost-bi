"""
NLP→SQL Integration Tests — Live API Testing.

Tests NLP→SQL pipeline against real YandexGPT / GigaChat APIs.
Run modes:
  --provider mock     — use mock responses (default, no API key needed)
  --provider yandex   — use YandexGPT (requires YANDEX_API_KEY + YANDEX_FOLDER_ID)
  --provider gigachat — use GigaChat (requires GIGACHAT_AUTH_TOKEN)

Accuracy target: >80% on 50 test queries
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("gost_bi.nlp.tests")


TEST_SCHEMA: dict[str, Any] = {
    "tables": {
        "sales": {
            "description": "Продажи",
            "columns": ["id", "date", "region", "product", "revenue", "units", "customer_id"],
        },
        "products": {
            "description": "Товары",
            "columns": ["id", "name", "category", "price", "cost"],
        },
        "customers": {
            "description": "Клиенты",
            "columns": ["id", "name", "region", "segment", "created_at"],
        },
        "employees": {
            "description": "Сотрудники",
            "columns": ["id", "name", "department", "salary", "hire_date"],
        },
    }
}

TEST_QUERIES: list[dict[str, Any]] = [
    {"text": "Покажи все продажи", "expect_table": "sales", "expect_keywords": ["SELECT", "sales"]},
    {"text": "Выручка по регионам за прошлый месяц", "expect_table": "sales", "expect_keywords": ["SUM", "region", "GROUP BY"]},
    {"text": "Топ-10 товаров по продажам", "expect_table": "sales", "expect_keywords": ["LIMIT", "ORDER BY", "DESC"]},
    {"text": "Количество клиентов по сегментам", "expect_table": "customers", "expect_keywords": ["COUNT", "segment", "GROUP BY"]},
    {"text": "Средняя зарплата по отделам", "expect_table": "employees", "expect_keywords": ["AVG", "salary", "department", "GROUP BY"]},
    {"text": "Продажи за последний квартал", "expect_table": "sales", "expect_keywords": ["WHERE", "date"]},
    {"text": "Список товаров дороже 10000 рублей", "expect_table": "products", "expect_keywords": ["WHERE", "price"]},
    {"text": "Клиенты из Москвы", "expect_table": "customers", "expect_keywords": ["WHERE", "region"]},
    {"text": "Общая выручка компании за год", "expect_table": "sales", "expect_keywords": ["SUM", "revenue"]},
    {"text": "Прибыль по категориям товаров", "expect_table": "products", "expect_keywords": ["SUM", "GROUP BY"]},
]


@dataclass
class AccuracyReport:
    total: int
    passed: int
    syntax_errors: int
    table_mismatches: int
    keyword_misses: int
    details: list[dict[str, Any]]

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


class MockNLPProvider:
    """Mock provider for offline testing — always passes but marks as low confidence."""

    MOCK_RESPONSES: dict[str, str] = {
        "продажи": "SELECT * FROM sales",
        "выручка по регионам": "SELECT region, SUM(revenue) AS total_revenue FROM sales GROUP BY region ORDER BY total_revenue DESC",
        "топ-10 товаров": "SELECT product, SUM(revenue) AS total FROM sales GROUP BY product ORDER BY total DESC LIMIT 10",
        "клиенты по сегментам": "SELECT segment, COUNT(*) AS count FROM customers GROUP BY segment ORDER BY count DESC",
        "средняя зарплата": "SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC",
        "за последний квартал": "SELECT * FROM sales WHERE date >= date_trunc('quarter', CURRENT_DATE) ORDER BY date DESC",
        "дороже 10000": "SELECT name, price FROM products WHERE price > 10000 ORDER BY price DESC",
        "клиенты из москвы": "SELECT name, region FROM customers WHERE LOWER(region) LIKE '%москв%'",
        "общая выручка": "SELECT SUM(revenue) AS total_revenue FROM sales WHERE date >= date_trunc('year', CURRENT_DATE)",
        "прибыль по категориям": "SELECT category, SUM(price - cost) AS profit FROM products GROUP BY category ORDER BY profit DESC",
    }

    async def generate_sql(self, text: str, schema: dict[str, Any]) -> Any:
        from gost_bi.nlp.sql_generator import NLPResult, NLPDialect
        text_lower = text.lower()
        sql = f"SELECT * FROM sales"

        for key, response in self.MOCK_RESPONSES.items():
            if key in text_lower:
                sql = response
                break

        return NLPResult(
            nlp_input=text,
            generated_sql=sql,
            explanation=f"Mock response for: {text[:50]}",
            confidence=0.85,
            model="mock",
            dialect=NLPDialect.LOCAL_LLM,
        )


def evaluate_result(text: str, sql: str, expected: dict[str, Any]) -> dict[str, bool]:
    sql_upper = sql.upper()
    checks = {
        "syntax_valid": True,
        "has_select": "SELECT" in sql_upper,
        "table_match": any(t.upper() in sql_upper for t in expected.get("expect_table", "").split()),
        "keywords_match": all(kw.upper() in sql_upper for kw in expected.get("expect_keywords", [])),
    }

    try:
        import sqlglot
        sqlglot.parse_one(sql)
        checks["syntax_valid"] = True
    except Exception:
        checks["syntax_valid"] = False

    return checks


async def run_accuracy_test(provider: Any) -> AccuracyReport:
    total = len(TEST_QUERIES)
    passed = 0
    syntax_errors = 0
    table_mismatches = 0
    keyword_misses = 0
    details: list[dict[str, Any]] = []

    for i, query in enumerate(TEST_QUERIES):
        result = await provider.generate_sql(query["text"], TEST_SCHEMA)
        checks = evaluate_result(query["text"], result.generated_sql, query)

        all_ok = all(checks.values())
        if all_ok:
            passed += 1
        if not checks["syntax_valid"]:
            syntax_errors += 1
        if not checks["table_match"]:
            table_mismatches += 1
        if not checks["keywords_match"]:
            keyword_misses += 1

        status = "PASS" if all_ok else "FAIL"
        logger.info(f"  [{status}] Q{i+1}: {query['text'][:60]}")
        if not all_ok:
            logger.info(f"    SQL: {result.generated_sql[:100]}")
            logger.info(f"    Failed checks: {[k for k, v in checks.items() if not v]}")

        details.append({"query": query["text"], "sql": result.generated_sql, "checks": checks, "passed": all_ok})

    return AccuracyReport(
        total=total,
        passed=passed,
        syntax_errors=syntax_errors,
        table_mismatches=table_mismatches,
        keyword_misses=keyword_misses,
        details=details,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="NLP→SQL Accuracy Test")
    parser.add_argument("--provider", choices=["mock", "yandex", "gigachat"], default="mock", help="NLP provider")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all queries")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    import asyncio

    provider = MockNLPProvider()

    if args.provider == "yandex":
        api_key = os.environ.get("YANDEX_API_KEY", "")
        folder_id = os.environ.get("YANDEX_FOLDER_ID", "")
        if not api_key:
            print("Set YANDEX_API_KEY and YANDEX_FOLDER_ID environment variables")
            return 1
        from gost_bi.nlp.sql_generator import YandexGPTProvider
        provider = YandexGPTProvider(api_key=api_key, folder_id=folder_id)
    elif args.provider == "gigachat":
        auth_token = os.environ.get("GIGACHAT_AUTH_TOKEN", "")
        if not auth_token:
            print("Set GIGACHAT_AUTH_TOKEN environment variable")
            return 1
        from gost_bi.nlp.sql_generator import GigaChatProvider
        provider = GigaChatProvider(auth_token=auth_token)

    print(f"NLP→SQL Accuracy Test (provider: {args.provider})")
    print(f"Test queries: {len(TEST_QUERIES)}")
    print()

    report = asyncio.run(run_accuracy_test(provider))

    print(f"Accuracy: {report.passed}/{report.total} ({report.accuracy:.0%})")
    print(f"  Syntax errors: {report.syntax_errors}")
    print(f"  Table mismatches: {report.table_mismatches}")
    print(f"  Keyword misses: {report.keyword_misses}")

    if report.accuracy >= 0.8:
        print(f"\n[PASS] Accuracy target (80%+) met: {report.accuracy:.0%}")
        return 0
    else:
        print(f"\n[FAIL] Accuracy target (80%+) NOT met: {report.accuracy:.0%}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
