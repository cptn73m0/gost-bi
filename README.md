# GOST BI

Российская BI-платформа на ядре Apache Superset с AI-ускорением.

**Ключевые дифференциаторы:**
- Прямой коннектор к 1С:Предприятие (OData)
- Русский NLP→SQL: «покажи выручку по регионам» → дашборд
- ГОСТ-отчётность из коробки (бухгалтерский баланс, налоговая, статистика)
- Полностью российский стек: Astra Linux, Alt Linux, Windows, Tantor, Postgres Pro

## Целевые платформы

| Платформа | Статус | Установка |
|-----------|:---:|-----------|
| **Astra Linux SE 1.8** (Смоленск) | ✅ | `sudo bash scripts/install-astra.sh` |
| **Alt Linux 10+** (Сервер/Рабочая станция) | ✅ | `sudo bash scripts/install-alt.sh` |
| **Windows 10/11** | ✅ | `powershell -File scripts/install-windows.ps1` |

Проверка совместимости: `python scripts/verify_platform.py`

## Статус проекта

| Спринт | Статус |
|:---:|------|
| 0 — Инициализация | ✅ Завершён |
| 1 — Система самопроверки (уровни 0–12) | ✅ Завершён |
| 2 — Форк Superset + российский стек | ✅ Завершён |
| 3 — Уровни 6–9 (SQL-верификатор, безопасность) | ✅ Завершён |
| 4 — 1С OData-коннектор | ✅ Завершён |
| 5 — NLP→SQL (русский) | ✅ Завершён |
| 6 — ГОСТ-шаблонизатор | ✅ Завершён |
| 7 — MVP-сборка | 🔄 В процессе |
| 8 — Первый пилот | ⏳ Ожидает |

## Архитектура

```
┌──────────────────────────────────────────────────┐
│  Пользовательский слой                           │
│  React UI │ Мобильное приложение │ Встраивание   │
├──────────────────────────────────────────────────┤
│  API Gateway (FastAPI)                           │
│  Аутентификация │ Rate Limiting │ API-ключи      │
├──────────────────────────────────────────────────┤
│  Ядро BI (Apache Superset — форк)                │
│  SQL Lab │ Dashboard Builder │ Caching (Redis)   │
├──────────────────┬───────────────────────────────┤
│  AI Engine       │  Интеграционный слой           │
│  NLP→SQL (рус.)  │  1С OData │ ГОСТ-шаблоны      │
├──────────────────┴───────────────────────────────┤
│  Слой данных                                     │
│  Tantor SE │ Postgres Pro │ Arenadata │ ClickHouse│
└──────────────────────────────────────────────────┘
```

## 12-уровневая система самопроверки

| Ур. | Название | Когда | Блокирует |
|:---:|---------|-------|:---:|
| 0 | Pre-commit (ruff, mypy, bandit) | `git commit` | Коммит |
| 1 | Unit-тесты (<30 сек) | CI / push | MR |
| 2 | Интеграционные тесты (<5 мин) | CI / MR | MR |
| 3 | E2E тесты (Playwright) | CI / MR | MR |
| 4 | Property-based + фаззинг | Nightly | Релиз |
| 5 | Визуальные регрессии | CI / UI MR | MR |
| 6 | SQL-верификатор | CI / SQL MR | MR |
| 7 | Консистентность данных | Nightly | Деплой |
| 8 | Нагрузочное / бенчмаркинг | Weekly | Релиз |
| 9 | Сканирование безопасности | CI / Nightly | MR / Релиз |
| 10 | AI код-ревью (Claude Code) | CI / MR | Предупреждение |
| 11 | Runtime health-checks | Production | Авторестарт |
| 12 | User feedback loop | Production | Автотриаж |

## Стек технологий

| Слой | Технология |
|------|-----------|
| Ядро BI | Apache Superset 5.x (форк) |
| API | FastAPI |
| Frontend | React 18 + TypeScript + Ant Design |
| СУБД | Tantor SE / Postgres Pro |
| Кеш | Redis |
| Очереди | Celery |
| AI | YandexGPT / GigaChat API + локальные модели |
| Контейнеризация | Docker + Kubernetes |

## Быстрый старт

```bash
# Установка
pip install -e ".[dev]"
pre-commit install

# Проверка платформы
python scripts/verify_platform.py

# Все проверки
make check-all

# Запуск (только API)
uvicorn gost_bi.core.app:app --reload

# Запуск с Tantor/Redis (Docker)
docker compose -f docker/docker-compose.tantor.yml up -d

# Форк Superset
python scripts/setup_superset_fork.py

# Проверка
curl http://localhost:8088/api/health
```

## Лицензия

Apache License 2.0 — наследуется от Superset.

## Репозиторий

https://github.com/cptn73m0/gost-bi
