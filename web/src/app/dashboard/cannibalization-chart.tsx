"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
} from "recharts";
import type { AuditResult } from "@/lib/engine";

interface Props {
  result: AuditResult;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    [key: string]: unknown;
  }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (active && payload?.length) {
    const cannibalized = payload.find((p) => p.name === "Cannibalized")?.value === 1;
    return (
      <div className="rounded-lg border bg-background p-2 shadow-sm text-sm">
        <p className="font-medium">{label}</p>
        {payload.map((entry, i) => {
          if (entry.name === "Cannibalized") return null;
          return (
            <p key={i} style={{ color: entry.color }}>
              {entry.name}: {entry.value}
            </p>
          );
        })}
        {cannibalized && (
          <p className="text-red-500 font-medium mt-1">Cannibalized Day</p>
        )}
      </div>
    );
  }
  return null;
}

export default function CannibalizationChart({ result }: Props) {
  if (!result.hasGSC) {
    return (
      <div className="flex items-center justify-center h-[300px] text-muted-foreground text-sm">
        Upload Google Search Console data to enable cannibalization analysis.
      </div>
    );
  }

  const rows = result.dailyRows.slice(-90);

  const data = rows.map((row) => ({
    date: row.date,
    Conversions: row.reportedConversions,
    "Brand Clicks": row.brandClicks,
    Cannibalized: row.cannibalized ? 1 : 0,
  }));

  const cannibalizedDates = data.filter((d) => d.Cannibalized === 1).map((d) => d.date);

  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          {cannibalizedDates.map((date) => (
            <ReferenceLine
              key={date}
              x={date}
              stroke="hsl(var(--destructive))"
              strokeDasharray="3 3"
              strokeOpacity={0.3}
            />
          ))}
          <Area
            type="monotone"
            dataKey="Conversions"
            stroke="hsl(var(--chart-1))"
            fill="hsl(var(--chart-1))"
            fillOpacity={0.1}
          />
          <Area
            type="monotone"
            dataKey="Brand Clicks"
            stroke="hsl(var(--chart-2))"
            fill="hsl(var(--chart-2))"
            fillOpacity={0.2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
