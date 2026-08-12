import { useState } from "react";
import { useTheme } from "@/hooks/useTheme";

export function SettingsPage() {
  const { theme, toggle } = useTheme();
  const [dbUrl, setDbUrl] = useState("postgresql://gostbi:****@localhost:5432/gostbi");
  const [redisUrl, setRedisUrl] = useState("redis://localhost:6379/0");
  const [lang, setLang] = useState("ru");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Настройки</h1>
        <p className="page-subtitle">Конфигурация системы, подключения и оформление</p>
      </div>

      <div className="dashboard-grid cols-2">
        {/* Оформление */}
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Оформление</span>
          </div>
          <div className="widget-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>Тема оформления</div>
                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>{theme === "light" ? "Светлая" : "Тёмная"}</div>
              </div>
              <button className="btn btn-secondary" onClick={toggle}>
                Переключить на {theme === "light" ? "тёмную" : "светлую"}
              </button>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                Язык интерфейса
              </label>
              <select className="input" value={lang} onChange={(e) => setLang(e.target.value)} style={{ cursor: "pointer" }}>
                <option value="ru">Русский</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </div>

        {/* Подключения */}
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Подключения</span>
          </div>
          <div className="widget-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                База данных (PostgreSQL / Tantor)
              </label>
              <input
                className="input"
                value={dbUrl}
                onChange={(e) => setDbUrl(e.target.value)}
                placeholder="postgresql://user:pass@host:5432/db"
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                Redis (кеш + очереди)
              </label>
              <input
                className="input"
                value={redisUrl}
                onChange={(e) => setRedisUrl(e.target.value)}
                placeholder="redis://localhost:6379/0"
              />
            </div>

            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button className="btn btn-primary" onClick={handleSave}>
                {saved ? "Сохранено" : "Сохранить"}
              </button>
              <button className="btn btn-sm btn-ghost" style={{ fontSize: "var(--font-xs)", color: "var(--accent-primary)" }}>
                Проверить подключение
              </button>
            </div>
          </div>
        </div>

        {/* 1С */}
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Интеграция с 1С</span>
          </div>
          <div className="widget-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                URL OData-сервиса 1С
              </label>
              <input className="input" placeholder="http://1c-server/base/odata/standard.odata" />
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                  Пользователь
                </label>
                <input className="input" placeholder="Администратор" />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                  Пароль
                </label>
                <input className="input" type="password" placeholder="••••••••" />
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleSave}>
              {saved ? "Сохранено" : "Сохранить"}
            </button>
          </div>
        </div>

        {/* AI-движок */}
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">AI-движок (NLP→SQL)</span>
          </div>
          <div className="widget-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                Провайдер
              </label>
              <select className="input" style={{ cursor: "pointer" }}>
                <option value="yandexgpt">YandexGPT</option>
                <option value="gigachat">GigaChat</option>
                <option value="local">Локальная LLM (on-premise)</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "var(--font-sm)", fontWeight: 500, color: "var(--text-primary)", marginBottom: 4 }}>
                API-ключ
              </label>
              <input className="input" type="password" placeholder="Введите ключ API" />
            </div>
            <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)" }}>
              Без AI-движка NLP→SQL будет недоступен. SQL-редактор продолжит работать.
            </div>
            <button className="btn btn-primary" onClick={handleSave}>
              {saved ? "Сохранено" : "Сохранить"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
