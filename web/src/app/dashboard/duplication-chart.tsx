"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
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
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
}

const COLORS = {
  reported: "#3B82F6",
  actual: "#10B981",
};

export default function DuplicationChart({ result }: Props) {
  const rows = result.dailyRows.slice(-60);

  const data = rows.map((row) => ({
    date: row.date,
    "Reported Conversions": row.reportedConversions,
    "Actual Conversions": row.actualConversions,
  }));

  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            interval="preserveStartEnd"
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fontSize: 13 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
          />
          <Bar
            dataKey="Reported Conversions"
            fill={COLORS.reported}
            radius={[4, 4, 0, 0]}
            animationBegin={0}
            animationDuration={800}
          />
          <Bar
            dataKey="Actual Conversions"
            fill={COLORS.actual}
            radius={[4, 4, 0, 0]}
            animationBegin={200}
            animationDuration={800}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
