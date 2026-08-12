"""Unit tests for health checks — Level 11."""

import pytest
from gost_bi.monitoring.health_checks import (
    HealthIssue,
    HealthCheckResult,
    Severity,
)


class TestHealthCheckResult:
    def test_healthy_with_no_issues(self):
        result = HealthCheckResult(component="test")
        assert result.healthy

    def test_healthy_with_warning_only(self):
        result = HealthCheckResult(
            component="test",
            issues=[HealthIssue(Severity.WARNING, "test", "something is slow")],
        )
        assert result.healthy

    def test_not_healthy_with_critical(self):
        result = HealthCheckResult(
            component="test",
            issues=[HealthIssue(Severity.CRITICAL, "test", "connection refused")],
        )
        assert not result.healthy

    def test_degraded(self):
        result = HealthCheckResult(
            component="test",
            issues=[HealthIssue(Severity.WARNING, "test", "high latency")],
        )
        assert not result.degraded

    def test_latency_recorded(self):
        result = HealthCheckResult(component="test", latency_ms=234.5)
        assert result.latency_ms == pytest.approx(234.5)

    def test_timestamp_is_iso(self):
        result = HealthCheckResult(component="test")
        assert "T" in result.timestamp
        assert "+" in result.timestamp or "Z" in result.timestamp


class TestHealthIssue:
    def test_severity_values(self):
        assert Severity.OK.value == "OK"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.CRITICAL.value == "CRITICAL"

    def test_issue_has_timestamp(self):
        issue = HealthIssue(Severity.CRITICAL, "db", "down")
        assert "T" in issue.timestamp
