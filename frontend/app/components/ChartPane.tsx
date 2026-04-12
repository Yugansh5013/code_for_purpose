"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartDisplay } from "./ChartDisplay";
import { StatCard } from "./StatCard";
import { DEFAULT_STATS, useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { ChartData, ChartType } from "@/lib/types";

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

export function ChartPane() {
  const activeChartData = useOmniDataStore((state) => state.activeChartData);
  const activeStats = useOmniDataStore((state) => state.activeStats);
  const messages = useOmniDataStore((state) => state.messages);
  const [chartType, setChartType] = useState<ChartType>("bar");
  const hasAiResponse = messages.some((message) => message.answer);

  const chartData = useMemo(() => {
    if (activeChartData) {
      return activeChartData;
    }

    return hasAiResponse ? null : defaultChartData;
  }, [activeChartData, hasAiResponse]);

  useEffect(() => {
    if (activeChartData) {
      setChartType(activeChartData.type);
    }
  }, [activeChartData]);

  const stats = activeStats.length ? activeStats : DEFAULT_STATS;

  return (
    <section className="flex min-h-0 flex-1 flex-col border-b border-border-0">
      <div className="flex h-8 flex-shrink-0 items-center justify-between border-b border-border-0 px-3 py-[7px]">
        <div className="font-mono text-[8px] uppercase tracking-[0.14em] text-text-3">
          VISUAL CONTEXT
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

      <div className="min-h-0 flex-1 px-3 pb-3 pt-2">
        <ChartDisplay data={chartData} chartType={chartType} />
      </div>
    </section>
  );
}
