# NLP→SQL Accuracy Benchmark — 50 queries with expected SQL

# Each entry: (russian_text, expected_sql_contains_keywords, table, expected_sql_oracle)
# expected_sql_oracle is optional — used for exact-match verification

QUERIES_V1: list[dict[str, Any]] = []

# ============================================================
# Simple SELECT
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q01",
        "text": "Покажи все продажи",
        "table": "sales",
        "keywords": ["SELECT", "FROM", "sales"],
        "must_have": ["SELECT", "FROM sales"],
        "must_not": ["INSERT", "DELETE", "DROP"],
    },
    {
        "id": "Q02",
        "text": "Список всех товаров",
        "table": "products",
        "keywords": ["SELECT", "FROM", "products"],
        "must_have": ["SELECT", "FROM products"],
    },
    {
        "id": "Q03",
        "text": "Выведи всех клиентов",
        "table": "customers",
        "keywords": ["SELECT", "FROM", "customers"],
        "must_have": ["SELECT", "FROM customers"],
    },
    {
        "id": "Q04",
        "text": "Все сотрудники компании",
        "table": "employees",
        "keywords": ["SELECT", "FROM", "employees"],
        "must_have": ["SELECT", "FROM employees"],
    },
    {
        "id": "Q05",
        "text": "Покажи 10 первых записей из продаж",
        "table": "sales",
        "keywords": ["SELECT", "FROM", "sales", "LIMIT"],
        "must_have": ["LIMIT 10"],
    },
])

# ============================================================
# Aggregation (SUM, AVG, COUNT)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q06",
        "text": "Общая выручка компании",
        "table": "sales",
        "keywords": ["SELECT", "SUM", "revenue", "FROM", "sales"],
        "must_have": ["SUM(revenue)"],
    },
    {
        "id": "Q07",
        "text": "Средняя зарплата сотрудников",
        "table": "employees",
        "keywords": ["SELECT", "AVG", "salary", "FROM", "employees"],
        "must_have": ["AVG(salary)"],
    },
    {
        "id": "Q08",
        "text": "Количество заказов",
        "table": "sales",
        "keywords": ["SELECT", "COUNT", "FROM", "sales"],
        "must_have": ["COUNT("],
    },
    {
        "id": "Q09",
        "text": "Максимальная цена товара",
        "table": "products",
        "keywords": ["SELECT", "MAX", "price", "FROM", "products"],
        "must_have": ["MAX(price)"],
    },
    {
        "id": "Q10",
        "text": "Минимальная стоимость товара",
        "table": "products",
        "keywords": ["SELECT", "MIN", "cost", "FROM", "products"],
        "must_have": ["MIN(cost)"],
    },
])

# ============================================================
# GROUP BY (категории, регионы, отделы)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q11",
        "text": "Выручка по регионам",
        "table": "sales",
        "keywords": ["SELECT", "region", "SUM", "revenue", "GROUP BY"],
        "must_have": ["SUM(revenue)", "GROUP BY region"],
    },
    {
        "id": "Q12",
        "text": "Количество продаж по категориям товаров",
        "table": "products",
        "keywords": ["SELECT", "category", "COUNT", "GROUP BY"],
        "must_have": ["COUNT(", "GROUP BY category"],
    },
    {
        "id": "Q13",
        "text": "Средняя зарплата по отделам",
        "table": "employees",
        "keywords": ["SELECT", "department", "AVG", "salary", "GROUP BY"],
        "must_have": ["AVG(salary)", "GROUP BY department"],
    },
    {
        "id": "Q14",
        "text": "Количество клиентов по сегментам",
        "table": "customers",
        "keywords": ["SELECT", "segment", "COUNT", "GROUP BY"],
        "must_have": ["COUNT(", "GROUP BY segment"],
    },
    {
        "id": "Q15",
        "text": "Суммарные продажи по товарам",
        "table": "sales",
        "keywords": ["SELECT", "product", "SUM", "GROUP BY"],
        "must_have": ["SUM(", "GROUP BY product"],
    },
])

# ============================================================
# ORDER BY + LIMIT (топы, рейтинги)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q16",
        "text": "Топ-10 товаров по продажам",
        "table": "sales",
        "keywords": ["SELECT", "product", "SUM", "ORDER BY", "DESC", "LIMIT 10"],
        "must_have": ["ORDER BY", "DESC", "LIMIT 10"],
    },
    {
        "id": "Q17",
        "text": "5 самых дорогих товаров",
        "table": "products",
        "keywords": ["SELECT", "price", "ORDER BY", "DESC", "LIMIT 5"],
        "must_have": ["ORDER BY price DESC", "LIMIT 5"],
    },
    {
        "id": "Q18",
        "text": "Регионы с наибольшей выручкой",
        "table": "sales",
        "keywords": ["SELECT", "region", "SUM(revenue)", "GROUP BY", "ORDER BY", "DESC"],
        "must_have": ["SUM(revenue)", "GROUP BY region", "ORDER BY", "DESC"],
    },
    {
        "id": "Q19",
        "text": "Самые активные клиенты за месяц",
        "table": "sales",
        "keywords": ["SELECT", "customer_id", "COUNT", "GROUP BY", "ORDER BY", "DESC"],
        "must_have": ["COUNT(", "GROUP BY customer_id", "ORDER BY", "DESC"],
    },
    {
        "id": "Q20",
        "text": "Отсортируй товары по цене от дешёвых к дорогим",
        "table": "products",
        "keywords": ["SELECT", "price", "ORDER BY", "ASC"],
        "must_have": ["ORDER BY price ASC"],
    },
])

# ============================================================
# WHERE (фильтрация)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q21",
        "text": "Продажи за последний месяц",
        "table": "sales",
        "keywords": ["SELECT", "FROM sales", "WHERE", "date"],
        "must_have": ["WHERE"],
    },
    {
        "id": "Q22",
        "text": "Товары дороже 10000 рублей",
        "table": "products",
        "keywords": ["SELECT", "FROM products", "WHERE", "price", ">"],
        "must_have": ["WHERE", "price > 10000"],
    },
    {
        "id": "Q23",
        "text": "Клиенты из Москвы",
        "table": "customers",
        "keywords": ["SELECT", "FROM customers", "WHERE", "region"],
        "must_have": ["WHERE", "region"],
    },
    {
        "id": "Q24",
        "text": "Сотрудники с зарплатой больше 100000",
        "table": "employees",
        "keywords": ["SELECT", "FROM employees", "WHERE", "salary", ">"],
        "must_have": ["WHERE", "salary > 100000"],
    },
    {
        "id": "Q25",
        "text": "Продажи за последний квартал",
        "table": "sales",
        "keywords": ["SELECT", "FROM sales", "WHERE", "date"],
        "must_have": ["WHERE"],
    },
])

# ============================================================
# WHERE + GROUP BY + ORDER BY (комплексные)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q26",
        "text": "Выручка по регионам за прошлый месяц",
        "table": "sales",
        "keywords": ["SELECT", "region", "SUM(revenue)", "FROM", "sales", "WHERE", "date", "GROUP BY region"],
        "must_have": ["SUM(revenue)", "GROUP BY region", "WHERE"],
    },
    {
        "id": "Q27",
        "text": "Топ-5 товаров по продажам в Москве",
        "table": "sales",
        "keywords": ["SELECT", "product", "SUM", "WHERE", "region", "GROUP BY", "ORDER BY", "LIMIT 5"],
        "must_have": ["WHERE", "GROUP BY", "ORDER BY", "DESC", "LIMIT 5"],
    },
    {
        "id": "Q28",
        "text": "Средний чек по регионам за этот год",
        "table": "sales",
        "keywords": ["SELECT", "region", "AVG(revenue)", "WHERE", "date", "GROUP BY"],
        "must_have": ["AVG(revenue)", "GROUP BY region", "WHERE"],
    },
    {
        "id": "Q29",
        "text": "Количество заказов по категориям дороже 5000",
        "table": "products",
        "keywords": ["SELECT", "category", "COUNT", "WHERE", "price", ">", "GROUP BY"],
        "must_have": ["WHERE price > 5000", "GROUP BY category"],
    },
    {
        "id": "Q30",
        "text": "Прибыль по категориям за прошлый год",
        "table": "products",
        "keywords": ["SELECT", "category", "price - cost", "GROUP BY"],
        "must_have": ["GROUP BY category"],
    },
])

# ============================================================
# JOIN
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q31",
        "text": "Продажи с названиями товаров",
        "table": "sales",
        "keywords": ["SELECT", "JOIN", "products", "ON"],
        "must_have": ["JOIN products"],
    },
    {
        "id": "Q32",
        "text": "Выручка по клиентам с их названиями",
        "table": "sales",
        "keywords": ["SELECT", "JOIN", "customers", "SUM", "GROUP BY"],
        "must_have": ["JOIN customers"],
    },
    {
        "id": "Q33",
        "text": "Сотрудники и их отделы с продажами",
        "table": "employees",
        "keywords": ["SELECT", "employees", "department"],
        "must_have": ["FROM employees"],
    },
    {
        "id": "Q34",
        "text": "Товары которые ни разу не продавались",
        "table": "products",
        "keywords": ["SELECT", "LEFT JOIN", "IS NULL"],
        "must_have": ["JOIN", "NULL"],
    },
    {
        "id": "Q35",
        "text": "Клиенты с суммой их покупок",
        "table": "customers",
        "keywords": ["SELECT", "JOIN", "sales", "SUM", "GROUP BY"],
        "must_have": ["JOIN sales", "SUM(", "GROUP BY"],
    },
])

# ============================================================
# HAVING
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q36",
        "text": "Регионы с выручкой больше 10 миллионов",
        "table": "sales",
        "keywords": ["SELECT", "region", "SUM(revenue)", "GROUP BY", "HAVING"],
        "must_have": ["SUM(revenue)", "GROUP BY region", "HAVING"],
    },
    {
        "id": "Q37",
        "text": "Категории где больше 100 товаров",
        "table": "products",
        "keywords": ["SELECT", "category", "COUNT", "GROUP BY", "HAVING"],
        "must_have": ["COUNT(", "GROUP BY category", "HAVING"],
    },
    {
        "id": "Q38",
        "text": "Отделы где средняя зарплата выше 150 тысяч",
        "table": "employees",
        "keywords": ["SELECT", "department", "AVG(salary)", "GROUP BY", "HAVING"],
        "must_have": ["AVG(salary)", "GROUP BY department", "HAVING"],
    },
])

# ============================================================
# Date/Time specific
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q39",
        "text": "Продажи за январь 2026 года",
        "table": "sales",
        "keywords": ["SELECT", "FROM sales", "WHERE", "date", "2026-01"],
        "must_have": ["WHERE", "date", "2026-01"],
    },
    {
        "id": "Q40",
        "text": "Выручка помесячно за 2026 год",
        "table": "sales",
        "keywords": ["SELECT", "date_trunc", "SUM(revenue)", "GROUP BY"],
        "must_have": ["SUM(revenue)", "GROUP BY"],
    },
    {
        "id": "Q41",
        "text": "Продажи за вчера",
        "table": "sales",
        "keywords": ["SELECT", "WHERE", "date", "CURRENT_DATE"],
        "must_have": ["WHERE"],
    },
    {
        "id": "Q42",
        "text": "Сравнение продаж по кварталам",
        "table": "sales",
        "keywords": ["SELECT", "SUM", "GROUP BY"],
        "must_have": ["SUM(", "GROUP BY"],
    },
])

# ============================================================
# Russian-specific (синонимы, аббревиатуры, падежи)
# ============================================================
QUERIES_V1.extend([
    {
        "id": "Q43",
        "text": "Сколько заработали в этом месяце",
        "table": "sales",
        "keywords": ["SELECT", "SUM(revenue)", "FROM sales"],
        "must_have": ["SUM(revenue)", "FROM sales"],
    },
    {
        "id": "Q44",
        "text": "Доход компании за год",
        "table": "sales",
        "keywords": ["SELECT", "SUM(revenue)", "FROM sales", "WHERE"],
        "must_have": ["SUM(revenue)", "FROM sales"],
    },
    {
        "id": "Q45",
        "text": "Объём реализации в штуках",
        "table": "sales",
        "keywords": ["SELECT", "SUM(units)", "FROM sales"],
        "must_have": ["SUM(units)"],
    },
    {
        "id": "Q46",
        "text": "Численность персонала по подразделениям",
        "table": "employees",
        "keywords": ["SELECT", "department", "COUNT", "GROUP BY"],
        "must_have": ["COUNT(", "GROUP BY department"],
    },
    {
        "id": "Q47",
        "text": "Рентабельность товарных категорий",
        "table": "products",
        "keywords": ["SELECT", "category", "price - cost", "GROUP BY"],
        "must_have": ["GROUP BY category"],
    },
    {
        "id": "Q48",
        "text": "Выручка в разрезе регионов и товаров",
        "table": "sales",
        "keywords": ["SELECT", "region", "product", "SUM(revenue)", "GROUP BY"],
        "must_have": ["SUM(revenue)", "GROUP BY"],
    },
    {
        "id": "Q49",
        "text": "Покупатели которые ничего не купили за полгода",
        "table": "customers",
        "keywords": ["SELECT", "LEFT JOIN", "IS NULL", "WHERE"],
        "must_have": ["JOIN", "NULL", "WHERE"],
    },
    {
        "id": "Q50",
        "text": "Динамика среднего чека по месяцам за текущий год",
        "table": "sales",
        "keywords": ["SELECT", "AVG(revenue)", "GROUP BY"],
        "must_have": ["AVG(revenue)", "GROUP BY"],
    },
])
