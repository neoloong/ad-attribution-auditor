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

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (active && payload?.length) {
    return (
      <div className="rounded-xl border bg-background/95 backdrop-blur-sm p-3 shadow-lg text-sm">
        {payload.map((entry, i) => (
          <p key={i} style={{ color: entry.color }}>
            {entry.name}: {entry.value}x
          </p>
        ))}
      </div>
    );
  }
  return null;
}

const COLORS = {
  reported: "#3B82F6",
  trueIncremental: "#10B981",
};

export default function ROASChart({ result }: Props) {
  const data = [
    {
      name: "ROAS",
      "Reported ROAS": Number(result.incrementalROAS.reportedROAS.toFixed(2)),
      "True Incremental ROAS": Number(result.incrementalROAS.trueIncrementalROAS.toFixed(2)),
    },
  ];

  return (
    <div className="h-[300px]">
      <div className="text-sm font-medium text-muted-foreground mb-2 text-center">
        Platform claimed vs actual after deduplication
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.1} />
          <XAxis dataKey="name" tick={{ fontSize: 13 }} />
          <YAxis tick={{ fontSize: 13 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="top"
            wrapperStyle={{ fontSize: 13, paddingBottom: 8 }}
          />
          <Bar
            dataKey="Reported ROAS"
            fill={COLORS.reported}
            radius={[4, 4, 0, 0]}
            animationBegin={0}
            animationDuration={800}
          />
          <Bar
            dataKey="True Incremental ROAS"
            fill={COLORS.trueIncremental}
            radius={[4, 4, 0, 0]}
            animationBegin={200}
            animationDuration={800}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
