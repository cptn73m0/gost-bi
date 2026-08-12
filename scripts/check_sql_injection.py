"""
SQL Injection Pre-commit Hook.

Scans Python files for unsafe SQL concatenation patterns.
Blocks commits that contain raw SQL string building.
"""

import re
import sys
from pathlib import Path

UNSAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "f-string SQL",
        re.compile(r"""(?:execute|executemany|executescript)\s*\(\s*(?:f["']|["'].*?"\s*%|["'].*?"\s*\.format)"""),
    ),
    (
        "string concat SQL",
        re.compile(r"""(?:execute|executemany|executescript)\s*\(\s*["'][^"']*["']\s*\+"""),
    ),
    (
        "percent format SQL",
        re.compile(r"""(?:execute|executemany|executescript)\s*\(\s*["'][^"']*%[srd]\s*["']\s*%\s*\("""),
    ),
    (
        "raw string format SQL",
        re.compile(r"""(?:execute|executemany|executescript)\s*\(\s*["'][^"']*\{[^}]*\}"""),
    ),
]

SAFE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "parameterized query",
        re.compile(r"""execute\s*\(\s*["'][^"']*["']\s*,\s*\([^)]*\)"""),
    ),
]


def check_file(filepath: str) -> list[str]:
    errors: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    in_safe_block = False
    for i, line in enumerate(lines, start=1):
        if "# sql-injection: allow" in line.lower():
            in_safe_block = True
            continue
        if "# sql-injection: end" in line.lower():
            in_safe_block = False
            continue
        if in_safe_block:
            continue

        for name, pattern in SAFE_PATTERNS:
            if pattern.search(line):
                break
        else:
            for name, pattern in UNSAFE_PATTERNS:
                if pattern.search(line):
                    errors.append(f"{filepath}:{i}: [{name}] {line.strip()[:100]}")
    return errors


def main() -> int:
    exit_code = 0
    for filepath in sys.argv[1:]:
        if not filepath.endswith(".py"):
            continue
        if "superset/" in filepath or "venv/" in filepath:
            continue
        errors = check_file(filepath)
        for error in errors:
            print(f"❌ {error}")
            exit_code = 1
        if errors:
            print(f"   💡 Use parameterized queries: cursor.execute('SELECT * FROM t WHERE id = %s', (id,))")
            print(f"   💡 Or add '# sql-injection: allow' if this is intentional.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
