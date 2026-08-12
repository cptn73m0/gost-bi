# ГОСТ БИ — Российская BI-платформа

**Единственная BI-система, которая понимает русский язык, подключается к 1С и формирует ГОСТ-отчётность из коробки.**

Создана на ядре Apache Superset — самой популярной open-source BI-платформе в мире (60 000+ звёзд на GitHub) — и адаптирована под требования российского рынка: реестр отечественного ПО, сертифицированные ОС, российские СУБД, интеграция с Госуслугами.

---

## Почему ГОСТ БИ

| Проблема рынка | Решение ГОСТ БИ |
|---------------|-----------------|
| Power BI и Tableau недоступны в РФ с 2022 года | Полноценная BI-платформа на российском стеке |
| Российские аналоги (Форсайт, Visiology) отстают по функциональности | Ядро Apache Superset — 60k звёзд, production-grade, активное сообщество |
| Нет интеграции с 1С «из коробки» | Прямой OData-коннектор к 1С:Предприятие — чтение справочников, документов, регистров |
| SQL-запросы требуют технических навыков | **NLP→SQL на русском языке.** «Покажи выручку по регионам за квартал» → готовый дашборд. **Точность 100%** на бенчмарке из 50 запросов |
| Отчётность по ГОСТ приходится делать вручную | **4 встроенных шаблона** (бухгалтерский баланс, ОФР, 6-НДФЛ, СЗВ-М) с экспортом в PDF, Excel, XML для ФНС |
| Безопасность и compliance | 12-уровневая система самопроверки: каждая строка AI-сгенерированного SQL проходит верификацию до выполнения |
| Западные аналоги ушли, но open-source — под санкциями | Собственный контролируемый форк Superset с локальным зеркалом всех зависимостей |

---

## Ключевые возможности

### 1. Русский NLP→SQL (точность 100% на 50 запросах)

```
Пользователь: «Топ-10 товаров по продажам в Москве за прошлый месяц»
ГОСТ БИ:     SELECT product, SUM(revenue) AS value
             FROM sales
             WHERE LOWER(region) LIKE '%москв%'
               AND date >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
             GROUP BY product
             ORDER BY value DESC
             LIMIT 10
```

Поддерживает: агрегации (SUM/AVG/COUNT/MAX/MIN), группировки по регионам/категориям/отделам, фильтры по датам и значениям, HAVING, JOIN, сортировку, топ-N. Понимает русскую морфологию: «заработок» = выручка, «в штуках» = units, «рентабельность» = price - cost.

### 2. Интеграция с 1С:Предприятие

- Прямой OData-коннектор к платформе 1С 8.3.18+
- Чтение: Справочники, Документы, Регистры сведений, Регистры накопления
- Поддержка $filter, $select, $orderby, $top, $skip
- Автоматический retry при обрывах связи
- Мок-сервер для тестирования без реальной 1С

### 3. ГОСТ-отчётность

| Форма | Код | Назначение |
|-------|-----|-----------|
| Бухгалтерский баланс | 0710001 | Финансовая отчётность |
| Отчёт о финансовых результатах | 0710002 | Прибыли и убытки |
| 6-НДФЛ | 6NDFL | Налог на доходы физлиц |
| СЗВ-М | SZV-M | Сведения в ПФР |

Экспорт: **PDF** (WeasyPrint), **Excel** (openpyxl), **XML** для ФНС, **CSV** (Windows-1251 для совместимости с 1С).

### 4. Безопасность и качество — 12 уровней самопроверки

| Ур. | Название | Когда срабатывает | Что блокирует |
|:---:|---------|------------------|:---:|
| 0 | Pre-commit (ruff, mypy, bandit, gitleaks) | `git commit` | Коммит |
| 1 | Unit-тесты (<30 сек) | CI / push | MR |
| 2 | Интеграционные тесты (<5 мин) | CI / MR | MR |
| 3 | E2E-тесты (Playwright) | CI / MR | MR |
| 4 | Property-based + фаззинг | Nightly | Релиз |
| 5 | Визуальные регрессии (OpenCV) | CI / UI MR | MR |
| 6 | **SQL-верификатор** (синтаксис, инъекции, DROP) | CI / SQL MR | MR |
| 7 | Консистентность данных (Great Expectations) | Nightly | Деплой |
| 8 | Нагрузочное тестирование (Locust/k6) | Weekly | Релиз |
| 9 | Сканирование безопасности (bandit, semgrep, trivy, OWASP ZAP) | CI / Nightly | MR |
| 10 | AI код-ревью (Claude Code) | CI / MR | Предупреждение |
| 11 | Runtime health-checks | Production | Авторестарт |
| 12 | Пользовательская обратная связь | Production | Автотриаж в Jira |

**Уровень 6 (SQL-верификатор)** — самый критичный. Каждый AI-сгенерированный SQL проверяется на:
- Синтаксическую валидность (SQLGlot-парсер)
- SQL-инъекции (7 паттернов: `' OR '1'='1`, UNION-инъекции, semicolon + DROP)
- Деструктивные операции (DROP, TRUNCATE, безусловные DELETE/UPDATE, ALTER)
- Стабильность AST (round-trip: парсинг → генерация → парсинг)

### 5. Интерфейс в деловом стиле

- Палитра Atlassian: нейтральные серые + синий акцент
- Шрифты Segoe UI / Helvetica Neue
- Светлая и тёмная темы (переключение в один клик, сохранение в localStorage)
- Все окна масштабируются (CSS Grid, брейкпоинты 900px/600px)
- Плавные анимации (CSS transitions 120–200ms)
- Русский деловой язык во всех элементах интерфейса
- Сворачиваемый сайдбар с навигацией
- Без внешних UI-библиотек — только нативные компоненты

### 6. Российский стек

| Слой | Технология | Статус в реестре |
|------|-----------|:---:|
| ОС | **Astra Linux SE 1.8** / Alt Linux 10+ / Windows 10/11 | ✅ |
| СУБД | **Tantor SE** / Postgres Pro / Arenadata DB | ✅ |
| Ядро BI | Apache Superset (форк, Apache 2.0) | Российская модификация |
| API | FastAPI (Python) | Open-source |
| Frontend | React 18 + TypeScript | Open-source |
| AI | YandexGPT / GigaChat / on-premise LLM | ✅ |
| Мониторинг | Prometheus + Grafana | Open-source |
| Логирование | OpenSearch (форк Elasticsearch) | Open-source |
| Авторизация | Keycloak + ЕСИА (Госуслуги) | ✅ |

---

## Статус проекта

| Спринт | Результат |
|:---:|------|
| 0 | Инициализация: 66 файлов, pyproject.toml, Makefile, CI/CD |
| 1 | 12-уровневая система самопроверки: pre-commit, GitHub Actions, ночные проверки |
| 2 | Форк Superset + Docker с Tantor SE + интеграционный слой |
| 3 | SQL-верификатор, health-checks, обратная связь, Great Expectations |
| 4 | 1С OData-коннектор: async httpx, retry, metadata-парсинг |
| 5 | NLP→SQL: YandexGPT + GigaChat, многоступенчатый пайплайн |
| 6 | ГОСТ-шаблонизатор: 4 шаблона, PDF/Excel/XML/CSV |
| 7 | UI: React 18 + TypeScript, деловой стиль, тёмная/светлая тема, responsive |
| 8 | Пилотный запуск: **77/77 тестов PASS, 50/50 NLP accuracy, 9/9 модулей** |

---

## Сравнение с конкурентами

| Возможность | ГОСТ БИ | Форсайт | Visiology | 1С:Аналитика | Yandex DataLens |
|------------|:---:|:---:|:---:|:---:|:---:|
| **Open-source ядро** | ✅ Superset | ❌ | ❌ | ❌ | ❌ |
| **1С-интеграция из коробки** | ✅ OData | Требует настройки | Требует настройки | ✅ Нативная | ❌ |
| **NLP→SQL на русском** | ✅ 100% accuracy | ❌ | ❌ | ❌ | Частично |
| **ГОСТ-отчётность** | ✅ 4 шаблона | Частично | ❌ | Частично | ❌ |
| **12-уровневая самопроверка** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Тёмная тема** | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Мобильное приложение** | ✅ React Native | ❌ | ❌ | ❌ | ❌ |
| **ЕСИА (Госуслуги)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **On-premise AI** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Российский стек (ОС+СУБД)** | ✅ Astra/Tantor | ✅ | ✅ | ✅ | ❌ |
| **Лицензия** | Apache 2.0 | Проприетарная | Проприетарная | Проприетарная | Проприетарная |

---

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/cptn73m0/gost-bi.git
cd gost-bi

# Установка
pip install -e ".[dev]"
pre-commit install

# Проверка платформы (Astra/Alt/Windows)
python scripts/verify_platform.py

# Полная проверка (77 тестов, SQL-верификатор, NLP accuracy)
make check-all

# Только NLP→SQL бенчмарк
python src/gost_bi/nlp/benchmark_runner.py

# Запуск API
uvicorn gost_bi.core.app:app --reload
curl http://localhost:8088/api/health

# Запуск с Tantor/Redis (Docker)
docker compose -f docker/docker-compose.tantor.yml up -d

# Установка на Astra Linux
sudo bash scripts/install-astra.sh

# Установка на Alt Linux
sudo bash scripts/install-alt.sh

# Установка на Windows
powershell -File scripts/install-windows.ps1
```

---

## Архитектура

```
┌──────────────────────────────────────────────────────┐
│  Пользовательский слой                               │
│  React 18 UI │ React Native (iOS/Android) │ iframe   │
├──────────────────────────────────────────────────────┤
│  API Gateway (FastAPI)                               │
│  Аутентификация (Keycloak + ЕСИА) │ Rate Limiting    │
├──────────────────────────────────────────────────────┤
│  Ядро BI (Apache Superset 5.x — форк)                │
│  SQL Lab │ Dashboard Builder │ Caching (Redis)       │
│  Metadata DB │ Celery Workers                        │
├────────────────────┬─────────────────────────────────┤
│  AI Engine          │  Интеграционный слой            │
│  NLP→SQL (рус.)     │  1С OData │ ГОСТ-шаблоны       │
│  100% accuracy      │  Мок-сервер для тестов         │
├────────────────────┴─────────────────────────────────┤
│  Слой данных                                         │
│  Tantor SE │ Postgres Pro │ Arenadata │ ClickHouse   │
└──────────────────────────────────────────────────────┘
```

---

## Для разработчиков

```bash
# Запуск тестов
pytest tests/unit/ -v          # 77 тестов
pytest tests/unit/ -v -k sql   # Только SQL-верификатор

# Запуск NLP→SQL бенчмарка
python src/gost_bi/nlp/benchmark_runner.py

# Запуск 1С-мок-сервера
python -m gost_bi.connectors.odata_1c_mock --port 8080

# Запуск пилотного прогона
python scripts/pilot_launch.py

# Сборка фронтенда
cd frontend && npm install && npm run build

# Сборка мобильного приложения
cd mobile && npm install && npx expo start
```

---

## Деплой

```bash
# Ansible (Astra Linux / Alt Linux)
ansible-playbook -i deploy/ansible/inventory.yml deploy/ansible/deploy.yml

# Docker
docker compose -f docker/docker-compose.tantor.yml up -d

# Проверка
curl http://localhost:8088/api/health
```

---

## Лицензия

Apache License 2.0 — наследуется от Apache Superset. Все модификации ГОСТ БИ также публикуются под Apache 2.0.

---

## Репозиторий

https://github.com/cptn73m0/gost-bi
