"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { ChartData, ChartType } from "@/lib/types";

interface ChartDisplayProps {
  data: ChartData | null;
  chartType: ChartType;
}

const fallbackColours = ["var(--green)", "var(--blue)", "var(--blue)", "var(--red)"];

export function ChartDisplay({ data, chartType }: ChartDisplayProps) {
  if (!data) {
    return (
      <div className="flex h-full items-center justify-center text-center font-mono text-[10px] text-text-3">
        No chart available for this query
      </div>
    );
  }

  const chartRows = data.labels.map((label, index) => ({
    label,
    value: data.values[index] ?? 0,
    colour: data.colours?.[index] ?? fallbackColours[index % fallbackColours.length]
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      {chartType === "line" ? (
        <LineChart data={chartRows} margin={{ top: 8, right: 10, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--border-0)" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--text-2)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--text-2)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--blue-text)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--blue-text)", strokeWidth: 0 }}
          />
        </LineChart>
      ) : chartType === "doughnut" ? (
        <PieChart margin={{ top: 6, right: 8, bottom: 6, left: 8 }}>
          <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
          <Pie
            data={chartRows}
            dataKey="value"
            nameKey="label"
            innerRadius="55%"
            outerRadius="78%"
            paddingAngle={2}
          >
            {chartRows.map((row) => (
              <Cell key={row.label} fill={row.colour} stroke="var(--bg-1)" />
            ))}
          </Pie>
        </PieChart>
      ) : (
        <BarChart data={chartRows} margin={{ top: 8, right: 10, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="var(--border-0)" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--text-2)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "var(--text-2)", fontSize: 9, fontFamily: "var(--font-ibm-plex-mono)" }}
          />
          <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {chartRows.map((row) => (
              <Cell key={row.label} fill={row.colour} />
            ))}
          </Bar>
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}

const tooltipStyle = {
  background: "var(--bg-0)",
  border: "1px solid var(--border-0)",
  borderRadius: 3,
  color: "var(--text-0)",
  fontFamily: "var(--font-ibm-plex-mono)",
  fontSize: 10
};

const tooltipLabelStyle = {
  color: "var(--text-2)",
  fontFamily: "var(--font-ibm-plex-mono)",
  fontSize: 9
};
