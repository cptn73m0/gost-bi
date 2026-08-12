"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_sql_queries():
    return {
        "valid_simple": "SELECT id, name FROM users WHERE active = true",
        "valid_complex": """
            WITH regional_sales AS (
                SELECT region, SUM(amount) AS total
                FROM orders WHERE date >= '2026-01-01'
                GROUP BY region
            )
            SELECT * FROM regional_sales WHERE total > 1000000
        """,
        "invalid_syntax": "SELECT * FORM users",
        "injection": "SELECT * FROM users WHERE email = '' OR '1'='1'",
        "destructive": "DROP TABLE users",
    }
