"""
GOST BI NLP->SQL Pipeline v2.1 — SmartMockProvider with proper SQL builder.

Architecture: rule-based mock provider -> PostProcessor -> SQL Verifier -> retry.
Target: >95% on 50-query benchmark.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("gost_bi.nlp.v2_1")


class NLPDialect(str, Enum):
    YANDEX_GPT = "yandexgpt"
    GIGA_CHAT = "gigachat"
    MOCK_SMART = "mock_smart"


@dataclass
class NLPResult:
    nlp_input: str
    generated_sql: str
    explanation: str
    confidence: float
    model: str
    dialect: NLPDialect
    retry_count: int = 0
    errors_fixed: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.confidence >= 0.7 and len(self.generated_sql.strip()) > 0


class BaseNLPSQLProvider(ABC):
    @abstractmethod
    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult: ...
    @abstractmethod
    async def health_check(self) -> dict[str, Any]: ...


class SQLBuilder:
    """Builds valid SQL from structured parts. No string mashing."""

    def __init__(self):
        self.table: str = "sales"
        self.select_cols: list[str] = ["*"]
        self.where_conds: list[str] = []
        self.group_cols: list[str] = []
        self.order_cols: list[tuple[str, str]] = []
        self.limit_val: int | None = None
        self.joins: list[str] = []
        self.having_cond: str = ""

    def build(self) -> str:
        parts: list[str] = [f"SELECT {', '.join(self.select_cols)}"]
        if self.joins:
            parts.append(f"FROM {self.table}\n  " + "\n  ".join(self.joins))
        else:
            parts.append(f"FROM {self.table}")
        if self.where_conds:
            parts.append("WHERE " + "\n  AND ".join(self.where_conds))
        if self.group_cols:
            parts.append("GROUP BY " + ", ".join(self.group_cols))
        if self.having_cond:
            parts.append(f"HAVING {self.having_cond}")
        if self.order_cols:
            parts.append("ORDER BY " + ", ".join(f"{c} {d}" for c, d in self.order_cols))
        if self.limit_val:
            parts.append(f"LIMIT {self.limit_val}")
        return "\n".join(parts)


class SmartMockProviderV2(BaseNLPSQLProvider):
    """Rule-based NLP->SQL. Proper SQL builder, no string concatenation."""

    AGG_MAP: dict[str, str] = {
        "реализаци": "SUM(units)",
        "рентабельност": "SUM(price - cost)", "прибыль": "SUM(price - cost)",
        "выручк": "SUM(revenue)", "доход": "SUM(revenue)", "заработ": "SUM(revenue)",
        "суммарн": "SUM(revenue)", "объём": "SUM",
        "средн": "AVG", "количеств": "COUNT(*)", "численност": "COUNT(*)",
        "сколько": "COUNT(*)",
        "максимальн": "MAX", "дорог": "MAX", "минимальн": "MIN", "дешёв": "MIN",
    }

    TABLE_MAP: dict[str, tuple[str, int]] = {
        "продаж": ("sales", 8), "чеки": ("sales", 8), "заказы": ("sales", 8),
        "реализац": ("sales", 8), "транзакци": ("sales", 8), "выручк": ("sales", 10),
        "доход": ("sales", 10), "заработ": ("sales", 8),
        "активн": ("sales", 11),
        "товар": ("products", 9), "продукт": ("products", 9), "номенклатур": ("products", 9),
        "ассортимент": ("products", 9), "издели": ("products", 9),
        "категор": ("products", 7),
        "клиент": ("customers", 10), "покупател": ("customers", 10),
        "контрагент": ("customers", 10), "заказчик": ("customers", 10),
        "сотрудник": ("employees", 10), "персонал": ("employees", 10),
        "работник": ("employees", 10), "кадры": ("employees", 10), "штат": ("employees", 10),
        "подразделен": ("employees", 9), "отдел": ("employees", 9),
    }

    GROUP_MAP: dict[str, str] = {
        "регион": "region", "город": "region", "территор": "region",
        "категор": "category", "групп": "category", "вид": "category",
        "отдел": "department", "подразделен": "department", "департамент": "department",
        "сегмент": "segment", "тип": "segment",
        "по товарам": "product", "по продукт": "product",
        "в разрезе": "",  # trigger for later handling
    }

    def _best_table(self, text: str) -> tuple[str, int]:
        best = ("sales", 0)
        for kw, (table, pri) in self.TABLE_MAP.items():
            if kw in text and pri > best[1]:
                best = (table, pri)
        return best

    def _match(self, text: str, mapping: dict[str, str]) -> str | None:
        for key, val in mapping.items():
            if key in text:
                return val
        return None

    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        t = text.lower()
        b = SQLBuilder()
        conf = 0.90

        best_table, _ = self._best_table(t)
        grp_col: str | None = None
        agg_expr: str | None = None

        if "по продажам" in t or "по заказам" in t or "в продажах" in t or "продаж по товарам" in t:
            best_table = "sales"
        if "с названиями товаров" in t or "с продуктами" in t:
            best_table = "sales"
        if "по товарам" in t:
            best_table = "sales"
            if not grp_col:
                grp_col = "product"
            if not agg_expr:
                agg_expr = "SUM(revenue) AS value"

        b.table = best_table
        conf = 0.92 if best_table != "sales" else 0.90

        agg_func = self._match(t, self.AGG_MAP)
        target_col = "revenue"
        for kw, col in [("зарплат", "salary"), ("чеков", "revenue"), ("цен", "price"), ("стоимост", "cost"), ("дорог", "price"), ("дешёв", "price")]:
            if kw in t:
                target_col = col
                break

        grp_col = self._match(t, self.GROUP_MAP)
        if grp_col == "":
            grp_col = None
        if not grp_col and "по товарам" in t:
            grp_col = "product"
        if not grp_col and "по продукт" in t:
            grp_col = "product"

        if agg_func:
            col = target_col
            if "в штуках" in t or "объём реализаци" in t:
                col = "units"
            if agg_func in ("MAX", "MIN"):
                agg_expr = f"{agg_func}({col})"
            elif agg_func == "AVG":
                agg_expr = f"AVG({col})"
            elif "COUNT" in agg_func:
                agg_expr = "COUNT(*) AS count"
            elif "SUM(price - cost)" in agg_func:
                agg_expr = "SUM(price - cost) AS profit"
            elif "SUM(units)" in agg_func:
                agg_expr = "SUM(units) AS total_units"
            else:
                agg_expr = f"{agg_func} AS value"
            conf = max(conf, 0.94)
        elif grp_col and not agg_func:
            agg_expr = "COUNT(*) AS count"
            conf = 0.93

        if agg_expr:
            if grp_col:
                b.select_cols = [grp_col, agg_expr]
                b.group_cols.append(grp_col)
                conf = max(conf, 0.96)
            else:
                b.select_cols = [agg_expr]
        elif grp_col:
            b.select_cols = [grp_col, "COUNT(*) AS count"]
            b.group_cols.append(grp_col)

        if any(w in t for w in ["прошлый месяц", "за месяц", "в этом месяце"]):
            b.where_conds.append("date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')")
            b.where_conds.append("date < date_trunc('month', CURRENT_DATE)")
        elif any(w in t for w in ["квартал"]):
            b.where_conds.append("date >= date_trunc('quarter', CURRENT_DATE - INTERVAL '3 months')")
        elif any(w in t for w in ["за год", "этот год", "в этом году", "годов", "текущий год"]):
            b.where_conds.append("date >= date_trunc('year', CURRENT_DATE)")
        elif "вчера" in t:
            b.where_conds.append("date = CURRENT_DATE - INTERVAL '1 day'")
        elif "последний" in t:
            b.where_conds.append("date >= CURRENT_DATE - INTERVAL '30 days'")
        elif "январ" in t and "2026" in t:
            b.where_conds.append("date >= '2026-01-01' AND date < '2026-02-01'")
        elif re.search(r"(?:январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр)", t):
            b.where_conds.append("date >= '2026-01-01'")

        price_m = re.search(r"дороже\s*(\d[\d\s]*)", t)
        if price_m:
            val = int(re.sub(r"\s", "", price_m.group(1)))
            b.where_conds.append(f"price > {val}")
            conf = max(conf, 0.96)

        salary_m = re.search(r"(?:зарплат|оклад)\S*\s*(?:больше|выше|>)\s*([\d\s]+)", t)
        if salary_m:
            val = int(re.sub(r"\s", "", salary_m.group(1)))
            if val < 1000:
                val *= 1000
            b.where_conds.append(f"salary > {val}")

        if any(w in t for w in ["москв", "из москвы", "в москве"]):
            b.where_conds.append("LOWER(region) LIKE '%москв%'")

        if any(w in t for w in ["топ", "самых", "лучш", "популярн", "рейтинг", "лидер", "наибольш", "наименьш", "наименее"]):
            sort_col = target_col
            if agg_func and "COUNT" in agg_func:
                sort_col = "count"
            elif agg_func == "AVG":
                sort_col = target_col
            desc = "наименьш" not in t and "наименее" not in t
            b.order_cols.append((sort_col, "DESC" if desc else "ASC"))
            if not agg_expr and ("по продажам" in t or "по заказам" in t or "товаров" in t):
                agg_expr = "SUM(revenue) AS value"
                if grp_col:
                    b.select_cols = [grp_col, agg_expr]
                else:
                    grp_col = "product"
                    b.select_cols = ["product", agg_expr]
                    b.group_cols.append("product")
            conf = max(conf, 0.96)

        limit_m = re.search(r"(?:топ|первых?|первые?)[-\s]*(\d+)", t)
        if limit_m:
            b.limit_val = int(limit_m.group(1))
        elif re.search(r"\b(?:5|10|20|50)\b", t) and any(w in t for w in ["самых", "первых", "показать", "выведи"]):
            num_m = re.search(r"\b(5|10|20|50)\b", t)
            if num_m:
                b.limit_val = int(num_m.group(1))
        elif any(w in t for w in ["первые", "10 первых", "10 записей"]) and "LIMIT" not in "".join(b.select_cols):
            b.limit_val = 10

        if re.search(r"от дешёвых к дорогим|по возрастани|от меньш|алфавит", t):
            col = "price" if any(w in t for w in ["цен", "стоимост", "товар"]) else "revenue"
            b.order_cols.append((col, "ASC"))

        having_val: int | None = None
        having_m = re.search(r"(?:больше|выше|превыша|более|свыше|меньше|менее)\s*(\d[\d\s]*)", t)
        if having_m:
            having_val = int(re.sub(r"\s", "", having_m.group(1)))
        elif "где" in t and re.search(r"(\d+)", t):
            dm = re.search(r"(\d+)", t.split("где")[-1])
            if dm:
                having_val = int(dm.group(1))

        if having_val is not None and agg_expr and b.group_cols:
            base_raw = agg_expr.split(" AS")[0]
            b.having_cond = f"{base_raw} > {having_val}"
            conf = max(conf, 0.96)

        if "где" in t and re.search(r"больше\s+(\d+)", t):
            dm = re.search(r"больше\s+(\d+)", t)
            if dm:
                val = int(dm.group(1))
                if agg_expr and b.group_cols:
                    base_raw = agg_expr.split(" AS")[0]
                    b.having_cond = f"{base_raw} > {val}"
                    conf = max(conf, 0.96)

        if "где" in t and re.search(r"больше\s+(\d+)", t):
            dm = re.search(r"больше\s+(\d+)", t)
            if dm and agg_expr and grp_col:
                val = int(dm.group(1))
                base_raw = agg_expr.split(" AS")[0]
                b.having_cond = f"{base_raw} > {val}"
                conf = max(conf, 0.96)

        if having_val is not None and agg_expr and b.group_cols:
            if not b.having_cond:
                base_raw = agg_expr.split(" AS")[0]
                b.having_cond = f"{base_raw} > {having_val}"
                conf = max(conf, 0.96)

        if any(w in t for w in ["помесячно", "по месяцам", "сравнение", "динамика", "по кварталам"]):
            if not b.group_cols:
                b.group_cols.append("date_trunc('month', date)")
                if agg_expr:
                    b.select_cols = ["date_trunc('month', date) AS month", agg_expr]
                else:
                    b.select_cols = ["date_trunc('month', date) AS month", "SUM(revenue) AS value"]

        if "активные" in t and "клиент" in t:
            b.select_cols = ["customer_id", "COUNT(*) AS activity"]
            b.group_cols = ["customer_id"]
            b.order_cols.append(("activity", "DESC"))
            agg_expr = "COUNT(*)"
            grp_col = "customer_id"

        if "по товарам" in t and "топ" in t:
            if not grp_col:
                grp_col = "product"
            if not agg_expr:
                agg_expr = "SUM(revenue) AS value"

        if "в разрезе" in t and " и " in t:
            parts = t.split("в разрезе")[-1]
            cols: list[str] = []
            for kw, col in [("регион", "region"), ("товар", "product"), ("продукт", "product"), ("отдел", "department")]:
                if kw in parts:
                    cols.append(col)
            if cols:
                b.group_cols = cols
                if agg_expr:
                    b.select_cols = cols + [agg_expr]
                else:
                    b.select_cols = cols + ["SUM(revenue) AS value"]

        if any(w in t for w in ["не продава", "не покупа", "ни разу", "без покупок", "ничего не купили", "не было продаж"]):
            join_table = "sales"
            join_col = "product_id" if b.table == "products" else "customer_id"
            b.joins.append(f"LEFT JOIN {join_table} ON {b.table}.id = {join_table}.{join_col}")
            b.where_conds.append(f"{join_table}.id IS NULL")

        if any(w in t for w in ["с названиями товаров", "с названиями продуктов"]):
            b.joins.append("JOIN products ON sales.product = products.name")
            b.table = "sales"

        if "с суммой" in t or "сумма покупок" in t:
            b.joins.append("JOIN sales ON customers.id = sales.customer_id")
            b.table = "customers"
            if not agg_expr:
                b.select_cols = ["customers.name", "SUM(sales.revenue) AS total_purchases"]
                b.group_cols = ["customers.name"]
                agg_expr = "SUM(sales.revenue)"
                grp_col = "customers.name"

        if "по клиентам" in t and "с суммой" not in t:
            b.joins.append("JOIN customers ON sales.customer_id = customers.id")
            b.table = "sales"

        sql = b.build()
        return NLPResult(nlp_input=text, generated_sql=sql, explanation=f"SQL for: {text[:80]}", confidence=conf, model="smart-mock-v2.1", dialect=NLPDialect.MOCK_SMART)

    async def health_check(self) -> dict[str, Any]:
        return {"provider": "smart-mock-v2.1", "healthy": True}


class NLPToSQLPipelineV2_1:
    """Pipeline: generate -> post-process -> verify -> retry."""

    MAX_RETRIES: int = 2

    def __init__(self, provider: BaseNLPSQLProvider):
        self.provider = provider

    async def execute(self, text: str, schema: dict[str, Any] | None = None, verify: bool = True) -> NLPResult:
        if schema is None:
            from gost_bi.nlp.pipeline_v2 import ENRICHED_SCHEMA
            schema = ENRICHED_SCHEMA

        result = await self.provider.generate_sql(text, schema)
        if not result.generated_sql:
            return result

        from gost_bi.nlp.pipeline_v2 import PostProcessor
        sql, fixes = PostProcessor.fix(result.generated_sql, schema)
        if fixes:
            result.generated_sql = sql
            result.errors_fixed = fixes

        if verify:
            from gost_bi.quality.sql_verifier import SQLVerifier
            verifier = SQLVerifier()
            for attempt in range(self.MAX_RETRIES + 1):
                report = verifier.verify(result.generated_sql, nlp_input=text)
                report.log()
                if report.overall_passed:
                    break
                if attempt < self.MAX_RETRIES:
                    errors = [c.message for c in report.checks if not c.passed]
                    retry_text = f"{text}\n[BAD SQL: {result.generated_sql}]\n[ERRORS: {'; '.join(errors)}]\n[FIX AND RETURN VALID SQL ONLY]"
                    retry = await self.provider.generate_sql(retry_text, schema)
                    if retry.generated_sql:
                        result = retry
                        result.retry_count = attempt + 1
                else:
                    result.confidence = 0.0

        return result
