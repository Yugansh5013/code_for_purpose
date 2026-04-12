"use client";

import { useState } from "react";

import { ConfidenceTab } from "./tabs/ConfidenceTab";
import { ContextTab } from "./tabs/ContextTab";
import { DataTab } from "./tabs/DataTab";
import { LanguageTab } from "./tabs/LanguageTab";
import { SqlTab } from "./tabs/SqlTab";
import { useOmniDataStore } from "@/lib/store";
import { cn } from "@/lib/utils";

type TransparencyTab =
  | "sql"
  | "data"
  | "docs"
  | "web"
  | "crm"
  | "context"
  | "confidence"
  | "language";

export function TransparencyDashboard() {
  const transparency = useOmniDataStore((state) => state.activeTransparency);
  const ragDocuments = useOmniDataStore((state) => state.ragDocuments);
  const webResults = useOmniDataStore((state) => state.webResults);
  const salesforceRecords = useOmniDataStore((state) => state.salesforceRecords);
  const chartPanels = useOmniDataStore((state) => state.chartPanels);
  const [activeTab, setActiveTab] = useState<TransparencyTab>("sql");

  // Build tabs dynamically based on available data
  const tabs: Array<{ key: TransparencyTab; label: string; count?: number }> = [
    { key: "sql", label: "SQL" },
    { key: "data", label: "DATA" },
  ];

  if (ragDocuments.length > 0) {
    tabs.push({ key: "docs", label: "DOCS", count: ragDocuments.length });
  }

  if (webResults.length > 0) {
    tabs.push({ key: "web", label: "WEB", count: webResults.length });
  }

  if (salesforceRecords.length > 0) {
    tabs.push({ key: "crm", label: "CRM", count: salesforceRecords.length });
  }

  tabs.push(
    { key: "context", label: "CONTEXT" },
    { key: "confidence", label: "CONF." },
    { key: "language", label: "LANGUAGE" }
  );

  return (
    <section className="flex min-h-[268px] flex-shrink-0 flex-col bg-bg-1">
      <div className="flex overflow-x-auto border-b border-border-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={cn(
              "flex items-center gap-1 border-b-[1.5px] px-[9px] py-2 font-mono text-[8px] tracking-[0.08em] transition whitespace-nowrap",
              activeTab === tab.key
                ? "border-blue text-blue-text"
                : "border-transparent text-text-3 hover:text-text-2"
            )}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
            {tab.count ? (
              <span className="rounded-sm bg-bg-2 px-1 py-[1px] text-[7px] text-text-3">
                {tab.count}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-[10px]">
        {activeTab === "sql" && <SqlTab sql={transparency?.sql} chartPanels={chartPanels} />}
        {activeTab === "data" && <DataTab rows={transparency?.raw_data} />}
        {activeTab === "docs" && <RagDocsTab documents={ragDocuments} />}
        {activeTab === "web" && <WebResultsTab results={webResults} />}
        {activeTab === "crm" && <CrmTab records={salesforceRecords} />}
        {activeTab === "context" && <ContextTab chunks={transparency?.context_chunks} />}
        {activeTab === "confidence" && <ConfidenceTab confidence={transparency?.confidence} />}
        {activeTab === "language" && (
          <LanguageTab
            substitutions={transparency?.semantic_substitutions}
            validationPassed={transparency?.validation_passed}
            validatorModel={transparency?.validator_model}
            validatorLatencyMs={transparency?.validator_latency_ms}
          />
        )}
      </div>
    </section>
  );
}


/* ── RAG Documents Tab (matches demo's "Knowledge Base Documents") ── */

import type { RagDocument } from "@/lib/types";

function RagDocsTab({ documents }: { documents: RagDocument[] }) {
  if (!documents.length) {
    return (
      <div className="flex items-center justify-center py-8 font-mono text-[10px] text-text-3">
        No knowledge base documents
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="mb-1 font-mono text-[8px] uppercase tracking-[0.1em] text-text-3">
        📄 Knowledge Base ({documents.length} documents)
      </div>
      {documents.map((doc, i) => (
        <RagDocCard key={`${doc.title}-${i}`} doc={doc} />
      ))}
    </div>
  );
}

function RagDocCard({ doc }: { doc: RagDocument }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round(doc.relevance * 100);
  const scoreColor =
    doc.relevance >= 0.8 ? "text-green" : doc.relevance >= 0.6 ? "text-[#f59e0b]" : "text-red";

  return (
    <div className="rounded-lg border border-border-0 bg-bg-0 p-3 transition hover:border-[#8b5cf6]">
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-semibold text-text-0 leading-tight">
          {doc.title}
        </span>
        <span className={cn("shrink-0 rounded-md bg-[#8b5cf615] px-[6px] py-[2px] text-[9px] font-semibold text-[#8b5cf6]")}>
          {scorePct}% match
        </span>
      </div>
      <div className="mt-1 flex items-center gap-1 text-[9px] text-text-3">
        📁 {doc.space || "AURA"}
      </div>
      <div className={cn("mt-2 text-[10px] leading-relaxed text-text-2", !expanded && "max-h-[60px] overflow-hidden relative")}>
        {doc.excerpt}
        {!expanded && (
          <div className="absolute bottom-0 left-0 right-0 h-5 bg-gradient-to-t from-bg-0 to-transparent" />
        )}
      </div>
      <button
        type="button"
        className="mt-1 w-full text-center text-[10px] text-[#8b5cf6] hover:underline"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Show less ▲" : "Show more ▼"}
      </button>
    </div>
  );
}


/* ── Web Results Tab (matches demo's "Web Intelligence") ── */

import type { WebResult } from "@/lib/types";

function WebResultsTab({ results }: { results: WebResult[] }) {
  if (!results.length) {
    return (
      <div className="flex items-center justify-center py-8 font-mono text-[10px] text-text-3">
        No web results
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="mb-1 font-mono text-[8px] uppercase tracking-[0.1em] text-text-3">
        🌐 Web Intelligence ({results.length} sources)
      </div>
      {results.map((result, i) => (
        <WebResultCard key={`${result.url}-${i}`} result={result} />
      ))}
    </div>
  );
}

function WebResultCard({ result }: { result: WebResult }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round(result.score * 100);

  let domain = "";
  try {
    domain = new URL(result.url).hostname.replace("www.", "");
  } catch {
    domain = result.url;
  }

  return (
    <div className="rounded-lg border border-border-0 bg-bg-0 p-3 transition hover:border-[#06b6d4]">
      <div className="flex items-start justify-between gap-2">
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] font-semibold text-[#06b6d4] hover:underline leading-tight"
        >
          {result.title}
        </a>
        <span className="shrink-0 rounded-md bg-[#06b6d415] px-[6px] py-[2px] text-[9px] font-semibold text-[#06b6d4]">
          {scorePct}%
        </span>
      </div>
      <div className="mt-1 text-[9px] text-text-3 truncate">
        🔗 {domain}
      </div>
      <div className={cn("mt-2 text-[10px] leading-relaxed text-text-2", !expanded && "max-h-[50px] overflow-hidden relative")}>
        {result.content}
        {!expanded && (
          <div className="absolute bottom-0 left-0 right-0 h-4 bg-gradient-to-t from-bg-0 to-transparent" />
        )}
      </div>
      <button
        type="button"
        className="mt-1 w-full text-center text-[10px] text-[#06b6d4] hover:underline"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Show less ▲" : "Show more ▼"}
      </button>
    </div>
  );
}


/* ── Salesforce CRM Tab ── */

import type { SalesforceRecord } from "@/lib/types";

function CrmTab({ records }: { records: SalesforceRecord[] }) {
  if (!records.length) {
    return (
      <div className="flex items-center justify-center py-8 font-mono text-[10px] text-text-3">
        No CRM records
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="mb-1 font-mono text-[8px] uppercase tracking-[0.1em] text-text-3">
        🏢 Salesforce CRM ({records.length} records)
      </div>
      {records.map((rec, i) => {
        const scorePct = Math.round(rec.relevance * 100);
        return (
          <div
            key={`${rec.account_name}-${i}`}
            className="rounded-lg border border-border-0 bg-bg-0 p-3 transition hover:border-[#8b5cf6]"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-[11px] font-semibold text-text-0">{rec.account_name}</span>
              <span className="shrink-0 rounded-md bg-[#8b5cf615] px-[6px] py-[2px] text-[9px] font-semibold text-[#8b5cf6]">
                {scorePct}%
              </span>
            </div>
            <div className="mt-1 text-[9px] text-text-3">{rec.object_type}</div>
            <div className="mt-2 text-[10px] leading-relaxed text-text-2 line-clamp-3">
              {rec.excerpt}
            </div>
          </div>
        );
      })}
    </div>
  );
}
