import { ThemeProvider } from "@/hooks/useTheme";
import { HomePage } from "@/pages/HomePage";
import { SQLLabPage } from "@/pages/SQLLabPage";
import { GOSTPage } from "@/pages/GOSTPage";
import { useState } from "react";

type Page = "home" | "sql" | "gost";

export default function App() {
  const [page, setPage] = useState<Page>("home");

  return (
    <ThemeProvider>
      {page === "home" && <HomePage />}
      {page === "sql" && <SQLLabPage />}
      {page === "gost" && <GOSTPage />}
    </ThemeProvider>
  );
}
