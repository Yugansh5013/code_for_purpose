"use client";

import { useEffect, useState } from "react";

import { getStatus } from "@/lib/api";
import { useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { IntegrationStatus } from "@/lib/types";

const statusPills = [
  {
    key: "snowflake",
    name: "SNOWFLAKE",
    dotClass: "bg-green",
    pulseSeconds: 2,
    liveLabel: "LIVE"
  },
  {
    key: "confluence",
    name: "CONFLUENCE",
    dotClass: "bg-amber",
    pulseSeconds: 2.5,
    liveLabel: "SYNC"
  },
  {
    key: "salesforce",
    name: "SALESFORCE",
    dotClass: "bg-blue",
    pulseSeconds: 3,
    liveLabel: "OK"
  },
  {
    key: "tavily",
    name: "TAVILY",
    dotClass: "bg-purple",
    pulseSeconds: null,
    liveLabel: "WEB"
  }
] as const;

export function Topbar() {
  const integrationStatus = useOmniDataStore(
    (state) => state.integrationStatus
  );
  const setIntegrationStatus = useOmniDataStore(
    (state) => state.setIntegrationStatus
  );
  const [clock, setClock] = useState("--:--:--");

  useEffect(() => {
    const updateClock = () => {
      setClock(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false
        }).format(new Date())
      );
    };

    updateClock();
    const intervalId = window.setInterval(updateClock, 1000);

    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    let isMounted = true;

    getStatus()
      .then((status) => {
        if (isMounted) {
          setIntegrationStatus(status);
        }
      })
      .catch((error) => {
        console.error(error);
      });

    return () => {
      isMounted = false;
    };
  }, [setIntegrationStatus]);

  return (
    <header className="flex h-[38px] items-center justify-between border-b border-border-0 bg-bg-1 px-4">
      <div className="flex items-baseline gap-3">
        <div className="font-mono text-[13px] font-medium text-[#e8edf5]">
          OMNI<span className="text-blue">DATA</span>
        </div>
        <div className="font-mono text-[9px] text-text-3">
          v1.0 · ENTERPRISE ANALYTICS TERMINAL
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          {statusPills.map((pill) => (
            <StatusPill
              key={pill.key}
              name={pill.name}
              value={integrationStatus[pill.key]}
              dotClass={pill.dotClass}
              pulseSeconds={pill.pulseSeconds}
              liveLabel={pill.liveLabel}
            />
          ))}
        </div>
        <div className="font-mono text-[10px] text-text-3">{clock}</div>
      </div>
    </header>
  );
}

interface StatusPillProps {
  name: string;
  value: IntegrationStatus[keyof IntegrationStatus];
  dotClass: string;
  pulseSeconds: number | null;
  liveLabel: string;
}

function StatusPill({
  name,
  value,
  dotClass,
  pulseSeconds,
  liveLabel
}: StatusPillProps) {
  const isError = value === "error";
  const label =
    value === "error"
      ? "ERR"
      : value === "connecting"
        ? "CONN"
        : liveLabel;

  return (
    <div className="flex items-center gap-[5px] font-mono text-[9px] uppercase tracking-[0.06em] text-text-2">
      <span
        className={cn(
          "h-[5px] w-[5px] rounded-full",
          isError ? "bg-red" : dotClass,
          pulseSeconds ? "animate-status-pulse" : ""
        )}
        style={
          pulseSeconds
            ? { animationDuration: `${pulseSeconds}s` }
          : undefined
        }
      />
      {name} {label}
    </div>
  );
}
