"use client";

import {
  Bot,
  Clock3,
  FileText,
  MessageSquare,
  UserRound
} from "lucide-react";

import { createSessionId, useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import type { ActiveNav, IntegrationStatus } from "@/lib/types";

const navItems = [
  { key: "chat", label: "Chat", icon: MessageSquare },
  { key: "agents", label: "Agents", icon: Bot },
  { key: "history", label: "History", icon: Clock3 },
  { key: "glossary", label: "Metrics Glossary", icon: FileText },
  { key: "profile", label: "Profile", icon: UserRound }
] satisfies Array<{
  key: ActiveNav;
  label: string;
  icon: typeof MessageSquare;
}>;

const recentSessions = [
  "Refund policy and return rates",
  "Revenue by region last month",
  "Churn risk accounts",
  "YTD sales vs target"
];

export function Sidebar() {
  const activeNav = useOmniDataStore((state) => state.activeNav);
  const setActiveNav = useOmniDataStore((state) => state.setActiveNav);
  const integrationStatus = useOmniDataStore(
    (state) => state.integrationStatus
  );
  const resetSession = useOmniDataStore((state) => state.resetSession);
  const addMessage = useOmniDataStore((state) => state.addMessage);

  const startNewSession = () => {
    resetSession();
    addMessage({
      id: createSessionId(),
      role: "system",
      content: `— NEW SESSION · ${formatClockTime()} —`,
      timestamp: new Date()
    });
    setActiveNav("chat");
  };

  return (
    <aside className="w-[196px] overflow-y-auto border-r border-border-0 bg-bg-1">
      <section className="border-b border-border-0 px-[14px] py-[13px]">
        <button
          type="button"
          className="w-full rounded-[3px] border border-blue-border bg-blue-dim px-3 py-[8px] font-mono text-[10px] tracking-[0.06em] text-blue transition hover:bg-[#1e3a5c]"
          onClick={startNewSession}
        >
          + NEW SESSION
        </button>
      </section>

      <SidebarSection label="NAVIGATION">
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeNav === item.key;

            return (
              <button
                key={item.key}
                type="button"
                className={cn(
                  "flex h-8 w-full items-center gap-2 border-l-2 px-[14px] py-[7px] text-left font-sans text-[12px] transition",
                  isActive
                    ? "border-blue bg-bg-2 text-[#e8edf5]"
                    : "border-transparent text-text-1 hover:bg-bg-2 hover:text-[#e8edf5]"
                )}
                onClick={() => setActiveNav(item.key)}
              >
                <Icon size={13} className="opacity-55" />
                <span className="truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </SidebarSection>

      <SidebarSection label="INTEGRATIONS">
        <div className="space-y-1 pb-1">
          <IntegrationRow
            source="snowflake"
            name="Snowflake"
            colourClass="bg-green"
            status={integrationStatus.snowflake}
          />
          <IntegrationRow
            source="confluence"
            name="Confluence"
            colourClass="bg-amber"
            status={integrationStatus.confluence}
          />
          <IntegrationRow
            source="salesforce"
            name="Salesforce"
            colourClass="bg-blue"
            status={integrationStatus.salesforce}
          />
          <IntegrationRow
            source="tavily"
            name="Tavily"
            colourClass="bg-purple"
            status={integrationStatus.tavily}
          />
        </div>
      </SidebarSection>

      <SidebarSection label="RECENT SESSIONS">
        <div className="pb-2">
          {recentSessions.map((query) => (
            <button
              key={query}
              type="button"
              className="block w-full truncate px-[14px] py-[6px] text-left font-mono text-[10px] text-text-2 transition hover:bg-bg-2 hover:text-text-1"
              onClick={() => {
                setActiveNav("chat");
                window.setTimeout(() => {
                  window.dispatchEvent(
                    new CustomEvent("omnidata:prefill-query", {
                      detail: query
                    })
                  );
                }, 0);
              }}
            >
              {query}
            </button>
          ))}
        </div>
      </SidebarSection>
    </aside>
  );
}

interface SidebarSectionProps {
  label: string;
  children: React.ReactNode;
}

function SidebarSection({ label, children }: SidebarSectionProps) {
  return (
    <section className="border-b border-border-0 py-3">
      <div className="mb-2 px-[14px] font-mono text-[8px] uppercase tracking-[0.14em] text-text-3">
        {label}
      </div>
      {children}
    </section>
  );
}

interface IntegrationRowProps {
  source: "snowflake" | "confluence" | "salesforce" | "tavily";
  name: string;
  colourClass: string;
  status: IntegrationStatus[keyof IntegrationStatus];
}

function IntegrationRow({
  source,
  name,
  colourClass,
  status
}: IntegrationRowProps) {
  const badge = integrationBadge(source, status);

  return (
    <div className="flex items-center justify-between px-[14px] py-[5px]">
      <div className="flex min-w-0 items-center gap-2">
        <span className={cn("h-[5px] w-[5px] rounded-full", colourClass)} />
        <span className="truncate font-sans text-[11px] text-text-1">
          {name}
        </span>
      </div>
      <span
        className={cn(
          "rounded-[2px] px-[5px] py-[2px] font-mono text-[8px]",
          badge.className
        )}
      >
        {badge.label}
      </span>
    </div>
  );
}

function integrationBadge(
  source: IntegrationRowProps["source"],
  status: IntegrationStatus[keyof IntegrationStatus]
) {
  if (status === "error") {
    return { label: "ERR", className: "bg-red-dim text-red" };
  }

  if (status === "connecting") {
    return { label: "CONN", className: "bg-blue-dim text-blue-text" };
  }

  switch (source) {
    case "snowflake":
      return { label: "LIVE", className: "bg-green-dim text-green" };
    case "confluence":
      return { label: "SYNC", className: "bg-amber-dim text-amber" };
    case "salesforce":
      return { label: "OK", className: "bg-blue-dim text-blue-text" };
    case "tavily":
      return { label: "WEB", className: "bg-purple-dim text-purple" };
  }
}

function formatClockTime(): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  }).format(new Date());
}
