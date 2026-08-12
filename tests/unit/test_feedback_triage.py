"""Unit tests for feedback triage system — Level 12."""

import pytest
from gost_bi.monitoring.feedback_triage import (
    Action,
    Category,
    FeedbackTriager,
    Severity,
    UserReport,
)


class TestFeedbackTriager:
    def setup_method(self):
        self.triager = FeedbackTriager()

    def test_critical_error_classified_critical(self):
        report = UserReport(user_id="user1", message="Всё упало, ничего не работает в дашборде")
        result = self.triager.triage(report)
        assert result.severity == Severity.CRITICAL

    def test_white_screen_classified_critical(self):
        report = UserReport(user_id="user1", message="Белый экран при открытии графика")
        result = self.triager.triage(report)
        assert result.severity == Severity.CRITICAL

    def test_db_error_classified_high(self):
        report = UserReport(user_id="user1", message="Ошибка при выполнении запроса SQL")
        result = self.triager.triage(report)
        assert result.severity == Severity.HIGH

    def test_slow_performance_classified_high(self):
        report = UserReport(user_id="user1", message="Дашборд медленно загружается, очень тормозит")
        result = self.triager.triage(report)
        assert result.severity == Severity.HIGH

    def test_question_classified_low(self):
        report = UserReport(user_id="user1", message="Как построить график продаж?")
        result = self.triager.triage(report)
        assert result.severity == Severity.LOW

    def test_sql_keyword_classified_sql_engine(self):
        report = UserReport(user_id="user1", message="Ошибка в запросе SQL")
        result = self.triager.triage(report)
        assert result.category == Category.SQL_ENGINE

    def test_1c_keyword_classified_1c_integration(self):
        report = UserReport(user_id="user1", message="Не подключается к 1С")
        result = self.triager.triage(report)
        assert result.category == Category.ONEC_INTEGRATION

    def test_gost_keyword_classified_gost(self):
        report = UserReport(user_id="user1", message="Отчёт по ГОСТ не формируется")
        result = self.triager.triage(report)
        assert result.category == Category.GOST_REPORTING

    def test_slow_keyword_classified_performance(self):
        report = UserReport(user_id="user1", message="Всё долго и медленно грузится")
        result = self.triager.triage(report)
        assert result.category == Category.PERFORMANCE

    def test_ui_issue_classified_ui_ux(self):
        report = UserReport(user_id="user1", message="Неудобный интерфейс, кнопка не нажимается")
        result = self.triager.triage(report)
        assert result.category == Category.UI_UX

    def test_unrecognized_message_classified_other(self):
        report = UserReport(user_id="user1", message="abcdefg")
        result = self.triager.triage(report)
        assert result.category == Category.OTHER

    def test_critical_triggers_jira_and_alert(self):
        report = UserReport(user_id="user1", message="Ничего не работает, всё упало")
        result = self.triager.triage(report)
        assert Action.CREATE_JIRA_TICKET in result.actions
        assert Action.ALERT_ONCALL in result.actions

    def test_sql_error_adds_to_test_suite(self):
        report = UserReport(user_id="user1", message="Ошибка SQL запроса")
        result = self.triager.triage(report)
        assert Action.ADD_TO_SQL_TEST_SUITE in result.actions

    def test_ui_issue_pings_product_manager(self):
        report = UserReport(user_id="user1", message="Непонятный интерфейс, неудобно")
        result = self.triager.triage(report)
        assert Action.PING_PRODUCT_MANAGER in result.actions

    def test_low_severity_logs_only(self):
        report = UserReport(user_id="user1", message="Как сохранить график?")
        result = self.triager.triage(report)
        assert Action.LOG_ONLY in result.actions

    def test_component_field_influences_category(self):
        report = UserReport(user_id="user1", message="Не работает", component="sql_editor")
        result = self.triager.triage(report)
        assert result.category == Category.SQL_ENGINE

    def test_with_sql_query_classified_sql_engine(self):
        report = UserReport(user_id="user1", message="что-то странное", sql_query="SELECT * FROM x")
        result = self.triager.triage(report)
        assert result.category == Category.SQL_ENGINE

    def test_auto_response_generated(self):
        report = UserReport(user_id="user1", message="Ничего не работает")
        result = self.triager.triage(report)
        assert len(result.auto_response) > 10
        assert "Спасибо" in result.auto_response


class TestUserReport:
    def test_default_timestamp(self):
        report = UserReport(user_id="u1", message="test")
        assert "T" in report.timestamp

    def test_optional_fields(self):
        report = UserReport(
            user_id="u1",
            message="test",
            dashboard_id="dash-42",
            sql_query="SELECT 1",
            browser_info="Chrome 130",
        )
        assert report.dashboard_id == "dash-42"
        assert report.sql_query == "SELECT 1"
