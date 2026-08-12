import { KPIWidget, WidgetCard } from "@/components/dashboard/WidgetCard";
import { DataTable } from "@/components/dashboard/DataTable";
import { SimpleChart } from "@/components/dashboard/SimpleChart";

const REVENUE_DATA = [
  { label: "Янв", value: 42 },
  { label: "Фев", value: 38 },
  { label: "Мар", value: 55 },
  { label: "Апр", value: 48 },
  { label: "Май", value: 62 },
  { label: "Июн", value: 70 },
  { label: "Июл", value: 65 },
  { label: "Авг", value: 58 },
];

const SALES_TABLE_COLS = [
  { key: "region", title: "Регион" },
  { key: "revenue", title: "Выручка, млн ₽", width: "140px" },
  { key: "orders", title: "Заказы", width: "90px" },
  { key: "avg", title: "Средний чек, ₽", width: "140px" },
  { key: "growth", title: "Рост", width: "80px" },
];

const SALES_TABLE_ROWS = [
  { region: "Москва", revenue: "1 247", orders: 8420, avg: "148 100", growth: "+8.2%" },
  { region: "Санкт-Петербург", revenue: "683", orders: 5120, avg: "133 400", growth: "+5.7%" },
  { region: "Краснодарский край", revenue: "412", orders: 3650, avg: "112 900", growth: "+12.1%" },
  { region: "Свердловская обл.", revenue: "387", orders: 2980, avg: "129 900", growth: "+3.4%" },
  { region: "Татарстан", revenue: "356", orders: 2740, avg: "129 900", growth: "+6.8%" },
  { region: "Новосибирская обл.", revenue: "298", orders: 2410, avg: "123 700", growth: "+4.1%" },
  { region: "Ростовская обл.", revenue: "245", orders: 1980, avg: "123 700", growth: "+9.3%" },
  { region: "Нижегородская обл.", revenue: "221", orders: 1890, avg: "116 900", growth: "+2.8%" },
  { region: "Башкортостан", revenue: "198", orders: 1620, avg: "122 200", growth: "+7.5%" },
  { region: "Самарская обл.", revenue: "176", orders: 1480, avg: "118 900", growth: "+4.9%" },
  { region: "Челябинская обл.", revenue: "154", orders: 1320, avg: "116 700", growth: "+3.2%" },
  { region: "Красноярский край", revenue: "132", orders: 1150, avg: "114 800", growth: "+6.1%" },
];

export function HomePage() {
  return (
    <>
      <div className="dashboard-grid cols-4" style={{ marginBottom: 20 }}>
        <WidgetCard title="Выручка">
          <KPIWidget label="За текущий месяц" value="1 247 млн ₽" trend={8.2} trendLabel="к прошлому месяцу" />
        </WidgetCard>
        <WidgetCard title="Заказы">
          <KPIWidget label="Всего за месяц" value="8 420" trend={5.1} trendLabel="к прошлому месяцу" />
        </WidgetCard>
        <WidgetCard title="Средний чек">
          <KPIWidget label="По компании" value="148 100 ₽" trend={-1.3} trendLabel="к прошлому месяцу" />
        </WidgetCard>
        <WidgetCard title="Активные клиенты">
          <KPIWidget label="Уникальных за месяц" value="3 842" trend={12.4} trendLabel="к прошлому месяцу" />
        </WidgetCard>
      </div>

      {/* График + Таблица */}
      <div className="dashboard-grid cols-2">
        <WidgetCard title="Динамика выручки" fullWidth={false}>
          <SimpleChart data={REVENUE_DATA} type="line" height={240} />
        </WidgetCard>
        <WidgetCard title="Продажи по регионам">
          <DataTable columns={SALES_TABLE_COLS} rows={SALES_TABLE_ROWS} pageSize={6} />
        </WidgetCard>
      </div>
    </>
  );
}
