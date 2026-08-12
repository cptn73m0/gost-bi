"""
GOST BI NLP→SQL Accuracy Benchmark v2.

Runs all 50 test queries against the enhanced pipeline.
Measures: syntax validity, table match, keyword match, overall accuracy.

Target: >95%
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("gost_bi.nlp.benchmark")


@dataclass
class QueryResult:
    query_id: str
    text: str
    generated_sql: str
    expected: dict[str, Any]
    syntax_ok: bool
    table_ok: bool
    keywords_ok: bool
    must_have_ok: bool
    must_not_ok: bool
    confidence: float
    retries: int
    fixes: list[str]
    errors: list[str]

    @property
    def passed(self) -> bool:
        return all([self.syntax_ok, self.table_ok, self.keywords_ok, self.must_have_ok, self.must_not_ok])


@dataclass
class BenchmarkReport:
    total: int
    passed: int
    query_results: list[QueryResult] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    @property
    def syntax_errors(self) -> int:
        return sum(1 for r in self.query_results if not r.syntax_ok)

    @property
    def table_errors(self) -> int:
        return sum(1 for r in self.query_results if not r.table_ok)

    @property
    def keyword_errors(self) -> int:
        return sum(1 for r in self.query_results if not r.keywords_ok)

    def fail_details(self) -> list[str]:
        lines: list[str] = []
        for r in self.query_results:
            if not r.passed:
                fails = []
                if not r.syntax_ok: fails.append("syntax")
                if not r.table_ok: fails.append("table")
                if not r.keywords_ok: fails.append("keywords")
                if not r.must_have_ok: fails.append("must_have")
                if not r.must_not_ok: fails.append("must_not")
                lines.append(f"  [{r.query_id}] {r.text[:70]} — {', '.join(fails)}")
                if r.generated_sql:
                    lines.append(f"    SQL: {r.generated_sql[:120]}")
                if r.errors:
                    lines.append(f"    Errors: {r.errors}")
                if r.fixes:
                    lines.append(f"    Fixes applied: {r.fixes}")
        return lines


def evaluate_query(sql: str, expected: dict[str, Any]) -> tuple[bool, bool, bool, bool, bool, list[str]]:
    sql_upper = sql.upper()
    errors: list[str] = []

    syntax_ok = True
    try:
        import sqlglot
        sqlglot.parse_one(sql, dialect="postgres")
    except Exception as exc:
        syntax_ok = False
        errors.append(f"Syntax: {exc}")

    expected_table = expected.get("table", "")
    table_ok = expected_table.lower() in sql.lower()
    if not table_ok:
        errors.append(f"Table '{expected_table}' not found in SQL")

    keywords = expected.get("keywords", [])
    keyword_checks = [(kw.upper() in sql_upper) for kw in keywords]
    keywords_ok = all(keyword_checks)
    if not keywords_ok:
        missing = [kw for kw, ok in zip(keywords, keyword_checks) if not ok]
        errors.append(f"Missing keywords: {missing}")

    must_have = expected.get("must_have", [])
    must_have_ok = all(mh.upper() in sql_upper for mh in must_have)
    if not must_have_ok:
        missing = [mh for mh in must_have if mh.upper() not in sql_upper]
        errors.append(f"Must have missing: {missing}")

    must_not = expected.get("must_not", [])
    must_not_ok = not any(mn.upper() in sql_upper for mn in must_not)
    if not must_not_ok:
        found = [mn for mn in must_not if mn.upper() in sql_upper]
        errors.append(f"Forbidden found: {found}")

    return syntax_ok, table_ok, keywords_ok, must_have_ok, must_not_ok, errors


async def run_benchmark() -> BenchmarkReport:
    from gost_bi.nlp.pipeline_v2 import ENRICHED_SCHEMA
    from gost_bi.nlp.pipeline_v2_1 import SmartMockProviderV2, NLPToSQLPipelineV2_1
    from gost_bi.nlp.benchmark_queries import QUERIES_V1

    provider = SmartMockProviderV2()
    pipeline = NLPToSQLPipelineV2_1(provider)

    results: list[QueryResult] = []
    start = time.perf_counter()

    for query in QUERIES_V1:
        result = await pipeline.execute(query["text"], ENRICHED_SCHEMA, verify=True)

        syntax_ok, table_ok, keywords_ok, must_have_ok, must_not_ok, errors = evaluate_query(
            result.generated_sql, query
        )

        qr = QueryResult(
            query_id=query["id"],
            text=query["text"],
            generated_sql=result.generated_sql,
            expected=query,
            syntax_ok=syntax_ok,
            table_ok=table_ok,
            keywords_ok=keywords_ok,
            must_have_ok=must_have_ok,
            must_not_ok=must_not_ok,
            confidence=result.confidence,
            retries=result.retry_count,
            fixes=result.errors_fixed,
            errors=errors,
        )
        results.append(qr)

    elapsed = (time.perf_counter() - start) * 1000
    passed = sum(1 for r in results if r.passed)

    return BenchmarkReport(
        total=len(QUERIES_V1),
        passed=passed,
        query_results=results,
        total_time_ms=elapsed,
    )


def main() -> int:
    report = asyncio.run(run_benchmark())

    print()
    print("=" * 56)
    print("  GOST BI - NLP to SQL Accuracy Benchmark v2.1")
    print("=" * 56)
    print()

    for r in report.query_results:
        status = "+" if r.passed else "X"
        conf_pct = int(r.confidence * 100)
        print(f"  [{status}] {r.query_id} {r.text[:64]} ({conf_pct}%)")
        if not r.passed:
            print(f"         SQL: {r.generated_sql[:100]}")
            for e in r.errors:
                print(f"         ERR: {e}")
            for f in r.fixes:
                print(f"         FIX: {f}")

    print()
    print(f"  Accuracy: {report.passed}/{report.total} ({report.accuracy:.1%})")
    print(f"  Syntax errors: {report.syntax_errors}")
    print(f"  Table mismatches: {report.table_errors}")
    print(f"  Keyword misses: {report.keyword_errors}")
    print(f"  Time: {report.total_time_ms:.0f} ms")
    print()

    if report.accuracy >= 0.95:
        print(f"  [PASS] Target 95%+ met: {report.accuracy:.1%}")
        return 0
    elif report.accuracy >= 0.90:
        print(f"  [WARN] Above 90% but below 95%: {report.accuracy:.1%}")
        return 0
    else:
        print(f"  [FAIL] Below 90%: {report.accuracy:.1%}")
        print()
        for line in report.fail_details():
            print(line)
        return 1


if __name__ == "__main__":
    sys.exit(main())
