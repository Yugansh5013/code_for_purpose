"use client";

import { useState } from "react";

import { cn } from "@/lib/utils";
import type { TraceEntry } from "@/lib/types";

interface ThinkingTraceProps {
  trace: TraceEntry[];
}

export function ThinkingTrace({ trace }: ThinkingTraceProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!trace.length) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        className="justify-self-end font-mono text-[9px] text-text-3 transition hover:text-text-1"
        onClick={() => setIsOpen((value) => !value)}
      >
        {isOpen ? "▴ TRACE" : "▾ TRACE"}
      </button>
      {isOpen ? (
        <div className="col-span-2 mt-2 rounded-[3px] border border-border-0 bg-bg-0 px-3 py-2 font-mono text-[10px] leading-[1.9]">
          {trace.map((entry) => (
            <div
              key={`${entry.node}-${entry.detail}`}
              className={cn(entry.highlight ? "text-green" : "text-text-3")}
            >
              <span
                className={cn(entry.highlight ? "text-green" : "text-text-1")}
              >
                → [{entry.node}]:
              </span>{" "}
              {entry.detail}
            </div>
          ))}
        </div>
      ) : null}
    </>
  );
}
