import { useState } from "react";

interface LoginPageProps {
  onLogin: (token: string, user: { id: number; login: string; full_name: string; role: string }) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"local" | "esia">("local");

  const handleLocalLogin = async () => {
    if (!login.trim() || !password.trim()) { setError("Введите логин и пароль"); return; }
    setLoading(true); setError("");
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password }),
      });
      if (!resp.ok) { const e = await resp.json(); setError(e.detail || "Ошибка входа"); return; }
      const data = await resp.json();
      localStorage.setItem("gost-bi-token", data.token);
      localStorage.setItem("gost-bi-user", JSON.stringify(data.user));
      onLogin(data.token, data.user);
    } catch { setError("Сервер недоступен"); }
    finally { setLoading(false); }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      background: "var(--bg-secondary)", fontFamily: "var(--font-family)",
    }}>
      <div style={{
        background: "var(--bg-elevated)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)",
        padding: 40, width: 380, maxWidth: "90vw",
      }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ width: 48, height: 48, background: "var(--accent-primary)", borderRadius: "var(--radius-md)", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: 18 }}>БИ</div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginTop: 12 }}>ГОСТ БИ</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginTop: 4 }}>Вход в систему</p>
        </div>

        <div style={{ display: "flex", marginBottom: 20, background: "var(--bg-tertiary)", borderRadius: "var(--radius-sm)", padding: 3 }}>
          <button onClick={() => setMode("local")} style={{ flex: 1, padding: "6px 0", borderRadius: "var(--radius-sm)", border: "none", cursor: "pointer", fontWeight: 500, fontSize: 13, background: mode === "local" ? "var(--bg-elevated)" : "transparent", color: "var(--text-primary)", boxShadow: mode === "local" ? "var(--shadow-sm)" : "none" }}>Логин/пароль</button>
          <button onClick={() => setMode("esia")} style={{ flex: 1, padding: "6px 0", borderRadius: "var(--radius-sm)", border: "none", cursor: "pointer", fontWeight: 500, fontSize: 13, background: mode === "esia" ? "var(--bg-elevated)" : "transparent", color: "var(--text-primary)", boxShadow: mode === "esia" ? "var(--shadow-sm)" : "none" }}>Госуслуги</button>
        </div>

        {mode === "local" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <input className="input" placeholder="Логин" value={login} onChange={e => setLogin(e.target.value)} onKeyDown={e => e.key === "Enter" && handleLocalLogin()} />
            <input className="input" type="password" placeholder="Пароль" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === "Enter" && handleLocalLogin()} />
            {error && <div style={{ fontSize: 12, color: "var(--danger)", textAlign: "center" }}>{error}</div>}
            <button className="btn btn-primary btn-lg" onClick={handleLocalLogin} disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
              {loading ? <span className="spinner" /> : "Войти"}
            </button>
          </div>
        )}

        {mode === "esia" && (
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>Вход через Единую систему идентификации и аутентификации</p>
            <button className="btn btn-primary btn-lg" style={{ width: "100%", justifyContent: "center" }} onClick={() => window.location.href = "/api/auth/esia/login"}>
              Войти через Госуслуги
            </button>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 8 }}>Требуется подтверждённая учётная запись</p>
          </div>
        )}
      </div>
    </div>
  );
}
