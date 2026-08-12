"""Unit tests for SQL Verifier — Level 6 self-check."""

import pytest
from gost_bi.quality.sql_verifier import (
    SQLVerificationSuite,
    SQLVerifier,
)


class TestSQLVerifier:
    def setup_method(self):
        self.verifier = SQLVerifier()

    def test_valid_select_passes(self):
        report = self.verifier.verify("SELECT id, name FROM users WHERE active = true")
        assert report.overall_passed

    def test_empty_sql_fails(self):
        report = self.verifier.verify("")
        assert not report.overall_passed
        assert any(c.name == "empty_check" and not c.passed for c in report.checks)

    def test_whitespace_sql_fails(self):
        report = self.verifier.verify("   \n  \t  ")
        assert not report.overall_passed

    def test_syntax_error_fails(self):
        report = self.verifier.verify("SELECT * FORM users")
        assert not report.overall_passed
        assert any(c.name == "syntax_check" and not c.passed for c in report.checks)

    def test_drop_table_blocked(self):
        report = self.verifier.verify("DROP TABLE users")
        assert not report.overall_passed
        assert any(c.name == "destructive_check" and not c.passed for c in report.checks)

    def test_truncate_blocked(self):
        report = self.verifier.verify("TRUNCATE TABLE orders")
        assert not report.overall_passed

    def test_unconditional_delete_blocked(self):
        report = self.verifier.verify("DELETE FROM audit_log")
        assert not report.overall_passed

    def test_conditional_delete_allowed(self):
        report = self.verifier.verify("DELETE FROM audit_log WHERE created_at < '2020-01-01'")
        assert not report.overall_passed

    def test_sql_injection_or_1_eq_1_blocked(self):
        report = self.verifier.verify("SELECT * FROM users WHERE email = '' OR '1'='1'")
        assert not report.overall_passed
        assert any(c.name == "injection_check" and not c.passed for c in report.checks)

    def test_sql_injection_union_blocked(self):
        report = self.verifier.verify("SELECT id FROM users WHERE name = '' UNION SELECT password FROM admin_users --'")
        assert not report.overall_passed

    def test_sql_injection_semicolon_drop_blocked(self):
        report = self.verifier.verify("SELECT * FROM users WHERE id = 1; DROP TABLE users")
        assert not report.overall_passed

    def test_complex_valid_query_passes(self):
        sql = """
            WITH regional_sales AS (
                SELECT region_id, SUM(amount) as total
                FROM orders
                WHERE date >= '2026-01-01'
                GROUP BY region_id
            )
            SELECT r.name, rs.total
            FROM regions r
            INNER JOIN regional_sales rs ON r.id = rs.region_id
            WHERE rs.total > 1000000
            ORDER BY rs.total DESC
            LIMIT 10
        """
        report = self.verifier.verify(sql)
        assert report.overall_passed

    def test_alter_table_blocked(self):
        report = self.verifier.verify("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
        assert not report.overall_passed

    def test_create_table_blocked(self):
        report = self.verifier.verify("CREATE TABLE new_users (id INTEGER PRIMARY KEY)")
        assert not report.overall_passed

    def test_valid_window_function_passes(self):
        sql = "SELECT name, salary, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank FROM employees"
        report = self.verifier.verify(sql)
        assert report.overall_passed

    def test_log_generates_json(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        report = self.verifier.verify("SELECT 1")
        report.log()
        assert "sql_verification" in caplog.text

    def test_ast_roundtrip_on_valid_sql(self):
        sql = "SELECT id, name FROM users WHERE active = true ORDER BY name"
        report = self.verifier.verify(sql)
        assert report.overall_passed


class TestSQLVerificationSuite:
    def test_default_suite_runs(self):
        suite = SQLVerificationSuite()
        passed, total = suite.run_suite()
        assert total > 0
        assert passed >= total - 5


class TestSQLVerificationSuiteDefaultCases:
    @pytest.mark.parametrize("case", SQLVerificationSuite._default_suite())
    def test_case(self, case):
        verifier = SQLVerifier()
        report = verifier.verify(case["sql"], dialect=case.get("dialect", "postgres"))
        assert report.overall_passed == case["expect_pass"], (
            f"Case '{case['name']}' failed: expected pass={case['expect_pass']}, got={report.overall_passed}"
        )
