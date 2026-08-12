"""
User Feedback Triage System — Level 12 of the self-checking system.

Processes user-submitted error reports and feedback from the UI:
- Classifies by severity and category
- Triggers automated actions (Jira ticket, alert, test suite extension)
- Generates user-facing response
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("gost_bi.monitoring.feedback")


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(Enum):
    SQL_ENGINE = "sql_engine"
    CHART_RENDERING = "chart_rendering"
    ONEC_INTEGRATION = "1c_integration"
    GOST_REPORTING = "gost_reporting"
    PERFORMANCE = "performance"
    AUTH = "authentication"
    UI_UX = "ui_ux"
    DATA_EXPORT = "data_export"
    NLP_AI = "nlp_ai"
    OTHER = "other"


class Action(Enum):
    CREATE_JIRA_TICKET = "create_jira_ticket"
    ALERT_ONCALL = "alert_oncall"
    ADD_TO_SQL_TEST_SUITE = "add_to_sql_test_suite"
    ADD_TO_VISUAL_REGRESSION = "add_to_visual_regression"
    LOG_ONLY = "log_only"
    SEND_AUTO_RESPONSE = "send_auto_response"
    PING_PRODUCT_MANAGER = "ping_product_manager"


@dataclass
class UserReport:
    user_id: str
    message: str
    component: str | None = None
    dashboard_id: str | None = None
    sql_query: str | None = None
    screenshot_base64: str | None = None
    browser_info: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TriageResult:
    severity: Severity
    category: Category
    actions: list[Action] = field(default_factory=list)
    auto_response: str = ""
    assigned_to: str = ""
    jira_key: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def execute_actions(self) -> None:
        """Execute the determined actions (integrations would go here)."""
        for action in self.actions:
            logger.info(f"Triage action: {action.value} for category {self.category.value}")
            match action:
                case Action.CREATE_JIRA_TICKET:
                    self._create_jira_ticket()
                case Action.ALERT_ONCALL:
                    self._alert_oncall()
                case Action.ADD_TO_SQL_TEST_SUITE:
                    self._add_to_sql_test_suite()
                case Action.ADD_TO_VISUAL_REGRESSION:
                    self._add_to_visual_regression()
                case Action.LOG_ONLY:
                    pass
                case Action.SEND_AUTO_RESPONSE:
                    pass
                case Action.PING_PRODUCT_MANAGER:
                    self._ping_product_manager()

    def _create_jira_ticket(self) -> None:
        logger.info(f"Creating Jira ticket for: {self.category.value}")
        # Integration point: Jira REST API

    def _alert_oncall(self) -> None:
        logger.critical(f"ONCALL ALERT: {self.category.value} — severity {self.severity.value}")

    def _add_to_sql_test_suite(self) -> None:
        logger.info("Adding failing SQL to regression test suite")

    def _add_to_visual_regression(self) -> None:
        logger.info("Adding screenshot to visual regression baseline")

    def _ping_product_manager(self) -> None:
        logger.info("Pinging product manager for UX issue")


class FeedbackTriager:
    """Classifies user feedback and determines automated actions."""

    DISASTER_KEYWORDS: list[str] = [
        "ничего не работает",
        "не открывается",
        "ошибка",
        "упало",
        "не грузится",
        "белый экран",
        "500",
        "пусто",
        "не загружается",
        "сломалось",
        "краш",
        "crash",
        "error",
        "broken",
        "down",
    ]

    CATEGORY_KEYWORDS: dict[Category, list[str]] = {
        Category.SQL_ENGINE: ["sql", "запрос", "query", "ошибка в запросе", "не выполняется"],
        Category.CHART_RENDERING: ["график", "диаграмма", "chart", "не отображается", "пустой график"],
        Category.ONEC_INTEGRATION: ["1с", "1c", "один эс", "odata", "коннектор", "синхронизация"],
        Category.GOST_REPORTING: ["гост", "отчёт", "бланк", "форма", "росстат", "налоговая", "фнс"],
        Category.PERFORMANCE: ["медленно", "долго", "тормозит", "зависает", "slow", "timeout", "lag"],
        Category.AUTH: ["вход", "пароль", "авторизация", "login", "есia", "logout"],
        Category.UI_UX: ["интерфейс", "кнопка", "ui", "неудобно", "непонятно"],
        Category.DATA_EXPORT: ["экспорт", "скачать", "выгрузить", "csv", "pdf", "xlsx", "export"],
        Category.NLP_AI: ["ai", "ассистент", "nlp", "текстовый запрос", "не понимает"],
    }

    def triage(self, report: UserReport) -> TriageResult:
        severity = self._classify_severity(report)
        category = self._classify_category(report)
        actions = self._determine_actions(severity, category, report)
        auto_response = self._generate_user_response(severity, category)

        result = TriageResult(
            severity=severity,
            category=category,
            actions=actions,
            auto_response=auto_response,
        )

        logger.info(
            f"Feedback triaged: user={report.user_id}, "
            f"severity={severity.value}, category={category.value}, "
            f"actions={[a.value for a in actions]}"
        )

        return result

    def _classify_severity(self, report: UserReport) -> Severity:
        message_lower = report.message.lower()

        severe_indicators = ["ничего не работает", "не открывается", "упало", "белый экран", "crash", "не грузится"]
        moderate_indicators = ["ошибка", "error", "медленно", "тормозит", "пусто", "не загружается"]

        if any(ind in message_lower for ind in severe_indicators):
            return Severity.CRITICAL
        if any(ind in message_lower for ind in moderate_indicators):
            return Severity.HIGH
        if "?" in report.message or "как" in message_lower:
            return Severity.LOW
        return Severity.MEDIUM

    def _classify_category(self, report: UserReport) -> Category:
        message_lower = report.message.lower()
        if report.component:
            message_lower += f" {report.component.lower()}"

        scores: dict[Category, int] = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=lambda k: scores[k])

        if report.sql_query:
            return Category.SQL_ENGINE
        if report.dashboard_id:
            return Category.CHART_RENDERING
        return Category.OTHER

    def _determine_actions(self, severity: Severity, category: Category, report: UserReport) -> list[Action]:
        actions: list[Action] = []

        if severity == Severity.CRITICAL:
            actions.append(Action.CREATE_JIRA_TICKET)
            actions.append(Action.ALERT_ONCALL)

        if severity in (Severity.CRITICAL, Severity.HIGH):
            category_actions = {
                Category.SQL_ENGINE: [Action.ADD_TO_SQL_TEST_SUITE],
                Category.CHART_RENDERING: [Action.ADD_TO_VISUAL_REGRESSION],
                Category.GOST_REPORTING: [Action.CREATE_JIRA_TICKET],
            }
            actions.extend(category_actions.get(category, []))

        if severity == Severity.LOW:
            actions.append(Action.LOG_ONLY)

        if category == Category.UI_UX:
            actions.append(Action.PING_PRODUCT_MANAGER)

        return actions

    def _generate_user_response(self, severity: Severity, category: Category) -> str:
        responses = {
            Category.SQL_ENGINE: {
                Severity.CRITICAL: "Ваш запрос не может быть выполнен. Мы уже работаем над исправлением. Приносим извинения.",
                Severity.HIGH: "Возникла ошибка при выполнении SQL-запроса. Наша команда уже проверяет причину.",
            },
            Category.PERFORMANCE: {
                Severity.HIGH: "Спасибо за сигнал! Мы работаем над ускорением системы. Ожидайте улучшений в ближайшем обновлении.",
            },
            Category.ONEC_INTEGRATION: {
                Severity.CRITICAL: "Проблема с подключением к 1С. Проверьте доступность сервера 1С или обратитесь к администратору.",
            },
            Category.GOST_REPORTING: {
                Severity.HIGH: "Проблема с формированием ГОСТ-отчёта. Наши специалисты проверят шаблон и исправят ошибку.",
            },
        }

        default_responses = {
            Severity.CRITICAL: "Спасибо за обращение! Мы уже в курсе проблемы и работаем над её решением.",
            Severity.HIGH: "Спасибо за сигнал! Мы проверим и исправим проблему в ближайшее время.",
            Severity.MEDIUM: "Спасибо за обратную связь! Мы учтём её в следующих обновлениях.",
            Severity.LOW: "Спасибо! Если у вас есть дополнительные пожелания, будем рады их услышать.",
        }

        return responses.get(category, {}).get(severity, default_responses.get(severity, "Спасибо за обращение!"))
