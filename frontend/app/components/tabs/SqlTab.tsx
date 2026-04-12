"use client";

import { EmptyState } from "./EmptyState";
import { HighlightedCode } from "./HighlightedCode";
import { highlightSql } from "@/lib/utils";
import type { ChartPanel } from "@/lib/types";

interface SqlTabProps {
  sql?: string;
  chartPanels?: ChartPanel[];
}

export function SqlTab({ sql, chartPanels }: SqlTabProps) {
  // Multi-SQL: show one block per chart panel
  if (chartPanels && chartPanels.length > 0) {
    const sqlPanels = chartPanels.filter((p) => p.sql);
    if (sqlPanels.length > 0) {
      return (
        <div className="space-y-2">
          {sqlPanels.map((panel, i) => (
            <div
              key={`sql-${i}`}
              className="overflow-hidden rounded-lg border border-border-0 bg-bg-0"
            >
              <div className="flex items-center justify-between border-b border-border-0 bg-bg-2 px-3 py-[6px]">
                <span className="font-mono text-[9px] font-semibold text-text-3">
                  {sqlPanels.length > 1 ? `Query ${i + 1}` : "Snowflake SQL"}
                  {panel.title ? ` — ${panel.title}` : ""}
                </span>
                <button
                  type="button"
                  className="rounded border border-border-0 px-2 py-[2px] font-mono text-[8px] text-text-3 transition hover:border-blue-border hover:text-blue-text"
                  onClick={() => {
                    if (panel.sql) {
                      navigator.clipboard.writeText(panel.sql);
                    }
                  }}
                >
                  Copy
                </button>
              </div>
              <div className="max-h-[100px] overflow-y-auto px-3 py-2">
                <HighlightedCode tokens={highlightSql(panel.sql!)} />
              </div>
              <div className="flex gap-3 border-t border-border-0 px-3 py-[4px] text-[8px] text-text-3">
                <span>{panel.row_count} rows</span>
                <span
                  className={
                    panel.confidence_tier === "green"
                      ? "text-green"
                      : panel.confidence_tier === "amber"
                        ? "text-[#f59e0b]"
                        : "text-red"
                  }
                >
                  {Math.round(panel.confidence_score * 100)}% confidence
                </span>
              </div>
            </div>
          ))}
        </div>
      );
    }
  }

  // Fallback: single SQL
  if (!sql) {
    return <EmptyState>No SQL query for this response</EmptyState>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border-0 bg-bg-0">
      <div className="flex items-center justify-between border-b border-border-0 bg-bg-2 px-3 py-[6px]">
        <span className="font-mono text-[9px] font-semibold text-text-3">
          Snowflake SQL
        </span>
        <button
          type="button"
          className="rounded border border-border-0 px-2 py-[2px] font-mono text-[8px] text-text-3 transition hover:border-blue-border hover:text-blue-text"
          onClick={() => navigator.clipboard.writeText(sql)}
        >
          Copy
        </button>
      </div>
      <div className="px-3 py-2">
        <HighlightedCode tokens={highlightSql(sql)} />
      </div>
    </div>
  );
}
