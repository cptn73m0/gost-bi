# GOST BI

Российская BI-платформа на ядре Apache Superset с AI-ускорением.

**Ключевые дифференциаторы:**
- Прямой коннектор к 1С:Предприятие (OData)
- Русский NLP→SQL: «покажи выручку по регионам» → дашборд
- ГОСТ-отчётность из коробки (бухгалтерский баланс, налоговая, статистика)
- Полностью российский стек: Astra Linux, Tantor, Postgres Pro, Arenadata

## Статус

**Спринт 0:** Инициализация проекта.

## Стек

| Слой | Технология |
|------|-----------|
| Ядро BI | Apache Superset (форк) |
| API | FastAPI |
| Frontend | React 18 + TypeScript + Ant Design |
| СУБД | Tantor SE / Postgres Pro |
| AI | YandexGPT / GigaChat API + локальные модели |
| Контейнеризация | Docker + Kubernetes |

## Лицензия

Apache License 2.0 — наследуется от Superset.

## Разработка

```bash
pip install -e ".[dev]"
pre-commit install
make check-all
```
