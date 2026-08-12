"""
GOST BI NLP→SQL Engine v2 — High-Accuracy Pipeline.

Target: >95% accuracy on 50 test queries.

Architecture:
    1. Analyze: entity extraction, intent classification, schema matching
    2. Generate: few-shot enriched prompt → LLM
    3. Post-process: fix common LLM errors (aliases, GROUP BY, date ranges)
    4. Verify: SQL Verifier (Level 6)
    5. Retry: if failed, feed error back to LLM (up to 3 attempts)
    6. Final verify
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("gost_bi.nlp.engine.v2")


class NLPDialect(str, Enum):
    YANDEX_GPT = "yandexgpt"
    GIGA_CHAT = "gigachat"
    LOCAL_LLM = "local"
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
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success(self) -> bool:
        return self.confidence >= 0.7 and len(self.generated_sql.strip()) > 0


class BaseNLPSQLProvider(ABC):
    @abstractmethod
    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        ...


# ============================================================
# Enriched Schema — column descriptions, Russian synonyms, sample values
# ============================================================

ENRICHED_SCHEMA: dict[str, Any] = {
    "tables": {
        "sales": {
            "name": "sales",
            "name_ru": "Продажи",
            "synonyms": ["продажи", "реализация", "сбыт", "выручка", "чеки", "заказы", "транзакции"],
            "description": "Таблица продаж. Каждая запись — одна транзакция продажи.",
            "columns": {
                "id": {"type": "INTEGER", "description": "Уникальный идентификатор транзакции"},
                "date": {"type": "DATE", "description": "Дата продажи. Формат: YYYY-MM-DD"},
                "region": {"type": "VARCHAR", "description": "Регион продажи. Примеры: Москва, Санкт-Петербург, Краснодарский край"},
                "product": {"type": "VARCHAR", "description": "Название товара"},
                "revenue": {"type": "NUMERIC", "description": "Выручка в рублях (сумма продажи)"},
                "units": {"type": "INTEGER", "description": "Количество проданных единиц"},
                "customer_id": {"type": "INTEGER", "description": "ID клиента (внешний ключ к таблице customers)"},
            },
            "sample_rows": [
                {"id": 1, "date": "2026-08-10", "region": "Москва", "product": "Ноутбук", "revenue": 150000, "units": 1, "customer_id": 42},
            ],
        },
        "products": {
            "name": "products",
            "name_ru": "Товары",
            "synonyms": ["товары", "продукты", "номенклатура", "ассортимент", "изделия", "продукция"],
            "description": "Справочник товаров (аналог справочника Номенклатура в 1С).",
            "columns": {
                "id": {"type": "INTEGER", "description": "Уникальный идентификатор товара"},
                "name": {"type": "VARCHAR", "description": "Наименование товара. Примеры: Ноутбук, Монитор, Клавиатура"},
                "category": {"type": "VARCHAR", "description": "Категория товара. Примеры: Электроника, Одежда, Продукты питания"},
                "price": {"type": "NUMERIC", "description": "Цена продажи в рублях"},
                "cost": {"type": "NUMERIC", "description": "Себестоимость в рублях (закупочная цена)"},
            },
            "sample_rows": [
                {"id": 1, "name": "Ноутбук", "category": "Электроника", "price": 150000, "cost": 120000},
            ],
        },
        "customers": {
            "name": "customers",
            "name_ru": "Клиенты",
            "synonyms": ["клиенты", "покупатели", "заказчики", "контрагенты", "потребители"],
            "description": "Справочник клиентов (аналог справочника Контрагенты в 1С).",
            "columns": {
                "id": {"type": "INTEGER", "description": "Уникальный идентификатор клиента"},
                "name": {"type": "VARCHAR", "description": "Наименование/ФИО клиента"},
                "region": {"type": "VARCHAR", "description": "Регион клиента. Примеры: Москва, Санкт-Петербург, Казань"},
                "segment": {"type": "VARCHAR", "description": "Сегмент клиента. Примеры: Розница, Опт, Корпоративный, VIP"},
                "created_at": {"type": "DATE", "description": "Дата регистрации клиента"},
            },
            "sample_rows": [
                {"id": 42, "name": "ООО Ромашка", "region": "Москва", "segment": "Опт", "created_at": "2025-03-15"},
            ],
        },
        "employees": {
            "name": "employees",
            "name_ru": "Сотрудники",
            "synonyms": ["сотрудники", "работники", "персонал", "кадры", "штат", "люди"],
            "description": "Справочник сотрудников компании.",
            "columns": {
                "id": {"type": "INTEGER", "description": "Табельный номер сотрудника"},
                "name": {"type": "VARCHAR", "description": "ФИО сотрудника"},
                "department": {"type": "VARCHAR", "description": "Отдел/подразделение. Примеры: IT, Продажи, Бухгалтерия, HR, Производство"},
                "salary": {"type": "NUMERIC", "description": "Месячный оклад в рублях"},
                "hire_date": {"type": "DATE", "description": "Дата приёма на работу"},
            },
            "sample_rows": [
                {"id": 1, "name": "Иванов Иван Иванович", "department": "IT", "salary": 150000, "hire_date": "2020-06-01"},
            ],
        },
    },
    "relationships": [
        {"from": "sales.customer_id", "to": "customers.id", "type": "many-to-one"},
        {"from": "sales.product", "to": "products.name", "type": "many-to-one"},
    ],
}


FEW_SHOT_EXAMPLES = """
=== Пример 1 ===
Запрос: Покажи все продажи
SQL: SELECT * FROM sales

=== Пример 2 ===
Запрос: Выручка по регионам за прошлый месяц
SQL: SELECT region, SUM(revenue) AS total_revenue FROM sales WHERE date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND date < date_trunc('month', CURRENT_DATE) GROUP BY region ORDER BY total_revenue DESC

=== Пример 3 ===
Запрос: Топ-10 товаров по продажам
SQL: SELECT product, SUM(revenue) AS total_sales FROM sales GROUP BY product ORDER BY total_sales DESC LIMIT 10

=== Пример 4 ===
Запрос: Количество клиентов по сегментам
SQL: SELECT segment, COUNT(*) AS client_count FROM customers GROUP BY segment ORDER BY client_count DESC

=== Пример 5 ===
Запрос: Средняя зарплата по отделам
SQL: SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC

=== Пример 6 ===
Запрос: Регионы с выручкой больше 10 миллионов
SQL: SELECT region, SUM(revenue) AS total FROM sales GROUP BY region HAVING SUM(revenue) > 10000000 ORDER BY total DESC
"""

SYSTEM_PROMPT_V2 = """Ты — SQL-эксперт для BI-системы ГОСТ БИ. Твоя задача: преобразовать запрос на русском языке в корректный PostgreSQL SQL.

ЖЁСТКИЕ ПРАВИЛА:
1. ТОЛЬКО SELECT. Никаких INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE.
2. Всегда пиши название таблицы ПОЛНОСТЬЮ как в схеме: sales, products, customers, employees. НИКОГДА не придумывай свои таблицы.
3. Всегда пиши названия колонок ТОЧНО как в схеме: region, revenue, product, category, price, cost, salary, department, segment, units.
4. Если запрос про деньги/выручку/доход/заработок — используй SUM(revenue) ИЛИ AVG(revenue) из таблицы sales.
5. Если запрос про количество/численность/сколько — используй COUNT(*).
6. Если запрос про 'по регионам/категориям/отделам/сегментам' — ОБЯЗАТЕЛЬНО добавь GROUP BY.
7. Если запрос про 'топ/самые/лучшие/худшие/рейтинг' — добавь ORDER BY ... DESC + LIMIT.
8. Если запрос про 'за месяц/квартал/год' — добавь WHERE date >= ... с правильным интервалом.
9. Для всех агрегаций добавляй понятные русские алиасы: AS total_revenue, AS avg_salary.
10. Форматируй SQL красиво: SELECT на одной строке, FROM на следующей, WHERE/GROUP BY/ORDER BY с новой строки.

ВОЗВРАЩАЙ СТРОГО JSON:
{"sql": "SELECT ...", "explanation": "Краткое описание на русском", "confidence": 0.95}"""


class PostProcessor:
    """Fixes common LLM mistakes in generated SQL."""

    TABLE_ALIASES: dict[str, str] = {
        "товары": "products",
        "продажи": "sales",
        "клиенты": "customers",
        "сотрудники": "employees",
        "продукты": "products",
        "заказы": "sales",
    }

    @classmethod
    def fix(cls, sql: str, schema: dict[str, Any]) -> tuple[str, list[str]]:
        fixes: list[str] = []
        original = sql

        sql = sql.strip().rstrip(";")

        # Fix: missing GROUP BY when aggregation present
        has_agg = bool(re.search(r"\b(SUM|AVG|COUNT|MIN|MAX)\s*\(.+?\)", sql, re.IGNORECASE))
        has_group_by = "GROUP BY" in sql.upper()
        non_agg_cols = cls._find_non_aggregated_columns(sql)

        if has_agg and not has_group_by and non_agg_cols:
            cols = ", ".join(sorted(non_agg_cols))
            sql += f"\nGROUP BY {cols}"
            fixes.append(f"Added GROUP BY {cols}")

        # Fix: missing ORDER BY DESC when LIMIT present and query implies ranking
        if "LIMIT" in sql.upper() and "ORDER BY" not in sql.upper():
            # Find a numeric column to sort by
            for col in ["revenue", "price", "salary", "units"]:
                if col in sql.lower():
                    sql += f"\nORDER BY {col} DESC"
                    fixes.append(f"Added ORDER BY {col} DESC")
                    break

        # Fix: use table aliases instead of Russian names
        for ru_name, en_name in cls.TABLE_ALIASES.items():
            pattern = re.compile(rf"\b{ru_name}\b", re.IGNORECASE)
            if pattern.search(sql) and en_name not in sql.lower():
                sql = pattern.sub(en_name, sql)
                fixes.append(f"Replaced '{ru_name}' with '{en_name}'")

        # Fix: missing LIMIT when query has "топ" or numbers like "5/10"
        limit_match = re.search(r"(?:TOP|ТОП|первые|первых)\s*(\d+)", original, re.IGNORECASE)
        if limit_match and "LIMIT" not in sql.upper():
            sql += f"\nLIMIT {limit_match.group(1)}"
            fixes.append(f"Added LIMIT {limit_match.group(1)}")

        # Fix: ensure WHERE uses proper date format
        sql = re.sub(r"date >= ['\"]?(\d{2}\.\d{2}\.\d{4})['\"]?", r"date >= '\1'", sql)

        return sql, fixes

    @staticmethod
    def _find_non_aggregated_columns(sql: str) -> set[str]:
        agg_cols = set()
        for match in re.finditer(r"\b(SUM|AVG|COUNT|MIN|MAX)\s*\(\s*(\w+)", sql, re.IGNORECASE):
            agg_cols.add(match.group(2).lower())

        all_cols = set(re.findall(r"[\w]+", sql.lower()))
        known_cols = {"region", "product", "category", "department", "segment", "name", "id", "customer_id", "date"}
        return {c for c in all_cols & known_cols if c not in agg_cols}


class SmartMockProvider(BaseNLPSQLProvider):
    """Rule-based NLP→SQL provider for offline testing. Designed for high accuracy."""

    def __init__(self):
        self.post = PostProcessor()
        self.rules = self._build_rules()

    def _build_rules(self) -> list[tuple[str, str, float]]:
        return [
            (r"продаж|чеки|заказы|транзакции|реализац", "FROM sales", 0.9),
            (r"товар|продукт|номенклатур|ассортимент", "FROM products", 0.9),
            (r"клиент|покупател|заказчик|контрагент", "FROM customers", 0.9),
            (r"сотрудник|персонал|работник|кадры|штат", "FROM employees", 0.9),
            (r"выручк|доход|заработ|прибыль.*(?:компани|общ|суммарн)", "SUM(revenue)", 0.9),
            (r"средн.*(?:зарплат|чек|цен)", "AVG", 0.9),
            (r"количеств|численност|сколько.*(?:всего|человек)", "COUNT(*)", 0.9),
            (r"максимальн|сам.*(?:больш|дорог|высок)", "MAX + ORDER BY DESC", 0.8),
            (r"минимальн|сам.*(?:маленьк|дешёв|низк)", "MIN + ORDER BY ASC", 0.8),
            (r"по регионам|по городам|по территор|в разрезе регион", "GROUP BY region", 0.95),
            (r"по категор|по группам|по видам.*товар", "GROUP BY category", 0.95),
            (r"по отделам|по подразделен|по департамент", "GROUP BY department", 0.95),
            (r"по сегментам|по типам.*клиент", "GROUP BY segment", 0.95),
            (r"топ|самых|лучш|популярн|рейтинг|лидер", "ORDER BY DESC + LIMIT", 0.85),
            (r"за месяц|за прошлый месяц|в этом месяце", "WHERE date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')", 0.85),
            (r"за квартал|за прошлый квартал|в этом квартале", "WHERE date >= date_trunc('quarter', CURRENT_DATE - INTERVAL '3 months')", 0.85),
            (r"за год|за этот год|в этом году|годов", "WHERE date >= date_trunc('year', CURRENT_DATE)", 0.85),
            (r"дороже\s*(\d+)", None, 0.0),
            (r"больше\s*(\d+)\s*(?:тысяч|миллион)", None, 0.0),
            (r"в москв|из москв|московск", "WHERE LOWER(region) LIKE '%москв%'", 0.9),
            (r"ни разу не|не прод|не куп|без.*продаж", "LEFT JOIN + IS NULL", 0.85),
        ]

    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        text_lower = text.lower()
        tables = []
        cols = ["*"]
        extras = []
        confidence = 0.85

        for pattern, action, conf in self.rules:
            if re.search(pattern, text_lower):
                if action and action.startswith("FROM "):
                    tables.append(action)
                elif action:
                    extras.append(action)
                confidence = max(confidence, conf)

        if not tables:
            tables = ["FROM sales"]

        primary_table = tables[0].replace("FROM ", "")

        has_agg = any("SUM" in e or "AVG" in e or "COUNT" in e or "MAX" in e or "MIN" in e for e in extras)
        has_group = any("GROUP BY" in e for e in extras)
        has_order = any("ORDER BY" in e for e in extras)
        has_limit = any("LIMIT" in e for e in extras)
        has_time_ref = any(w in text_lower for w in ["за ", "месяц", "квартал", "год", "вчера", "сегодня", "январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"])
        has_where = any("WHERE" in e for e in extras) or has_time_ref

        if has_agg:
            agg_parts = [e for e in extras if any(kw in e for kw in ["SUM", "AVG", "COUNT", "MAX", "MIN"])]
            group_parts = [e for e in extras if "GROUP BY" in e]
            if agg_parts:
                cols = []
                if group_parts:
                    gp = group_parts[0].replace("GROUP BY ", "")
                    cols.append(gp)
                cols.extend(agg_parts)
            else:
                cols = ["SUM(revenue) AS total_revenue"]
        elif "топ" in text_lower or "самых" in text_lower:
            cols = ["product", "SUM(revenue) AS total"]
            extras.append("GROUP BY product")
            extras.append("ORDER BY total DESC")
            extras.append("LIMIT 10")

        select_clause = "SELECT " + ", ".join(cols)
        sql = f"{select_clause}\n{tables[0]}"

        extras_seen = set()
        for e in extras:
            if e not in extras_seen and not e.startswith("FROM "):
                extras_seen.add(e)
                sql += f"\n{e}"

        if has_where and not any("WHERE" in e for e in extras):
            sql += "\nWHERE date >= date_trunc('year', CURRENT_DATE)"

        if has_agg and not any("GROUP BY" in e for e in extras):
            group_col = self._infer_group_column(text_lower, cols)
            if group_col:
                sql += f"\nGROUP BY {group_col}"
                extras_seen.add(f"GROUP BY {group_col}")

        if not any("ORDER BY" in e for e in extras) and "топ" in text_lower:
            sql += "\nORDER BY total DESC"

        limit_match = re.search(r"(?:топ|первых?)\s*(\d+)", text_lower)
        if limit_match and not has_limit:
            sql += f"\nLIMIT {limit_match.group(1)}"

        sql, fixes = self.post.fix(sql, schema)

        return NLPResult(
            nlp_input=text,
            generated_sql=sql,
            explanation=f"Сгенерирован SQL для: {text[:80]}",
            confidence=min(confidence + len(fixes) * 0.02, 0.99),
            model="smart-mock-v2",
            dialect=NLPDialect.MOCK_SMART,
            errors_fixed=fixes,
        )

    def _infer_group_column(self, text: str, cols: list[str]) -> str | None:
        if "регион" in text:
            return "region"
        if "категор" in text or "категори" in text:
            return "category"
        if "отдел" in text or "подразделен" in text or "департамент" in text:
            return "department"
        if "сегмент" in text:
            return "segment"
        for col in cols:
            if col in ("region", "category", "department", "segment", "product"):
                return col
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"provider": "smart-mock-v2", "healthy": True}


class NLPToSQLPipelineV2:
    """Enhanced pipeline with retry loop."""

    MAX_RETRIES: int = 3

    def __init__(self, provider: BaseNLPSQLProvider):
        self.provider = provider
        self.post = PostProcessor()

    async def execute(self, text: str, schema: dict[str, Any] | None = None, verify: bool = True) -> NLPResult:
        if schema is None:
            schema = ENRICHED_SCHEMA

        from gost_bi.quality.sql_verifier import SQLVerifier
        verifier = SQLVerifier()

        result = await self.provider.generate_sql(text, schema)

        if result.generated_sql:
            sql, fixes = self.post.fix(result.generated_sql, schema)
            if fixes:
                result.generated_sql = sql
                result.errors_fixed = fixes
                result.confidence = min(result.confidence + len(fixes) * 0.02, 0.99)

        for attempt in range(1, self.MAX_RETRIES + 1):
            if not result.generated_sql:
                break

            if verify:
                report = verifier.verify(result.generated_sql, nlp_input=text, model=result.model)
                report.log()

                if report.overall_passed:
                    break

                errors = [c.message for c in report.checks if not c.passed]
                logger.warning(f"NLP→SQL retry {attempt}/{self.MAX_RETRIES}: {'; '.join(errors)}")

                if attempt < self.MAX_RETRIES:
                    retry_result = await self._retry_with_error(text, schema, result.generated_sql, errors)
                    if retry_result.generated_sql:
                        result = retry_result
                        result.retry_count = attempt
                else:
                    result.confidence = 0.0
                    result.explanation += f" | Failed after {self.MAX_RETRIES} retries: {'; '.join(errors)}"

        return result

    async def _retry_with_error(self, text: str, schema: dict[str, Any], failed_sql: str, errors: list[str]) -> NLPResult:
        enriched_text = f"{text}\n\n[Предыдущая попытка SQL: {failed_sql}]\n[Ошибки: {'; '.join(errors)}]\n[Исправь ошибки и верни корректный SQL.]"
        return await self.provider.generate_sql(enriched_text, schema)
