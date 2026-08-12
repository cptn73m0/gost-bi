import type { ReactNode } from "react";

interface WidgetCardProps {
  title: string;
  fullWidth?: boolean;
  actions?: ReactNode;
  children: ReactNode;
}

export function WidgetCard({ title, fullWidth, actions, children }: WidgetCardProps) {
  return (
    <div className={`widget-card${fullWidth ? " widget-card-full" : ""}`}>
      <div className="widget-card-header">
        <span className="widget-card-title">{title}</span>
        {actions && <div className="widget-card-actions">{actions}</div>}
      </div>
      <div className="widget-card-body">{children}</div>
    </div>
  );
}

interface KPIProps {
  label: string;
  value: string;
  trend?: number;
  trendLabel?: string;
}

export function KPIWidget({ label, value, trend, trendLabel }: KPIProps) {
  const isPositive = trend !== undefined && trend >= 0;
  return (
    <div style={{ textAlign: "center", padding: "8px 0" }}>
      <div
        style={{
          fontSize: "var(--font-xs)",
          color: "var(--text-tertiary)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "var(--font-2xl)", fontWeight: 700, color: "var(--text-primary)" }}>
        {value}
      </div>
      {trend !== undefined && (
        <div
          style={{
            fontSize: "var(--font-xs)",
            color: isPositive ? "var(--success)" : "var(--danger)",
            marginTop: 4,
            fontWeight: 500,
          }}
        >
          {isPositive ? "▲" : "▼"} {Math.abs(trend)}%
          {trendLabel && <span style={{ color: "var(--text-tertiary)", marginLeft: 4 }}>{trendLabel}</span>}
        </div>
      )}
    </div>
  );
}
