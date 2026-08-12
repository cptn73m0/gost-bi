import { useState } from "react";

interface DataTableProps {
  columns: { key: string; title: string; width?: string }[];
  rows: Record<string, string | number>[];
  pageSize?: number;
}

export function DataTable({ columns, rows, pageSize = 10 }: DataTableProps) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(rows.length / pageSize);
  const visible = rows.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} style={col.width ? { width: col.width } : undefined}>
                  {col.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ textAlign: "center", padding: 32, color: "var(--text-disabled)" }}>
                  Нет данных для отображения
                </td>
              </tr>
            ) : (
              visible.map((row, i) => (
                <tr key={i}>
                  {columns.map((col) => (
                    <td key={col.key}>{row[col.key] ?? "—"}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 8,
            padding: "12px 0 0",
            fontSize: "var(--font-sm)",
          }}
        >
          <span style={{ color: "var(--text-tertiary)" }}>
            {page * pageSize + 1}–{Math.min((page + 1) * pageSize, rows.length)} из {rows.length}
          </span>
          <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
            ← Назад
          </button>
          <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
            Вперёд →
          </button>
        </div>
      )}
    </div>
  );
}
