import { useState } from "react";

interface GOSTTemplate {
  code: string;
  name: string;
  description: string;
  category: string;
}

const GOST_TEMPLATES: GOSTTemplate[] = [
  { code: "0710001", name: "Бухгалтерский баланс", description: "Форма по ОКУД 0710001. Активы и пассивы организации.", category: "Бухгалтерская отчётность" },
  { code: "0710002", name: "Отчёт о финансовых результатах", description: "Прибыли и убытки за отчётный период.", category: "Бухгалтерская отчётность" },
  { code: "6NDFL", name: "6-НДФЛ", description: "Расчёт сумм налога на доходы физических лиц.", category: "Налоговая отчётность" },
  { code: "SZV-M", name: "СЗВ-М", description: "Сведения о застрахованных лицах (ежемесячная).", category: "Пенсионный фонд" },
  { code: "SZV-TD", name: "СЗВ-ТД", description: "Сведения о трудовой деятельности сотрудников.", category: "Пенсионный фонд" },
  { code: "2NDFL", name: "2-НДФЛ", description: "Справка о доходах физического лица.", category: "Налоговая отчётность" },
  { code: "P-4", name: "П-4", description: "Сведения о численности и заработной плате работников.", category: "Статистика (Росстат)" },
];

export function GOSTPage() {
  const [selected, setSelected] = useState<GOSTTemplate | null>(null);
  const [period, setPeriod] = useState("2026-07-01");
  const [generated, setGenerated] = useState(false);

  const handleGenerate = () => {
    setGenerated(true);
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">ГОСТ-отчётность</h1>
        <p className="page-subtitle">Формирование регламентированной отчётности по ГОСТ, ФНС и Росстату</p>
      </div>

      <div className="dashboard-grid cols-2">
        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">Выберите форму</span>
          </div>
          <div className="widget-card-body">
            {GOST_TEMPLATES.map((tpl) => (
              <div
                key={tpl.code}
                onClick={() => { setSelected(tpl); setGenerated(false); }}
                style={{
                  padding: "10px 0",
                  borderBottom: "1px solid var(--border-primary)",
                  cursor: "pointer",
                  background: selected?.code === tpl.code ? "var(--accent-subtle)" : "transparent",
                  borderRadius: "var(--radius-sm)",
                  paddingLeft: 8,
                  marginBottom: 4,
                  transition: "background 120ms ease-out",
                }}
              >
                <div style={{ fontWeight: 600, fontSize: "var(--font-md)", color: "var(--text-primary)" }}>{tpl.name}</div>
                <div style={{ fontSize: "var(--font-xs)", color: "var(--text-tertiary)", marginTop: 2 }}>
                  {tpl.code} — {tpl.category}
                </div>
                <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginTop: 4 }}>{tpl.description}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="widget-card">
          <div className="widget-card-header">
            <span className="widget-card-title">{selected ? selected.name : "Параметры отчёта"}</span>
          </div>
          <div className="widget-card-body">
            {selected ? (
              <>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: "block", fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: 4 }}>
                    Отчётный период
                  </label>
                  <input
                    className="input"
                    type="date"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                  />
                </div>

                <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                  <button className="btn btn-primary" onClick={handleGenerate}>Сформировать</button>
                  <button className="btn btn-secondary" disabled={!generated}>PDF</button>
                  <button className="btn btn-secondary" disabled={!generated}>Excel</button>
                  <button className="btn btn-secondary" disabled={!generated}>XML (ФНС)</button>
                </div>

                {generated && (
                  <div
                    style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-primary)",
                      borderRadius: "var(--radius-md)",
                      padding: 16,
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 8, color: "var(--success)" }}>Отчёт сформирован</div>
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                      Форма: {selected.name} ({selected.code})
                    </div>
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                      Период: {period}
                    </div>
                    <div style={{ fontSize: "var(--font-sm)", color: "var(--text-tertiary)", marginTop: 8 }}>
                      Данные автоматически подставлены из подключённых источников.
                      Отчёт готов к экспорту.
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: "center", padding: 40, color: "var(--text-disabled)" }}>
                Выберите форму отчёта из списка слева
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
