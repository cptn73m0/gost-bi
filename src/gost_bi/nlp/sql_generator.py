"""
Russian NLP → SQL Engine — Sprint 5.

Converts natural language queries in Russian to SQL.
Uses YandexGPT / GigaChat with a fallback to on-premise LLMs.

Pipeline:
    Text → Entity Extraction → Schema Mapping → SQL Generation → Verification (Level 6) → Execution

Example:
    "покажи выручку по регионам за прошлый квартал"
    → SELECT region, SUM(revenue) FROM sales WHERE date >= '2026-04-01' GROUP BY region
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

logger = logging.getLogger("gost_bi.nlp.engine")


class NLPDialect(str, Enum):
    YANDEX_GPT = "yandexgpt"
    GIGA_CHAT = "gigachat"
    LOCAL_LLM = "local"


@dataclass
class NLPQuery:
    """Parsed NLP query with extracted entities."""

    raw_text: str
    intent: str = "select"
    entities: dict[str, str] = field(default_factory=dict)
    time_range: str = ""
    aggregations: list[str] = field(default_factory=list)
    group_by: list[str] = field(default_factory=list)
    filters: list[dict[str, str]] = field(default_factory=list)
    sort: str = ""

    @property
    def is_valid(self) -> bool:
        return len(self.raw_text.strip()) >= 3


@dataclass
class NLPResult:
    """Result of NLP→SQL conversion."""

    nlp_input: str
    generated_sql: str
    explanation: str
    confidence: float
    model: str
    dialect: NLPDialect
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success(self) -> bool:
        return self.confidence >= 0.7 and len(self.generated_sql.strip()) > 0


class BaseNLPSQLProvider(ABC):
    """Abstract base for NLP→SQL providers."""

    @abstractmethod
    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        ...


class YandexGPTProvider(BaseNLPSQLProvider):
    """YandexGPT API provider for NLP→SQL."""

    SYSTEM_PROMPT = """Ты — SQL-ассистент для BI-системы на базе Superset.
Твоя задача: преобразовать запрос на русском языке в корректный SQL-запрос PostgreSQL.

ПРАВИЛА:
1. Только SELECT-запросы. Никаких INSERT, UPDATE, DELETE, DROP.
2. Используй русские имена таблиц и колонок как есть из схемы.
3. Всегда используй явные JOIN, не подзапросы.
4. Для агрегаций добавляй осмысленные алиасы (AS).
5. Форматируй SQL красиво с отступами.
6. Если запрос неоднозначный — уточни у пользователя в explanation.
7. ВСЕГДА используй DeletionMark eq false для справочников 1С.

Возвращай JSON:
{
    "sql": "SELECT ...",
    "explanation": "Запрос показывает ...",
    "confidence": 0.85
}"""

    def __init__(self, api_key: str, folder_id: str, model: str = "yandexgpt-pro"):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model

    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        schema_text = json.dumps(schema, ensure_ascii=False, indent=2)

        prompt = f"""{self.SYSTEM_PROMPT}

СХЕМА БД:
{schema_text}

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{text}

SQL:"""

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                    headers={
                        "Authorization": f"Api-Key {self.api_key}",
                        "x-folder-id": self.folder_id,
                    },
                    json={
                        "modelUri": f"gpt://{self.folder_id}/{self.model}",
                        "completionOptions": {"temperature": 0.1, "maxTokens": 1000},
                        "messages": [
                            {"role": "system", "text": self.SYSTEM_PROMPT},
                            {"role": "user", "text": f"Схема:\n{schema_text}\n\nЗапрос: {text}\n\nSQL:"},
                        ],
                    },
                )

                if resp.status_code != 200:
                    return NLPResult(
                        nlp_input=text,
                        generated_sql="",
                        explanation=f"API error: {resp.status_code}",
                        confidence=0.0,
                        model=self.model,
                        dialect=NLPDialect.YANDEX_GPT,
                    )

                data = resp.json()
                content = data["result"]["alternatives"][0]["message"]["text"]

                result = self._parse_response(content)

                return NLPResult(
                    nlp_input=text,
                    generated_sql=result.get("sql", ""),
                    explanation=result.get("explanation", ""),
                    confidence=result.get("confidence", 0.0),
                    model=self.model,
                    dialect=NLPDialect.YANDEX_GPT,
                )

        except ImportError:
            return NLPResult(
                nlp_input=text,
                generated_sql="",
                explanation="httpx not installed",
                confidence=0.0,
                model=self.model,
                dialect=NLPDialect.YANDEX_GPT,
            )
        except Exception as exc:
            logger.error(f"YandexGPT error: {exc}")
            return NLPResult(
                nlp_input=text,
                generated_sql="",
                explanation=str(exc),
                confidence=0.0,
                model=self.model,
                dialect=NLPDialect.YANDEX_GPT,
            )

    def _parse_response(self, text: str) -> dict[str, Any]:
        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        sql_match = re.search(r"(SELECT\b.*?)(?:;|\n\n|$)", text, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return {"sql": sql_match.group(1).strip(), "explanation": text[:200], "confidence": 0.6}

        return {"sql": "", "explanation": text[:200], "confidence": 0.0}

    async def health_check(self) -> dict[str, Any]:
        return {
            "provider": "yandexgpt",
            "model": self.model,
            "healthy": bool(self.api_key),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class GigaChatProvider(BaseNLPSQLProvider):
    """GigaChat API provider for NLP→SQL."""

    def __init__(self, auth_token: str, model: str = "GigaChat-Pro"):
        self.auth_token = auth_token
        self.model = model

    async def generate_sql(self, text: str, schema: dict[str, Any]) -> NLPResult:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": YandexGPTProvider.SYSTEM_PROMPT.replace(
                                    "YandexGPT", "GigaChat"
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Схема БД:\n{json.dumps(schema, ensure_ascii=False)}\n\nЗапрос: {text}",
                            },
                        ],
                        "temperature": 0.1,
                    },
                )

                if resp.status_code != 200:
                    return NLPResult(
                        nlp_input=text,
                        generated_sql="",
                        explanation=f"GigaChat API error: {resp.status_code}",
                        confidence=0.0,
                        model=self.model,
                        dialect=NLPDialect.GIGA_CHAT,
                    )

                content = resp.json()["choices"][0]["message"]["content"]

                result = YandexGPTProvider._parse_response(YandexGPTProvider, content)

                return NLPResult(
                    nlp_input=text,
                    generated_sql=result.get("sql", ""),
                    explanation=result.get("explanation", ""),
                    confidence=result.get("confidence", 0.0),
                    model=self.model,
                    dialect=NLPDialect.GIGA_CHAT,
                )

        except ImportError:
            return NLPResult(
                nlp_input=text,
                generated_sql="",
                explanation="httpx not installed",
                confidence=0.0,
                model=self.model,
                dialect=NLPDialect.GIGA_CHAT,
            )
        except Exception as exc:
            logger.error(f"GigaChat error: {exc}")
            return NLPResult(
                nlp_input=text,
                generated_sql="",
                explanation=str(exc),
                confidence=0.0,
                model=self.model,
                dialect=NLPDialect.GIGA_CHAT,
            )

    async def health_check(self) -> dict[str, Any]:
        return {
            "provider": "gigachat",
            "model": self.model,
            "healthy": bool(self.auth_token),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class NLPToSQLPipeline:
    """Full NLP→SQL pipeline with verification."""

    def __init__(self, provider: BaseNLPSQLProvider):
        self.provider = provider

    async def execute(self, text: str, schema: dict[str, Any], verify: bool = True) -> NLPResult:
        result = await self.provider.generate_sql(text, schema)

        if not result.success:
            logger.warning(f"NLP→SQL low confidence: {result.confidence:.2f}")
            return result

        if verify and result.generated_sql:
            from gost_bi.quality.sql_verifier import SQLVerifier

            verifier = SQLVerifier()
            report = verifier.verify(result.generated_sql, nlp_input=text, model=result.model)
            report.log()

            if not report.overall_passed:
                result.confidence = 0.0
                result.explanation += f" | Заблокировано SQL-верификатором: {'; '.join(c.message for c in report.checks if not c.passed)}"

        return result
