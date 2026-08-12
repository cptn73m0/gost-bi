import type { ReactNode } from "react";

import { useState } from "react";
import { useTheme } from "@/hooks/useTheme";
import "@/styles/theme.css";
import "@/styles/sidebar.css";
import "@/styles/header.css";
import "@/styles/layout.css";

interface SidebarItem {
  id: string;
  label: string;
  icon: string;
  path: string;
}

interface SidebarSection {
  title: string;
  items: SidebarItem[];
}

const NAV_SECTIONS: SidebarSection[] = [
  {
    title: "Аналитика",
    items: [
      { id: "home", label: "Главная", icon: "📊", path: "/" },
      { id: "dashboards", label: "Дашборды", icon: "📈", path: "/dashboards" },
      { id: "explore", label: "Исследование", icon: "🔍", path: "/explore" },
    ],
  },
  {
    title: "Данные",
    items: [
      { id: "sql", label: "SQL-лаборатория", icon: "💾", path: "/sql" },
      { id: "datasets", label: "Источники данных", icon: "🗄️", path: "/datasets" },
    ],
  },
  {
    title: "Отчётность",
    items: [
      { id: "gost", label: "ГОСТ-отчёты", icon: "📋", path: "/gost" },
      { id: "export", label: "Экспорт", icon: "📥", path: "/export" },
    ],
  },
  {
    title: "Настройки",
    items: [
      { id: "settings", label: "Параметры", icon: "⚙️", path: "/settings" },
      { id: "admin", label: "Администрирование", icon: "🔐", path: "/admin" },
    ],
  },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [activeItem, setActiveItem] = useState("home");

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Сайдбар */}
      <nav className={`sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">БИ</div>
          <span>ГОСТ БИ</span>
        </div>

        <div className="sidebar-nav">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title}>
              <div className="sidebar-section">{section.title}</div>
              {section.items.map((item) => (
                <button
                  key={item.id}
                  className={`sidebar-item${activeItem === item.id ? " active" : ""}`}
                  onClick={() => setActiveItem(item.id)}
                  title={item.label}
                >
                  <span className="sidebar-item-icon">{item.icon}</span>
                  <span className="sidebar-item-label">{item.label}</span>
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="sidebar-item" onClick={toggle}>
            <span className="sidebar-item-icon">{theme === "light" ? "🌙" : "☀️"}</span>
            <span className="sidebar-item-label">
              {theme === "light" ? "Тёмная тема" : "Светлая тема"}
            </span>
          </button>
        </div>
      </nav>

      {/* Сворачиватель */}
      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed(!collapsed)}
        style={{
          position: "fixed",
          bottom: 12,
          left: collapsed ? 44 : 244,
          zIndex: 10,
          width: 24,
          height: 24,
          borderRadius: "50%",
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-primary)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "var(--shadow-sm)",
          transition: "left 200ms ease-out",
        }}
      >
        {collapsed ? "→" : "←"}
      </button>

      {/* Основная область */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Шапка */}
        <header className="header">
          <div className="header-left">
            <div className="breadcrumb">
              <span className="breadcrumb-item current">
                {NAV_SECTIONS.flatMap((s) => s.items).find((i) => i.id === activeItem)?.label ?? "Главная"}
              </span>
            </div>
          </div>

          <div className="header-right">
            <button className="header-btn" onClick={toggle} title="Сменить тему">
              {theme === "light" ? "🌙" : "☀️"}
            </button>
            <div className="header-divider" />
            <div className="user-avatar">АИ</div>
          </div>
        </header>

        {/* Контент */}
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
