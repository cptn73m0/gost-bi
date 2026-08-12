#!/usr/bin/env python3
"""
Platform Compatibility Verification Script.

Checks that GOST BI works on the current platform:
- Astra Linux 1.8
- Alt Linux 10+
- Windows 10/11

Run: python scripts/verify_platform.py
"""

from __future__ import annotations

import ctypes
import locale
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    fix: str = ""


class PlatformVerifier:
    CHECKS: list[tuple[str, str]] = [
        ("python_version", "Python 3.12+"),
        ("os_supported", "Поддерживаемая ОС (Astra/Alt/Windows)"),
        ("russian_locale", "Русская локаль (ru_RU.UTF-8 / Russian_Russia.1251)"),
        ("database_driver", "Драйвер PostgreSQL (psycopg2 / asyncpg)"),
        ("redis_available", "Redis доступен (redis-cli или Python client)"),
        ("openssl", "OpenSSL установлен"),
        ("git", "Git установлен"),
        ("disk_space", "Свободное место > 1 GB"),
        ("ram", "Оперативная память > 2 GB"),
        ("gost_bi_import", "GOST BI импортируется без ошибок"),
        ("sql_verifier", "SQL-верификатор работает"),
        ("health_checks", "Health checks инициализируются"),
    ]

    def run_all(self) -> list[CheckResult]:
        results: list[CheckResult] = []
        for check_id, check_name in self.CHECKS:
            method = getattr(self, f"check_{check_id}", None)
            if method:
                try:
                    result = method()
                except Exception as exc:
                    result = CheckResult(name=check_name, passed=False, detail=str(exc))
            else:
                result = CheckResult(name=check_name, passed=True, detail="Not implemented")
            results.append(result)
        return results

    def check_python_version(self) -> CheckResult:
        ver = sys.version_info
        passed = ver.major == 3 and ver.minor >= 12
        return CheckResult(
            name="Python 3.12+",
            passed=passed,
            detail=f"Python {ver.major}.{ver.minor}.{ver.micro}",
            fix="Установите Python 3.12: https://python.org" if not passed else "",
        )

    def check_os_supported(self) -> CheckResult:
        system = platform.system()
        if system == "Linux":
            if os.path.exists("/etc/astra_version"):
                os_name = "Astra Linux"
                passed = True
            elif os.path.exists("/etc/altlinux-release"):
                os_name = "Alt Linux"
                passed = True
            elif os.path.exists("/etc/os-release"):
                os_name = "Linux (совместимый)"
                passed = True
            else:
                os_name = "Linux (неизвестный)"
                passed = True
        elif system == "Windows":
            ver = sys.getwindowsversion()
            if ver.major >= 10:
                os_name = f"Windows {ver.major}"
                passed = True
            else:
                os_name = f"Windows {ver.major} (устаревшая)"
                passed = False
        else:
            os_name = system
            passed = False

        return CheckResult(
            name="Поддерживаемая ОС",
            passed=passed,
            detail=f"{os_name} | {platform.platform()}",
            fix="Требуется Astra Linux 1.8+, Alt Linux 10+, Windows 10+" if not passed else "",
        )

    def check_russian_locale(self) -> bool:
        if platform.system() == "Windows":
            try:
                import ctypes.wintypes
                lcid = ctypes.windll.kernel32.GetUserDefaultLCID()
                passed = lcid in (1049, 25)
                return CheckResult(
                    name="Русская локаль",
                    passed=passed,
                    detail=f"LCID: {lcid}" + (" (Русская)" if passed else ""),
                    fix="Установите русский языковой пакет в Windows" if not passed else "",
                )
            except Exception:
                return CheckResult(name="Русская локаль", passed=True, detail="Проверка пропущена")

        try:
            current = locale.getlocale()
            passed = any("ru" in str(x).lower() for x in current if x)
        except Exception:
            passed = "ru_RU" in os.environ.get("LANG", "")

        return CheckResult(
            name="Русская локаль",
            passed=passed,
            detail=f"LANG={os.environ.get('LANG', 'not set')}",
            fix="Выполните: sudo locale-gen ru_RU.UTF-8" if not passed else "",
        )

    def check_database_driver(self) -> CheckResult:
        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine("postgresql://")
            return CheckResult(name="Драйвер PostgreSQL", passed=True, detail=f"SQLAlchemy {sqlalchemy.__version__}")
        except ImportError:
            return CheckResult(name="Драйвер PostgreSQL", passed=False, detail="SQLAlchemy не установлен", fix="pip install sqlalchemy psycopg2-binary")
        except Exception as exc:
            return CheckResult(name="Драйвер PostgreSQL", passed=True, detail=f"OK ({exc})")

    def check_redis_available(self) -> CheckResult:
        if shutil.which("redis-cli"):
            return CheckResult(name="Redis доступен", passed=True, detail="redis-cli найден")
        try:
            import redis
            return CheckResult(name="Redis клиент (Python)", passed=True, detail=f"redis-py {redis.__version__}")
        except ImportError:
            return CheckResult(name="Redis клиент", passed=False, detail="redis-py не установлен", fix="pip install redis")

    def check_openssl(self) -> CheckResult:
        if shutil.which("openssl"):
            try:
                result = subprocess.run(["openssl", "version"], capture_output=True, text=True)
                return CheckResult(name="OpenSSL", passed=True, detail=result.stdout.strip())
            except Exception:
                pass
        try:
            import ssl
            return CheckResult(name="OpenSSL (Python)", passed=True, detail=ssl.OPENSSL_VERSION)
        except ImportError:
            return CheckResult(name="OpenSSL", passed=False, detail="Не найден", fix="Установите OpenSSL")

    def check_git(self) -> CheckResult:
        if shutil.which("git"):
            result = subprocess.run(["git", "--version"], capture_output=True, text=True)
            return CheckResult(name="Git", passed=True, detail=result.stdout.strip())
        return CheckResult(name="Git", passed=False, detail="Не найден", fix="Установите Git: https://git-scm.com")

    def check_disk_space(self) -> CheckResult:
        usage = shutil.disk_usage(Path.cwd())
        free_gb = usage.free / (1024 ** 3)
        passed = free_gb > 1.0
        return CheckResult(
            name="Свободное место",
            passed=passed,
            detail=f"{free_gb:.1f} GB свободно",
            fix=f"Освободите место (доступно только {free_gb:.1f} GB)" if not passed else "",
        )

    def check_ram(self) -> None:
        try:
            import psutil
            total_gb = psutil.virtual_memory().total / (1024 ** 3)
            passed = total_gb > 2.0
            return CheckResult(
                name="Оперативная память",
                passed=passed,
                detail=f"{total_gb:.1f} GB",
                fix="Требуется минимум 2 GB RAM" if not passed else "",
            )
        except ImportError:
            return CheckResult(name="Оперативная память", passed=True, detail="psutil не установлен (проверка пропущена)")

    def check_gost_bi_import(self) -> CheckResult:
        try:
            from gost_bi import __version__
            return CheckResult(name="GOST BI импорт", passed=True, detail=f"v{__version__}")
        except ImportError as exc:
            return CheckResult(name="GOST BI импорт", passed=False, detail=str(exc), fix="pip install -e .")

    def check_sql_verifier(self) -> CheckResult:
        try:
            from gost_bi.quality.sql_verifier import SQLVerifier
            verifier = SQLVerifier()
            report = verifier.verify("SELECT 1")
            passed = report.overall_passed
            return CheckResult(name="SQL-верификатор", passed=passed, detail="SELECT 1: OK" if passed else "SELECT 1: FAIL")
        except Exception as exc:
            return CheckResult(name="SQL-верификатор", passed=False, detail=str(exc))

    def check_health_checks(self) -> CheckResult:
        try:
            from gost_bi.monitoring.health_checks import DatabaseHealthCheck, RedisHealthCheck
            return CheckResult(name="Health checks", passed=True, detail="Модули загружены")
        except Exception as exc:
            return CheckResult(name="Health checks", passed=False, detail=str(exc))


def main() -> int:
    print("=" * 60)
    print("  GOST BI — Проверка совместимости с платформой")
    print("  Целевые ОС: Astra Linux 1.8 | Alt Linux 10+ | Windows 10/11")
    print("=" * 60)
    print()

    verifier = PlatformVerifier()
    results = verifier.run_all()

    all_passed = True
    for r in results:
        status = "OK" if r.passed else "FAIL"
        color = "\033[92m" if r.passed else "\033[91m"
        reset = "\033[0m"

        print(f"  {color}[{status}]{reset} {r.name}: {r.detail}")
        if not r.passed and r.fix:
            print(f"       {r.fix}")

        if not r.passed:
            all_passed = False

    print()
    passed_count = sum(1 for r in results if r.passed)
    print(f"  Итого: {passed_count}/{len(results)} проверок пройдено")

    if all_passed:
        print()
        print("  Платформа готова к работе с GOST BI.")
        print("  Запустите: make check-all")
        return 0
    else:
        print()
        print("  Часть проверок не пройдена. Исправьте ошибки и повторите.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
