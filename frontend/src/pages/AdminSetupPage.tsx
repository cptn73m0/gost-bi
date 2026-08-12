import { useState } from "react";

interface AdminSetupProps {
  onComplete: (token: string, user: { id: number; login: string; full_name: string; role: string }) => void;
}

export function AdminSetupPage({ onComplete }: AdminSetupProps) {
  const [login, setLogin] = useState("admin");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSetup = async () => {
    if (!fullName.trim()) { setError("Введите ФИО"); return; }
    if (password.length < 6) { setError("Пароль должен быть не менее 6 символов"); return; }
    if (password !== confirm) { setError("Пароли не совпадают"); return; }
    setLoading(true); setError("");
    try {
      const resp = await fetch("/api/auth/setup", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password, full_name: fullName, role: "admin" }),
      });
      if (!resp.ok) { const e = await resp.json(); setError(e.detail || "Ошибка"); return; }
      const loginResp = await fetch("/api/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login, password }),
      });
      const data = await loginResp.json();
      localStorage.setItem("gost-bi-token", data.token);
      localStorage.setItem("gost-bi-user", JSON.stringify(data.user));
      onComplete(data.token, data.user);
    } catch { setError("Сервер недоступен"); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-secondary)" }}>
      <div style={{ background: "var(--bg-elevated)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", padding: 40, width: 400, maxWidth: "90vw" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>Настройка администратора</h1>
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", marginTop: 6 }}>Создайте учётную запись администратора системы</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>Логин</label>
            <input className="input" value={login} onChange={e => setLogin(e.target.value)} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>ФИО</label>
            <input className="input" placeholder="Иванов Иван Иванович" value={fullName} onChange={e => setFullName(e.target.value)} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>Пароль</label>
            <input className="input" type="password" placeholder="Не менее 6 символов" value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>Подтверждение пароля</label>
            <input className="input" type="password" placeholder="Повторите пароль" value={confirm} onChange={e => setConfirm(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSetup()} />
          </div>
          {error && <div style={{ fontSize: 12, color: "var(--danger)", textAlign: "center" }}>{error}</div>}
          <button className="btn btn-primary btn-lg" onClick={handleSetup} disabled={loading} style={{ width: "100%", justifyContent: "center", marginTop: 4 }}>
            {loading ? <span className="spinner" /> : "Создать администратора"}
          </button>
        </div>
      </div>
    </div>
  );
}
