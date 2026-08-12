import { useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { DataTable } from "@/components/dashboard/DataTable";

const USERS = [
  { login: "developer", full_name: "Разработчик ГОСТ БИ", roles: "admin", last_login: "2026-08-12 14:30", status: "active" },
  { login: "analyst", full_name: "Аналитик (демо)", roles: "analyst", last_login: "2026-08-12 10:15", status: "active" },
  { login: "viewer", full_name: "Зритель (демо)", roles: "viewer", last_login: "2026-08-11 18:45", status: "active" },
  { login: "auditor", full_name: "Аудитор", roles: "auditor", last_login: "2026-08-10 09:00", status: "inactive" },
];

const USER_COLS = [
  { key: "login", title: "Логин" },
  { key: "full_name", title: "ФИО" },
  { key: "roles", title: "Роли" },
  { key: "last_login", title: "Последний вход" },
  { key: "status", title: "Статус" },
];

const AUDIT_LOG = [
  { time: "2026-08-12 14:35", user: "developer", action: "Создание дашборда", detail: "Продажи по регионам" },
  { time: "2026-08-12 14:30", user: "analyst", action: "Просмотр дашборда", detail: "Главная" },
  { time: "2026-08-12 14:25", user: "developer", action: "SQL-запрос", detail: "SELECT region, SUM(revenue) FROM sales..." },
  { time: "2026-08-12 14:20", user: "viewer", action: "Экспорт отчёта", detail: "Бухгалтерский баланс (PDF)" },
  { time: "2026-08-12 14:15", user: "developer", action: "Изменение настроек", detail: "Подключение 1С" },
  { time: "2026-08-12 14:10", user: "analyst", action: "ГОСТ-отчёт", detail: "6-НДФЛ за июль 2026" },
  { time: "2026-08-12 14:00", user: "developer", action: "Вход в систему", detail: "127.0.0.1" },
];

const AUDIT_COLS = [
  { key: "time", title: "Время", width: "160px" },
  { key: "user", title: "Пользователь", width: "110px" },
  { key: "action", title: "Действие", width: "150px" },
  { key: "detail", title: "Детали" },
];

export function AdminPage() {
  const [tab, setTab] = useState<"users" | "audit" | "health">("users");

  return (
    <AppLayout>
      <div className="page-header">
        <h1 className="page-title">Администрирование</h1>
        <p className="page-subtitle">Управление пользователями, аудит действий и состояние системы</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button className={`btn ${tab === "users" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("users")}>
          Пользователи
        </button>
        <button className={`btn ${tab === "audit" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("audit")}>
          Аудит
        </button>
        <button className={`btn ${tab === "health" ? "btn-primary" : "btn-secondary"}`} onClick={() => setTab("health")}>
          Состояние
        </button>
      </div>

      {tab === "users" && (
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Пользователи ({USERS.length})</span>
            <button className="btn btn-sm btn-primary">Добавить</button>
          </div>
          <div className="widget-card-body">
            <DataTable columns={USER_COLS} rows={USERS} pageSize={10} />
          </div>
        </div>
      )}

      {tab === "audit" && (
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Журнал аудита</span>
          </div>
          <div className="widget-card-body">
            <DataTable columns={AUDIT_COLS} rows={AUDIT_LOG} pageSize={10} />
          </div>
        </div>
      )}

      {tab === "health" && (
        <div className="dashboard-grid cols-2">
          <div className="widget-card">
            <div className="widget-card-header">
              <span className="widget-card-title">Компоненты системы</span>
            </div>
            <div className="widget-card-body">
              {[
                { name: "API сервер", status: "ok", latency: "2 ms" },
                { name: "База данных", status: "ok", latency: "8 ms" },
                { name: "Redis", status: "ok", latency: "1 ms" },
                { name: "1С-коннектор", status: "warning", latency: "—" },
                { name: "AI-движок", status: "ok", latency: "340 ms" },
                { name: "SQL-верификатор", status: "ok", latency: "<1 ms" },
                { name: "Celery workers", status: "ok", latency: "—" },
                { name: "ГОСТ-шаблоны", status: "ok", latency: "—" },
              ].map((c) => (
                <div key={c.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border-primary)" }}>
                  <div>
                    <span style={{ fontWeight: 500, color: "var(--text-primary)", fontSize: "var(--font-md)" }}>{c.name}</span>
                    <span style={{ marginLeft: 8, fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>{c.latency}</span>
                  </div>
                  <span style={{
                    display: "inline-block", width: 10, height: 10, borderRadius: "50%",
                    background: c.status === "ok" ? "var(--success)" : c.status === "warning" ? "var(--warning)" : "var(--danger)"
                  }} />
                </div>
              ))}
            </div>
          </div>

          <div className="widget-card">
            <div className="widget-card-header">
              <span className="widget-card-title">Ресурсы сервера</span>
            </div>
            <div className="widget-card-body" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--font-sm)", marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>CPU</span>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>23%</span>
                </div>
                <div style={{ height: 6, background: "var(--bg-tertiary)", borderRadius: 3 }}>
                  <div style={{ height: 6, width: "23%", background: "var(--accent-primary)", borderRadius: 3 }} />
                </div>
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--font-sm)", marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>Память</span>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>412 MB / 2 GB</span>
                </div>
                <div style={{ height: 6, background: "var(--bg-tertiary)", borderRadius: 3 }}>
                  <div style={{ height: 6, width: "20%", background: "var(--success)", borderRadius: 3 }} />
                </div>
              </div>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--font-sm)", marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>Диск</span>
                  <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>24 GB / 256 GB</span>
                </div>
                <div style={{ height: 6, background: "var(--bg-tertiary)", borderRadius: 3 }}>
                  <div style={{ height: 6, width: "9%", background: "var(--warning)", borderRadius: 3 }} />
                </div>
              </div>

              <div style={{ marginTop: 8, padding: 12, background: "var(--accent-subtle)", borderRadius: "var(--radius-md)", fontSize: "var(--font-sm)" }}>
                <div style={{ fontWeight: 600, color: "var(--accent-primary)", marginBottom: 4 }}>Версия системы</div>
                <div style={{ color: "var(--text-secondary)" }}>ГОСТ БИ 0.1.0</div>
                <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)", marginTop: 4 }}>Python 3.12 | FastAPI | Apache Superset 5.x</div>
                <div style={{ color: "var(--text-tertiary)", fontSize: "var(--font-xs)" }}>Windows 11 | Uvicorn 0.52 | 96 tests PASS</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
