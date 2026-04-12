"use client";

import { useState } from "react";

import { CodeTab } from "./tabs/CodeTab";
import { ConfidenceTab } from "./tabs/ConfidenceTab";
import { ContextTab } from "./tabs/ContextTab";
import { DataTab } from "./tabs/DataTab";
import { LanguageTab } from "./tabs/LanguageTab";
import { SoqlTab } from "./tabs/SoqlTab";
import { SqlTab } from "./tabs/SqlTab";
import { useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";

type TransparencyTab =
  | "sql"
  | "soql"
  | "data"
  | "code"
  | "context"
  | "confidence"
  | "language";

const tabs = [
  { key: "sql", label: "SQL" },
  { key: "soql", label: "SOQL" },
  { key: "data", label: "DATA" },
  { key: "code", label: "CODE" },
  { key: "context", label: "CONTEXT" },
  { key: "confidence", label: "CONF." },
  { key: "language", label: "LANGUAGE" }
] satisfies Array<{ key: TransparencyTab; label: string }>;

export function TransparencyDashboard() {
  const transparency = useOmniDataStore((state) => state.activeTransparency);
  const [activeTab, setActiveTab] = useState<TransparencyTab>("sql");

  return (
    <section className="flex h-[268px] flex-shrink-0 flex-col bg-bg-1">
      <div className="flex overflow-x-auto border-b border-border-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={cn(
              "border-b-[1.5px] px-[9px] py-2 font-mono text-[8px] tracking-[0.08em] transition",
              activeTab === tab.key
                ? "border-blue text-blue-text"
                : "border-transparent text-text-3 hover:text-text-2"
            )}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-[10px]">
        {renderTab(activeTab, transparency)}
      </div>
    </section>
  );
}

function renderTab(
  tab: TransparencyTab,
  transparency: ReturnType<typeof useOmniDataStore.getState>["activeTransparency"]
) {
  switch (tab) {
    case "sql":
      return <SqlTab sql={transparency?.sql} />;
    case "soql":
      return <SoqlTab soql={transparency?.soql} />;
    case "data":
      return <DataTab rows={transparency?.raw_data} />;
    case "code":
      return <CodeTab code={transparency?.python_code} />;
    case "context":
      return <ContextTab chunks={transparency?.context_chunks} />;
    case "confidence":
      return <ConfidenceTab confidence={transparency?.confidence} />;
    case "language":
      return (
        <LanguageTab
          substitutions={transparency?.semantic_substitutions}
          validationPassed={transparency?.validation_passed}
          validatorModel={transparency?.validator_model}
          validatorLatencyMs={transparency?.validator_latency_ms}
        />
      );
  }
}
