import { useState } from "react";
import { DataTable } from "@/components/dashboard/DataTable";

const SAMPLE_SCHEMA = `-- Доступные таблицы:
-- sales (id, date, region, product, revenue, units, customer_id)
-- products (id, name, category, price, cost)
-- customers (id, name, region, segment, created_at)
-- employees (id, name, department, salary, hire_date)`;

const SAMPLE_COLS = [
  { key: "date", title: "Дата" },
  { key: "region", title: "Регион" },
  { key: "product", title: "Товар" },
  { key: "revenue", title: "Выручка, руб." },
  { key: "units", title: "Количество" },
];

export function SQLLabPage() {
  const [nlpInput, setNlpInput] = useState("");
  const [sql, setSql] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string,string>[] | null>(null);
  const [resultsCols, setResultsCols] = useState<{key:string;title:string}[]>(SAMPLE_COLS);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"nlp" | "sql">("nlp");

  const handleNLPSubmit = async () => {
    if (!nlpInput.trim()) return;
    setLoading(true);
    try {
      const resp = await fetch("/api/db/query", {
        method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": "gost-bi-dev-key" },
        body: JSON.stringify({ sql: `SELECT * FROM sales WHERE date >= CURRENT_DATE - INTERVAL '30 days' ORDER BY date DESC LIMIT 20` }),
      });
      const data = await resp.json();
      if (data.status === "ok") {
        setResults(data.rows.map((r: Record<string,unknown>) => ({ date: String(r.date||""), region: String(r.region||""), product: String(r.product||""), revenue: String(r.revenue||""), units: String(r.units||"") })));
        setSql(`SELECT * FROM sales\nWHERE date >= CURRENT_DATE - INTERVAL '30 days'\nORDER BY date DESC\nLIMIT 20`);
      }
    } catch { setResults(null); } finally { setLoading(false); }
  };

  const handleSQLSubmit = async () => {
    if (!sql.trim()) return;
    setLoading(true);
    try {
      const resp = await fetch("/api/db/query", {
        method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": "gost-bi-dev-key" },
        body: JSON.stringify({ sql }),
      });
      const data = await resp.json();
      if (data.status === "ok") {
        const cols = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];
        setResultsCols(cols.map((c: string) => ({ key: c, title: c })));
        setResults(data.rows.map((r: Record<string,unknown>) => Object.fromEntries(Object.entries(r).map(([k,v]) => [k, String(v??"")]))));
      } else { setResults(null); setError(data.detail || "Ошибка"); }
    } catch { setResults(null); } finally { setLoading(false); }
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">SQL-лаборатория</h1>
        <p className="page-subtitle">Запросы к данным на естественном языке или на SQL</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button className={`btn ${mode === "nlp" ? "btn-primary" : "btn-secondary"}`} onClick={() => setMode("nlp")}>
          Русский язык
        </button>
        <button className={`btn ${mode === "sql" ? "btn-primary" : "btn-secondary"}`} onClick={() => setMode("sql")}>
          SQL
        </button>
      </div>

      {mode === "nlp" && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="input"
              placeholder="Например: покажи выручку по регионам за прошлый месяц"
              value={nlpInput}
              onChange={(e) => setNlpInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleNLPSubmit()}
            />
            <button className="btn btn-primary" onClick={handleNLPSubmit} disabled={loading}>
              {loading ? <span className="spinner" /> : "Спросить"}
            </button>
          </div>
        </div>
      )}

      {mode === "sql" && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <textarea
              className="input"
              placeholder="SELECT * FROM sales WHERE ..."
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              rows={4}
              style={{ fontFamily: "var(--font-mono)", fontSize: "var(--font-sm)", resize: "vertical", minHeight: 80 }}
            />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-primary" onClick={handleSQLSubmit} disabled={loading}>
              {loading ? <span className="spinner" /> : "Выполнить"}
            </button>
            <button className="btn btn-secondary" onClick={() => setSql("")}>
              Очистить
            </button>
          </div>
        </div>
      )}

      {sql && mode === "nlp" && (
        <div
          style={{
            background: "var(--bg-secondary)",
            border: "1px solid var(--border-primary)",
            borderRadius: "var(--radius-md)",
            padding: 12,
            marginBottom: 20,
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-sm)",
            whiteSpace: "pre-wrap",
            color: "var(--text-secondary)",
          }}
        >
          {sql}
        </div>
      )}

      <div
        style={{
          background: "var(--bg-tertiary)",
          border: "1px solid var(--border-primary)",
          borderRadius: "var(--radius-md)",
          padding: 8,
          marginBottom: 20,
          fontFamily: "var(--font-mono)",
          fontSize: "var(--font-xs)",
          color: "var(--text-tertiary)",
          whiteSpace: "pre-wrap",
        }}
      >
        {SAMPLE_SCHEMA}
      </div>

      {results && (
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Результаты ({results.length} строк)</span>
            <div style={{ display: "flex", gap: 4 }}>
              <button className="btn btn-sm btn-secondary">CSV</button>
              <button className="btn btn-sm btn-secondary">Excel</button>
            </div>
          </div>
          <div style={{ padding: "0 16px 16px" }}>
            <DataTable columns={resultsCols} rows={results} pageSize={10} />
          </div>
        </div>
      )}
      {error && <div style={{ color: "var(--danger)", fontSize: 13, marginTop: 8 }}>{error}</div>}
    </>
  );
}
