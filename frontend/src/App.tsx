import { ThemeProvider } from "@/hooks/useTheme";
import { AppLayout } from "@/components/layout/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { SQLLabPage } from "@/pages/SQLLabPage";
import { GOSTPage } from "@/pages/GOSTPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { AdminPage } from "@/pages/AdminPage";
import { LoginPage } from "@/pages/LoginPage";
import { AdminSetupPage } from "@/pages/AdminSetupPage";
import { useState, useEffect } from "react";

type Page = "home" | "dashboards" | "explore" | "sql" | "datasets" | "gost" | "export" | "settings" | "admin";

interface User {
  id: number; login: string; full_name: string; role: string;
}

export default function App() {
  const [page, setPage] = useState<Page>("home");
  const [user, setUser] = useState<User | null>(null);
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null);

  useEffect(() => {
    const savedToken = localStorage.getItem("gost-bi-token");
    const savedUser = localStorage.getItem("gost-bi-user");
    if (savedToken && savedUser) {
      setUser(JSON.parse(savedUser));
      return;
    }
    fetch("/api/auth/setup-status")
      .then(r => r.json())
      .then(d => setNeedsSetup(!d.has_admin))
      .catch(() => setNeedsSetup(false));
  }, []);

  const handleLogin = (_t: string, u: User) => { setUser(u); };
  const handleLogout = () => { localStorage.removeItem("gost-bi-token"); localStorage.removeItem("gost-bi-user"); setUser(null); };

  if (needsSetup === null && !user) return <div style={{ display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",color:"var(--text-tertiary)" }}><span className="spinner" /></div>;
  if (needsSetup && !user) return <AdminSetupPage onComplete={handleLogin} />;
  if (!user) return <LoginPage onLogin={handleLogin} />;

  const isAdmin = user.role === "admin";

  const renderPage = () => {
    switch (page) {
      case "home": return <HomeContent />;
      case "dashboards": return <DashboardsContent />;
      case "explore": return <ExploreContent />;
      case "sql": return <SQLLabPage />;
      case "datasets": return <DatasetsContent />;
      case "gost": return <GOSTPage />;
      case "export": return <ExportContent />;
      case "settings": return <SettingsPage />;
      case "admin": return isAdmin ? <AdminPage /> : <HomeContent />;
      default: return <HomeContent />;
    }
  };

  return (
    <ThemeProvider>
      <AppLayout activePage={page} onNavigate={(p) => setPage(p as Page)} onLogout={handleLogout} userName={user.full_name}>
        {renderPage()}
      </AppLayout>
    </ThemeProvider>
  );
}

function HomeContent() {
  return <><div className="page-header"><h1 className="page-title">Добро пожаловать</h1><p className="page-subtitle">Обзор ключевых показателей</p></div><HomePage /></>;
}

function DashboardsContent() {
  return <div className="page-header"><h1 className="page-title">Дашборды</h1><p className="page-subtitle">Сохранённые дашборды и отчёты</p><div className="dashboard-grid cols-3">{[
    {name:"Продажи",widgets:4,updated:"12.08.2026"},{name:"Финансы",widgets:3,updated:"11.08.2026"},{name:"Склад",widgets:5,updated:"10.08.2026"},{name:"HR",widgets:2,updated:"09.08.2026"},{name:"Маркетинг",widgets:3,updated:"08.08.2026"},{name:"Логистика",widgets:4,updated:"07.08.2026"}
  ].map(d=><div key={d.name} className="widget-card"><div className="widget-card-body" style={{padding:20}}><div style={{fontWeight:600,fontSize:15,color:"var(--text-primary)"}}>{d.name}</div><div style={{fontSize:12,color:"var(--text-tertiary)",marginTop:4}}>{d.widgets} виджетов · {d.updated}</div></div></div>)}</div></div>;
}

function ExploreContent() {
  return <div className="page-header"><h1 className="page-title">Исследование</h1><p className="page-subtitle">Интерактивное построение графиков</p><div className="widget-card"><div className="widget-card-body" style={{padding:24,textAlign:"center",color:"var(--text-tertiary)"}}>Выберите источник данных и перетащите поля для построения графика</div></div></div>;
}

function DatasetsContent() {
  return <div className="page-header"><h1 className="page-title">Источники данных</h1><p className="page-subtitle">Подключённые базы данных и таблицы</p><div className="dashboard-grid cols-2">{[
    {name:"sales",rows:30,type:"PostgreSQL"},{name:"products",rows:10,type:"PostgreSQL"},{name:"customers",rows:10,type:"PostgreSQL"},{name:"employees",rows:10,type:"PostgreSQL"}
  ].map(d=><div key={d.name} className="widget-card"><div className="widget-card-body" style={{padding:20}}><div style={{fontWeight:600,color:"var(--text-primary)"}}>{d.name}</div><div style={{fontSize:12,color:"var(--text-tertiary)",marginTop:4}}>{d.rows} строк · {d.type}</div></div></div>)}</div></div>;
}

function ExportContent() {
  return <div className="page-header"><h1 className="page-title">Экспорт</h1><p className="page-subtitle">Выгрузка данных в различные форматы</p><div className="dashboard-grid cols-2">{[
    {name:"CSV",desc:"Экспорт в CSV (Windows-1251)",icon:"📄"},{name:"Excel",desc:"Экспорт в Microsoft Excel",icon:"📊"},{name:"PDF",desc:"Экспорт в PDF",icon:"📕"},{name:"XML (ФНС)",desc:"Экспорт для налоговой",icon:"📋"}
  ].map(d=><div key={d.name} className="widget-card" style={{cursor:"pointer"}}><div className="widget-card-body" style={{padding:24,textAlign:"center"}}><div style={{fontSize:28,marginBottom:8}}>{d.icon}</div><div style={{fontWeight:600,color:"var(--text-primary)"}}>{d.name}</div><div style={{fontSize:12,color:"var(--text-tertiary)",marginTop:4}}>{d.desc}</div></div></div>)}</div></div>;
}
