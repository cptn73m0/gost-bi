"""
Destructive SQL Pre-commit Hook.

Scans Python files for hardcoded destructive SQL statements
(DROP, TRUNCATE, unconditional DELETE/UPDATE).
"""

import re
import sys
from pathlib import Path

DESTRUCTIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("DROP TABLE", re.compile(r"['\"]DROP\s+TABLE\s", re.IGNORECASE)),
    ("DROP DATABASE", re.compile(r"['\"]DROP\s+DATABASE\s", re.IGNORECASE)),
    ("DROP SCHEMA", re.compile(r"['\"]DROP\s+SCHEMA\s", re.IGNORECASE)),
    ("TRUNCATE", re.compile(r"['\"]TRUNCATE\s+(TABLE\s+)?", re.IGNORECASE)),
    ("DELETE without WHERE", re.compile(r"['\"]DELETE\s+FROM\s+\w+['\"]\s*(?!.*\bWHERE\b)", re.IGNORECASE)),
    ("UPDATE without WHERE", re.compile(r"['\"]UPDATE\s+\w+\s+SET\s+.+?['\"]\s*(?!.*\bWHERE\b)", re.IGNORECASE)),
]


def check_file(filepath: str) -> list[str]:
    errors: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, start=1):
        if "# destructive-sql: allow" in line.lower():
            continue

        for name, pattern in DESTRUCTIVE_PATTERNS:
            if pattern.search(line):
                errors.append(f"{filepath}:{i}: [{name}] {line.strip()[:100]}")

    return errors


def main() -> int:
    exit_code = 0
    for filepath in sys.argv[1:]:
        if not filepath.endswith(".py"):
            continue
        if "superset/" in filepath or "migrations/" in filepath or "venv/" in filepath:
            continue
        errors = check_file(filepath)
        for error in errors:
            print(f"🔴 {error}")
            exit_code = 1
    if exit_code != 0:
        print("   💡 Hardcoded destructive SQL is forbidden in application code.")
        print("   💡 Use migrations (Alembic) for schema changes.")
        print("   💡 Add '# destructive-sql: allow' if this is intentional (test fixtures).")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
