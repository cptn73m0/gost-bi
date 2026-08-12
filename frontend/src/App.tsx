import { ThemeProvider } from "@/hooks/useTheme";
import { AppLayout } from "@/components/layout/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { SQLLabPage } from "@/pages/SQLLabPage";
import { GOSTPage } from "@/pages/GOSTPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { AdminPage } from "@/pages/AdminPage";
import { useState } from "react";

type Page = "home" | "dashboards" | "explore" | "sql" | "datasets" | "gost" | "export" | "settings" | "admin";

export default function App() {
  const [page, setPage] = useState<Page>("home");

  const renderPage = () => {
    switch (page) {
      case "home": return <HomePageContent />;
      case "sql": return <SQLLabContent />;
      case "gost": return <GOSTContent />;
      case "settings": return <SettingsContent />;
      case "admin": return <AdminContent />;
      default: return <HomePageContent />;
    }
  };

  return (
    <ThemeProvider>
      <AppLayout activePage={page} onNavigate={(p) => setPage(p as Page)}>
        {renderPage()}
      </AppLayout>
    </ThemeProvider>
  );
}

function HomePageContent() {
  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Добро пожаловать, Алексей Иванович</h1>
        <p className="page-subtitle">Обзор ключевых показателей компании за август 2026 года</p>
      </div>
      <HomePage />
    </>
  );
}

function SQLLabContent() {
  return <SQLLabPage />;
}

function GOSTContent() {
  return <GOSTPage />;
}

function SettingsContent() {
  return <SettingsPage />;
}

function AdminContent() {
  return <AdminPage />;
}
