"use client";

import { useEffect, useMemo, useState } from "react";

import { getMetrics } from "@/lib/api";
import type { MetricEntry } from "@/lib/types";

export function MetricsGlossary() {
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let isMounted = true;

    getMetrics()
      .then((response) => {
        if (isMounted) {
          setMetrics(response.metrics);
        }
      })
      .catch((error) => {
        console.error(error);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredMetrics = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    if (!normalizedQuery) {
      return metrics;
    }

    return metrics.filter((metric) => {
      const aliases = metric.aliases.join(" ").toLowerCase();

      return (
        metric.name.toLowerCase().includes(normalizedQuery) ||
        metric.display_name.toLowerCase().includes(normalizedQuery) ||
        aliases.includes(normalizedQuery)
      );
    });
  }, [metrics, query]);

  return (
    <section className="flex flex-1 flex-col overflow-hidden bg-bg-0">
      <input
        value={query}
        placeholder="Search metrics..."
        className="m-3 w-[calc(100%-24px)] rounded-[3px] border border-border-0 bg-bg-0 px-3 py-[9px] font-mono text-[11px] text-text-0 outline-none placeholder:text-text-3 focus:border-blue-border"
        onChange={(event) => setQuery(event.target.value)}
      />

      <div className="flex-1 overflow-y-auto px-[14px] pb-3">
        {filteredMetrics.map((metric) => (
          <article
            key={metric.canonical_column}
            className="border-b border-border-0 py-2"
          >
            <div className="font-mono text-[10px] font-medium text-text-0">
              {metric.display_name}{" "}
              <span className="font-normal text-text-3">[{metric.unit}]</span>
            </div>
            <div className="mt-1 font-mono text-[9px] text-blue-text">
              → {metric.canonical_column}
            </div>
            <p className="mt-1 font-sans text-[10px] leading-[1.5] text-text-2">
              {metric.description}
            </p>
            <div className="mt-1 font-mono text-[9px] text-text-3">
              aliases: {metric.aliases.join(", ")}
            </div>
          </article>
        ))}

        {filteredMetrics.length === 0 ? (
          <div className="py-8 text-center font-mono text-[10px] text-text-3">
            No matching metrics found.
          </div>
        ) : null}
      </div>
    </section>
  );
}
