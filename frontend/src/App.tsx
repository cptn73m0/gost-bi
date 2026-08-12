import { ThemeProvider } from "@/hooks/useTheme";
import { HomePage } from "@/pages/HomePage";
import { SQLLabPage } from "@/pages/SQLLabPage";
import { GOSTPage } from "@/pages/GOSTPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { AdminPage } from "@/pages/AdminPage";
import { useState } from "react";

type Page = "home" | "sql" | "gost" | "settings" | "admin";

export default function App() {
  const [page, setPage] = useState<Page>("home");

  return (
    <ThemeProvider>
      {page === "home" && <HomePage />}
      {page === "sql" && <SQLLabPage />}
      {page === "gost" && <GOSTPage />}
      {page === "settings" && <SettingsPage />}
      {page === "admin" && <AdminPage />}
    </ThemeProvider>
  );
}
