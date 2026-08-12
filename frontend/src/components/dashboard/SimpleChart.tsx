import { useMemo } from "react";

interface SimpleChartProps {
  data: { label: string; value: number }[];
  type?: "bar" | "line";
  height?: number;
  color?: string;
}

export function SimpleChart({ data, type = "bar", height = 200, color = "var(--accent-primary)" }: SimpleChartProps) {
  const maxVal = useMemo(() => Math.max(...data.map((d) => d.value), 1), [data]);
  const width = 100;
  const gap = 4;
  const barW = (width - (data.length - 1) * gap) / data.length;

  return (
    <div style={{ position: "relative", height, width: "100%" }}>
      <svg viewBox={`0 0 100 100`} preserveAspectRatio="none" style={{ width: "100%", height: "100%" }}>
        {/* Сетка */}
        {[0, 25, 50, 75, 100].map((y) => (
          <g key={y}>
            <line
              x1="0"
              y1={100 - y}
              x2="100"
              y2={100 - y}
              stroke="var(--border-primary)"
              strokeWidth="0.3"
              strokeDasharray="2 2"
            />
          </g>
        ))}

        {type === "bar" &&
          data.map((d, i) => {
            const h = (d.value / maxVal) * 85;
            const y = 98 - h;
            const x = i * (barW + gap);
            return <rect key={i} x={x} y={y} width={barW} height={h} rx="1" fill={color} opacity={0.85} />;
          })}

        {type === "line" && data.length > 1 && (
          <polyline
            points={data
              .map((d, i) => {
                const x = (i / (data.length - 1)) * 96 + 2;
                const y = 98 - (d.value / maxVal) * 85;
                return `${x},${y}`;
              })
              .join(" ")}
            fill="none"
            stroke={color}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
      </svg>

      {/* Подписи */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
        {data.map((d, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              textAlign: "center",
              fontSize: "var(--font-xs)",
              color: "var(--text-tertiary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {d.label}
          </div>
        ))}
      </div>
    </div>
  );
}
