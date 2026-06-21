"use client";

import {
  ComposedChart,
  Bar,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
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
    return (
      <div className="rounded-xl border bg-background/95 backdrop-blur-sm p-3 shadow-lg text-sm">
        <p className="font-medium mb-1">{label}</p>
        {payload.map((entry, i) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
}

const COLORS = {
  spend: "#3B82F6",
  actual: "#10B981",
  reported: "#8B5CF6",
};

export default function TrendChart({ result }: Props) {
  const rows = result.dailyRows.slice(-90);

  const data = rows.map((row) => ({
    date: row.date,
    "Ad Spend ($)": Number(row.spend.toFixed(0)),
    "Actual Conversions": row.actualConversions,
    "Reported Conversions": row.reportedConversions,
  }));

  return (
    <div className="h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
          <defs>
            <linearGradient id="actualGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.actual} stopOpacity={0.3} />
              <stop offset="95%" stopColor={COLORS.actual} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 13 }}
            label={{ value: "Spend ($)", angle: -90, position: "insideLeft", style: { fontSize: 12, fill: "#888" } }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 13 }}
            label={{ value: "Conversions", angle: 90, position: "insideRight", style: { fontSize: 12, fill: "#888" } }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
          />
          <Bar
            yAxisId="left"
            dataKey="Ad Spend ($)"
            fill={COLORS.spend}
            radius={[4, 4, 0, 0]}
            opacity={0.75}
            animationBegin={0}
            animationDuration={800}
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="Actual Conversions"
            fill="url(#actualGradient)"
            stroke="none"
            animationBegin={200}
            animationDuration={1000}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="Actual Conversions"
            stroke={COLORS.actual}
            strokeWidth={2.5}
            dot={false}
            animationBegin={200}
            animationDuration={1000}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="Reported Conversions"
            stroke={COLORS.reported}
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            animationBegin={400}
            animationDuration={1000}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
