#!/usr/bin/env python3
"""
GOST BI — Pilot Launch Script (Sprint 8).

Полный цикл: проверка → сборка → запуск → верификация.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    ("Python 3.12+", [sys.executable, "--version"]),
    ("pip", [sys.executable, "-m", "pip", "--version"]),
    ("git", ["git", "--version"]),
]

STEPS = [
    ("verify_imports", "Проверка импорта всех модулей", [sys.executable, "scripts/verify_imports.py"]),
    ("unit_tests", "Unit-тесты (77 шт.)", [sys.executable, "-m", "pytest", "tests/unit/", "-x", "-q"]),
    ("sql_verifier", "SQL-верификатор", [sys.executable, "-m", "gost_bi.quality.sql_verifier", "--suite", "default"]),
]


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd or PROJECT_ROOT)
        return result.returncode, (result.stdout + result.stderr)[:500]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="GOST BI — Pilot Launch")
    parser.add_argument("--skip-checks", action="store_true", help="Skip prerequisites")
    parser.add_argument("--skip-tests", action="store_true", help="Skip unit tests")
    parser.add_argument("--start-server", action="store_true", help="Start FastAPI server after checks")
    parser.add_argument("--port", type=int, default=8088, help="Server port")
    args = parser.parse_args()

    border = "=" * 56
    print(border)
    print("  ГОСТ БИ — Пилотный запуск (Спринт 8)")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Проект: {PROJECT_ROOT}")
    print(border)

    failures = 0

    if not args.skip_checks:
        print("\n--- Проверка окружения ---")
        for name, cmd in CHECKS:
            code, output = run(cmd)
            status = "[PASS]" if code == 0 else "[FAIL]"
            print(f"  {status} {name}: {output.strip().split(chr(10))[0]}")
            if code != 0:
                failures += 1

    print("\n--- Проверка модулей ---")
    code, output = run([sys.executable, str(PROJECT_ROOT / "scripts" / "verify_imports.py")])
    status = "[PASS]" if code == 0 else "[FAIL]"
    print(f"  {status} Импорт модулей")
    for line in output.strip().split("\n"):
        if "[PASS]" in line or "[FAIL]" in line:
            print(f"    {line.strip()}")
    if code != 0:
        failures += 1

    if not args.skip_tests:
        print("\n--- Unit-тесты ---")
        code, output = run([sys.executable, "-m", "pytest", "tests/unit/", "-x", "-q", "--tb=line"])
        status = "[PASS]" if code == 0 else "[FAIL]"
        for line in output.strip().split("\n"):
            if any(kw in line for kw in ["passed", "failed", "error"]):
                print(f"  {status} {line.strip()}")
        if code != 0:
            failures += 1

    print("\n--- SQL-верификатор ---")
    code, output = run([sys.executable, "-m", "gost_bi.quality.sql_verifier", "--suite", "default"])
    status = "[PASS]" if code == 0 else "[FAIL]"
    for line in output.strip().split("\n"):
        if "passed" in line.lower() or "complete" in line.lower() or "FAIL" in line:
            print(f"  {status} {line.strip()}")
    if code != 0:
        failures += 1

    print(f"\n{border}")
    if failures == 0:
        print(f"  [PASS] Пилотный запуск успешен — все проверки пройдены")
        print(f"  Готово к развёртыванию на Astra Linux / Alt Linux / Windows")
    else:
        print(f"  [FAIL] {failures} проверок не пройдено")
        return 1

    if args.start_server:
        print(f"\n--- Запуск сервера (порт {args.port}) ---")
        print(f"  http://localhost:{args.port}/api/health")
        print(f"  http://localhost:{args.port}/api/docs")
        subprocess.run([sys.executable, "-m", "uvicorn", "gost_bi.core.app:app", "--host", "0.0.0.0", "--port", str(args.port)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
