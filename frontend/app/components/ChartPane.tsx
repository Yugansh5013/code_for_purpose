"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartDisplay } from "./ChartDisplay";
import { StatCard } from "./StatCard";
import { DEFAULT_STATS, useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { ChartData, ChartPanel, ChartType } from "@/lib/types";

const defaultChartData: ChartData = {
  type: "bar",
  labels: ["North", "East", "West", "South"],
  values: [1420, 840, 560, 980],
  colours: ["var(--green)", "var(--blue)", "var(--blue)", "var(--red)"],
  y_label: "Total Sales (£K)"
};

const chartToggles = [
  { label: "BAR", value: "bar" },
  { label: "LINE", value: "line" },
  { label: "DONUT", value: "doughnut" }
] satisfies Array<{ label: string; value: ChartType }>;

function chartPanelToChartData(panel: ChartPanel): ChartData | null {
  if (!panel.data?.length || !panel.columns?.length) return null;
  if (panel.chart_type === "number") return null;

  const labelCol = panel.columns[0];
  const valueCol = panel.columns.length > 1 ? panel.columns[1] : panel.columns[0];

  const labels = panel.data.map((row) => String(row[labelCol] ?? ""));
  const values = panel.data.map((row) => {
    const v = row[valueCol];
    return typeof v === "number" ? v : typeof v === "string" ? parseFloat(v) || 0 : 0;
  });

  const typeMap: Record<string, ChartType> = {
    bar: "bar", line: "line", pie: "doughnut", doughnut: "doughnut", number: "bar"
  };

  return {
    type: typeMap[panel.chart_type] ?? "bar",
    labels,
    values,
    y_label: panel.title || valueCol,
  };
}

function NumberCard({ panel }: { panel: ChartPanel }) {
  const row = panel.data[0] || {};
  const keys = Object.keys(row);
  const numKey = keys.find((k) => {
    const v = row[k];
    return typeof v === "number" || (typeof v === "string" && v !== "" && !isNaN(Number(v)));
  }) || keys[keys.length - 1] || "";
  const val = row[numKey];
  const numericVal = typeof val === "number" ? val : parseFloat(String(val)) || 0;
  const formatted = Math.abs(numericVal) > 1000
    ? `£${numericVal.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : numericVal.toLocaleString();

  return (
    <div className="rounded-xl border border-border-0 bg-bg-0 p-4 text-center">
      <div className="bg-gradient-to-r from-[#3b82f6] via-[#8b5cf6] to-[#06b6d4] bg-clip-text text-2xl font-bold text-transparent">
        {formatted}
      </div>
      <div className="mt-1 text-[10px] text-text-3">
        {(panel.title || numKey).replace(/_/g, " ")}
      </div>
      <div className="mt-1 text-[8px] text-text-3">
        <span className={panel.confidence_tier === "green" ? "text-green" : panel.confidence_tier === "amber" ? "text-[#f59e0b]" : "text-red"}>
          {Math.round(panel.confidence_score * 100)}%
        </span>
      </div>
    </div>
  );
}

export function ChartPane() {
  const activeChartData = useOmniDataStore((state) => state.activeChartData);
  const activeStats = useOmniDataStore((state) => state.activeStats);
  const chartPanels = useOmniDataStore((state) => state.chartPanels);
  const messages = useOmniDataStore((state) => state.messages);
  const [chartType, setChartType] = useState<ChartType>("bar");
  const hasAiResponse = messages.some((message) => message.answer);

  // Multi-chart: extract number cards and visualizable charts
  const numberCards = useMemo(
    () => chartPanels.filter((p) => p.chart_type === "number" && p.data?.length),
    [chartPanels]
  );

  const vizCharts = useMemo(
    () => chartPanels.filter((p) => p.chart_type !== "number" && p.data?.length).map(chartPanelToChartData).filter(Boolean) as ChartData[],
    [chartPanels]
  );

  const chartData = useMemo(() => {
    // If multi-chart panels have visualizable charts, use those
    if (vizCharts.length > 0) return vizCharts[0];
    if (activeChartData) return activeChartData;
    return hasAiResponse ? null : defaultChartData;
  }, [activeChartData, hasAiResponse, vizCharts]);

  useEffect(() => {
    if (chartData) {
      setChartType(chartData.type);
    }
  }, [chartData]);

  const stats = activeStats.length ? activeStats : DEFAULT_STATS;

  return (
    <section className="flex min-h-0 flex-1 flex-col border-b border-border-0">
      <div className="flex h-8 flex-shrink-0 items-center justify-between border-b border-border-0 px-3 py-[7px]">
        <div className="font-mono text-[8px] uppercase tracking-[0.14em] text-text-3">
          VISUAL CONTEXT
          {chartPanels.length > 1 && (
            <span className="ml-2 rounded-sm bg-[#06b6d410] px-[5px] py-[1px] text-[#06b6d4]">
              {chartPanels.length} charts
            </span>
          )}
        </div>
        <div className="flex items-center gap-[4px]">
          {chartToggles.map((toggle) => (
            <button
              key={toggle.value}
              type="button"
              className={cn(
                "rounded-[2px] border px-[7px] py-[2px] font-mono text-[8px] tracking-[0.06em]",
                chartType === toggle.value
                  ? "border-border-1 bg-bg-3 text-text-0"
                  : "border-border-0 bg-transparent text-text-2 hover:text-text-1"
              )}
              onClick={() => setChartType(toggle.value)}
            >
              {toggle.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid flex-shrink-0 grid-cols-3 gap-2 px-3 pb-[6px] pt-[10px]">
        {stats.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </div>

      {/* Number cards section */}
      {numberCards.length > 0 && (
        <div className="grid grid-cols-2 gap-2 px-3 pb-2">
          {numberCards.map((panel, i) => (
            <NumberCard key={`num-${i}`} panel={panel} />
          ))}
        </div>
      )}

      {/* Main chart */}
      <div className="min-h-0 flex-1 px-3 pb-3 pt-2">
        <ChartDisplay data={chartData} chartType={chartType} />
      </div>

      {/* Additional charts (if multi-chart) */}
      {vizCharts.length > 1 && (
        <div className="space-y-2 px-3 pb-3">
          {vizCharts.slice(1).map((cd, i) => (
            <div key={`extra-chart-${i}`} className="h-[160px] rounded-lg border border-border-0 bg-bg-0 p-2">
              <ChartDisplay data={cd} chartType={cd.type} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
