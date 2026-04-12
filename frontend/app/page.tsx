"use client";

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Bar, Line, Pie } from "react-chartjs-2";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  ArcElement,
  PointElement,
  Tooltip,
  Legend,
  Filler
);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CHART_COLORS = [
  "#3b82f6",
  "#8b5cf6",
  "#06b6d4",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
];

/* ################################################################
   Types
   ################################################################ */

interface ChartPanel {
  title: string;
  chart_type: string;
  data: Record<string, unknown>[];
  columns: string[];
  sql?: string;
  row_count: number;
  confidence_score: number;
  confidence_tier: string;
}

interface RagDoc {
  title: string;
  space: string;
  excerpt: string;
  relevance: number;
}

interface WebResult {
  title: string;
  url: string;
  content: string;
  score: number;
}

interface SFRecord {
  account_name: string;
  object_type: string;
  excerpt: string;
  relevance: number;
}

interface JargonSub {
  original: string;
  replacement: string;
  category: string;
}

interface Source {
  source_type: string;
  label: string;
  confidence?: number;
}

interface TraceEntry {
  node: string;
  detail: string;
  highlight?: boolean;
}

interface AnswerPayload {
  text: string;
  branches: string[];
  trace: TraceEntry[];
  date_resolution?: string;
  sources: Source[];
  transparency: {
    sql?: string;
    raw_data?: Record<string, unknown>[];
    confidence?: {
      score: number;
      tier: string;
      signals: Record<string, number>;
      explanation: string;
    };
    semantic_substitutions?: {
      original: string;
      replaced_with: string;
      location: string;
    }[];
  };
  chart_data?: {
    type: string;
    labels: string[];
    values: number[];
    y_label?: string;
  };
  charts?: ChartPanel[];
  rag_documents?: RagDoc[];
  web_results?: WebResult[];
  salesforce_records?: SFRecord[];
  jargon_substitutions?: JargonSub[];
  confidence_score?: number;
  confidence_tier?: string;
  processing_time_ms?: number;
}

interface ChatMsg {
  id: string;
  role: "user" | "bot" | "clarification";
  content: string;
  answer?: AnswerPayload;
  clarificationOptions?: unknown[];
  originalQuery?: string;
  streamingTrace?: TraceEntry[];
}

/* ################################################################
   Main Page Component
   ################################################################ */

export default function OmniDataPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<string>("connecting");
  const [healthServices, setHealthServices] = useState<Record<string,string>>({});
  const [panelData, setPanelData] = useState<AnswerPayload | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages, loading]);

  // Health check
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API_URL}/api/status`, { signal: AbortSignal.timeout(5000) });
        const d = await r.json();
        setHealthServices(d);
        const allOk = Object.values(d).every((v) =>
          typeof v === "string" && (v === "live" || v.startsWith("ok"))
        );
        setHealth(allOk ? "healthy" : "degraded");
      } catch {
        setHealth("offline");
      }
    };
    check();
    const iv = setInterval(check, 30000);
    return () => clearInterval(iv);
  }, []);

  // Send query
  const sendQuery = useCallback(
    async (query: string, clarificationAnswer?: string) => {
      if (!query.trim() || loading) return;
      setLoading(true);

      const msgId = `msg-${Date.now()}`;
      
      if (!clarificationAnswer) {
        setMessages((m) => [
          ...m,
          { id: `u-${Date.now()}`, role: "user", content: query },
          { id: msgId, role: "bot", content: "", streamingTrace: [] }
        ]);
        setInput("");
      } else {
        setMessages((m) => [
          ...m,
          { id: msgId, role: "bot", content: "", streamingTrace: [] }
        ]);
      }

      try {
        const r = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: "session-" + Date.now(),
            message: query,
            clarification_answer: clarificationAnswer,
          }),
        });

        const reader = r.body?.getReader();
        const decoder = new TextDecoder("utf-8");

        if (reader) {
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const dataString = line.substring(6);
                try {
                  const data = JSON.parse(dataString);
                  if (data.type === "trace") {
                    setMessages((m) => m.map((msg) => {
                      if (msg.id === msgId) {
                        return { ...msg, streamingTrace: [...(msg.streamingTrace || []), { node: data.node, detail: data.detail }] };
                      }
                      return msg;
                    }));
                  } else if (data.type === "clarification") {
                    setMessages((m) => m.map((msg) => {
                      if (msg.id === msgId) {
                        return {
                          ...msg,
                          id: data.message_id || msgId,
                          role: "clarification",
                          content: data.clarification.question,
                          clarificationOptions: data.clarification.options,
                          originalQuery: query,
                          streamingTrace: undefined
                        };
                      }
                      return msg;
                    }));
                  } else if (data.type === "answer") {
                    setMessages((m) => m.map((msg) => {
                      if (msg.id === msgId) {
                        return {
                          ...msg,
                          id: data.message_id || msgId,
                          role: "bot",
                          content: data.answer.text,
                          answer: data.answer,
                          streamingTrace: undefined
                        };
                      }
                      return msg;
                    }));
                    setPanelData(data.answer);
                  } else if (data.type === "error") {
                    setMessages((m) => m.map((msg) => {
                      if (msg.id === msgId) {
                        return { ...msg, content: `Error: ${data.detail}`, streamingTrace: undefined };
                      }
                      return msg;
                    }));
                  }
                } catch (err) {
                  console.error("Parse error:", err, dataString);
                }
              }
            }
          }
        }
      } catch (e: unknown) {
        const errMsg = e instanceof Error ? e.message : "Unknown error";
        setMessages((m) => m.map((msg) => {
          if (msg.id === msgId) {
            return { ...msg, content: `Error: ${errMsg}. Is the backend running?`, streamingTrace: undefined };
          }
          return msg;
        }));
      }
      setLoading(false);
    },
    [loading]
  );

  const askSuggested = (text: string) => {
    setInput("");
    sendQuery(text);
  };

  return (
    <>
      <div className="bg-grid" />
      <div className="app">
        {/* ── Left Sidebar ── */}
        <Sidebar onNewSession={() => { setMessages([]); setPanelData(null); setInput(""); }} healthServices={healthServices} />

        {/* ── Chat Panel ── */}
        <div className="main-panel">
          <div className="chat-area" ref={chatRef}>
            {messages.length === 0 && (
              <div className="welcome">
                <div className="welcome-icon">⚡</div>
                <h1>Ask anything about Aura Retail</h1>
                <p>
                  Query sales data, internal policies, market intelligence, and
                  more — powered by multi-source AI.
                </p>
                <div className="suggested-queries">
                  {[
                    "Total sales by region in Q1 2026?",
                    "Why did South region revenue drop in February?",
                    "What does our returns policy say about defective products?",
                    "Why are returns spiking for AuraSound Pro?",
                    "SMB churn trends in the South",
                    "How does AuraSound Pro compare to competitors?",
                    "What's happening in the UK headphone market?",
                  ].map((q) => (
                    <button
                      key={q}
                      className="suggested-btn"
                      onClick={() => askSuggested(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                onClarify={(oq, cv) => sendQuery(oq, cv)}
              />
            ))}

            {loading && <ThinkingDots />}
          </div>

          {/* ── Input Bar ── */}
          <div className="input-zone">
            <div className="action-row">
              <button className="action-btn" onClick={() => askSuggested("Deep Analytics on Q1 Sales")}>📊 Deep Analytics</button>
              <button className="action-btn" onClick={() => askSuggested("Audit our Return Policy")}>📄 Policy Audit</button>
              <button className="action-btn" onClick={() => askSuggested("Check Salesforce Churn")}>☁️ CRM Churn</button>
              <button className="action-btn" onClick={() => askSuggested("Search Web Competitors")}>🌐 Web Intel</button>
            </div>
            <div className="input-bar">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about sales, churn, products, market trends..."
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendQuery(input);
                }
              }}
            />
            <button
              className="send-btn"
              disabled={!input.trim() || loading}
              onClick={() => sendQuery(input)}
            >
              ➤
            </button>
            </div>
          </div>
        </div>

        {/* ── Right Panel ── */}
        <RightPanel data={panelData} />
      </div>
    </>
  );
}

/* ################################################################
   Sidebar
   ################################################################ */

function Sidebar({ 
  onNewSession, 
  healthServices 
}: { 
  onNewSession: () => void, 
  healthServices: Record<string, string> 
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">⚡</div>
          <span className="logo-text">OmniData</span>
          <span className="logo-badge">PHASE 3</span>
        </div>
        <button className="new-chat-btn" onClick={onNewSession}>
          + New Session
        </button>
      </div>

      <div className="sidebar-section">
        <h4 className="sidebar-title">DATA SOURCES</h4>
        <div className="source-list">
          <StatusItem label="Snowflake DWH" status={healthServices.snowflake} icon="❄️" />
          <StatusItem label="Confluence Docs" status={healthServices.confluence} icon="📄" />
          <StatusItem label="Salesforce CRM" status={healthServices.salesforce} icon="☁️" />
          <StatusItem label="Tavily Web Search" status={healthServices.tavily} icon="🌐" />
        </div>
      </div>

      <div className="sidebar-section">
        <h4 className="sidebar-title">RECENT CHATS</h4>
        <div className="recent-list">
          <div className="recent-chat">Total sales by region Q1...</div>
          <div className="recent-chat">Why did South revenue drop...</div>
          <div className="recent-chat">Returns policy on defective...</div>
        </div>
      </div>
    </div>
  );
}

function StatusItem({ label, status, icon }: { label: string; status?: string; icon: string }) {
  const isLive = status === "live" || (status && status.startsWith("ok"));
  const isSyncing = status === "syncing" || status === "connecting";
  const dotColor = isLive ? "var(--accent-green)" : isSyncing ? "var(--accent-amber)" : "var(--accent-red)";
  const shortLabel = status === "live" ? "Live" : status === "syncing" ? "Sync" : status === "connecting" ? "Conn" : status === "error" ? "Err" : "Web";
  
  return (
    <div className="source-item">
      <div className="source-info">
        <span className="source-icon">{icon}</span>
        <span className="source-label">{label}</span>
      </div>
      <div className="status-pill-small">
        <span className="source-dot" style={{ backgroundColor: dotColor, boxShadow: `0 0 6px ${dotColor}` }} />
        <span className="short-label">{shortLabel}</span>
      </div>
    </div>
  );
}

/* ################################################################
   Message Bubble
   ################################################################ */

function MessageBubble({
  msg,
  onClarify,
}: {
  msg: ChatMsg;
  onClarify: (oq: string, cv: string) => void;
}) {
  if (msg.role === "user") {
    return (
      <div className="message user">
        <div className="msg-avatar">👤</div>
        <div className="msg-content">{msg.content}</div>
      </div>
    );
  }

  if (msg.role === "clarification") {
    return (
      <div className="message bot">
        <div className="msg-avatar">⚡</div>
        <div className="msg-content">
          <p>{msg.content}</p>
          <div className="clarification-box">
            <h4>⚡ Which metric did you mean?</h4>
            <div className="clarification-options">
              {(msg.clarificationOptions as string[] || []).map((opt) => (
                <button
                  key={String(opt)}
                  className="clarification-btn"
                  onClick={() => onClarify(msg.originalQuery || "", String(opt))}
                >
                  <div className="label">{String(opt)}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Bot answer
  const a = msg.answer;
  const tier = a?.confidence_tier || "green";
  const score = a?.confidence_score || 0;
  const tierLabel = tier === "green" ? "HIGH" : tier === "amber" ? "MEDIUM" : "LOW";
  const timeStr = a?.processing_time_ms ? `${(a.processing_time_ms / 1000).toFixed(1)}s` : "";
  const chartCount = a?.charts?.length || 0;

  return (
    <div className="message bot">
      <div className="msg-avatar">⚡</div>
      <div className="msg-content">
        {/* Live Trace */}
        {(a?.trace || msg.streamingTrace) && (
          <LiveTraceUI trace={a?.trace || msg.streamingTrace || []} isComplete={!!a} />
        )}

        {/* Response text */}
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        </div>

        {/* Date + metric resolution */}
        {a?.date_resolution && (
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
            📅 {a.date_resolution}
          </p>
        )}

        {/* Meta row */}
        {a && (
          <div className="msg-meta">
            <span className={`confidence-badge ${tier}`}>
              <span className={`confidence-dot ${tier}`} />
              {tierLabel} ({Math.round(score * 100)}%)
            </span>
            {a?.sources?.map((s, i) => (
              <span key={i} className="source-chip">📡 {s.label}</span>
            ))}
            {chartCount > 1 && (
              <span className="multi-query-tag">📊 {chartCount} charts</span>
            )}
            {timeStr && <span className="time-chip">⏱ {timeStr}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ################################################################
   Live Trace UI
   ################################################################ */

function LiveTraceUI({ trace, isComplete }: { trace: TraceEntry[], isComplete: boolean }) {
  const [open, setOpen] = useState(false);

  if (isComplete && !open) {
    const count = trace.length > 0 ? trace.length : 1;
    return (
      <button className="trace-summary-btn" onClick={() => setOpen(true)}>
        <span style={{color: 'var(--accent-green)'}}>✓</span> Processed {count} steps
      </button>
    );
  }

  return (
    <div className="live-trace-container">
      {isComplete && (
        <button className="trace-summary-btn" onClick={() => setOpen(false)} style={{marginBottom: 8}}>
          ▾ Hide Trace
        </button>
      )}
      
      {trace.length === 0 && !isComplete && (
        <div className="live-trace-step">
          <div className="live-trace-icon trace-active">⚡</div>
          <div className="trace-text active">Initializing Agentic Tools...</div>
        </div>
      )}

      {trace.map((t, i) => {
        const isLastAndActive = !isComplete && i === trace.length - 1;
        return (
          <div key={i} className="live-trace-step">
            <div className={`live-trace-icon ${isLastAndActive ? 'trace-active' : 'trace-completed'}`}>
              {isLastAndActive ? '⚡' : '✓'}
            </div>
            <div className={`trace-text ${isLastAndActive ? 'active' : ''}`}>
              {t.detail}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ################################################################
   Thinking Dots
   ################################################################ */

function ThinkingDots() {
  return (
    <div className="thinking">
      <div className="thinking-avatar">⚡</div>
      <div className="thinking-dots">
        <div className="thinking-dot" />
        <div className="thinking-dot" />
        <div className="thinking-dot" />
      </div>
    </div>
  );
}

/* ################################################################
   Right Panel
   ################################################################ */

function RightPanel({ data }: { data: AnswerPayload | null }) {
  if (!data) {
    return (
      <div className="right-panel">
        <div className="empty-panel">
          <div className="empty-panel-icon">📊</div>
          <div>Charts, SQL, and confidence scores will appear here when you ask a question.</div>
        </div>
      </div>
    );
  }

  const charts = data.charts || [];
  const ragDocs = data.rag_documents || [];
  const webResults = data.web_results || [];
  const sfRecords = data.salesforce_records || [];
  const jargonSubs = data.jargon_substitutions || [];
  const rawData = data.transparency?.raw_data || (charts.length > 0 ? charts[0].data as Record<string,unknown>[] : null);

  return (
    <div className="right-panel">
      {/* Charts */}
      {charts.length > 0 && (
        <div className="panel-section">
          <h3>📊 Visualizations{charts.length > 1 ? ` (${charts.length})` : ""}</h3>
          {charts.map((c, i) => (
            <ChartCard key={i} chart={c} colorIdx={i} />
          ))}
        </div>
      )}

      {/* RAG Documents */}
      {ragDocs.length > 0 && (
        <div className="panel-section">
          <h3>📄 Knowledge Base{ragDocs.length > 1 ? ` (${ragDocs.length} documents)` : ""}</h3>
          {ragDocs.map((doc, i) => (
            <RagCard key={i} doc={doc} />
          ))}
        </div>
      )}

      {/* Web Results */}
      {webResults.length > 0 && (
        <div className="panel-section">
          <h3>🌐 Web Intelligence{webResults.length > 1 ? ` (${webResults.length} sources)` : ""}</h3>
          {webResults.map((wr, i) => (
            <WebCard key={i} result={wr} />
          ))}
        </div>
      )}

      {/* Salesforce CRM */}
      {sfRecords.length > 0 && (
        <div className="panel-section">
          <h3>🏢 Salesforce CRM ({sfRecords.length} records)</h3>
          {sfRecords.map((rec, i) => (
            <SFCard key={i} record={rec} />
          ))}
        </div>
      )}

      {/* Language Audit */}
      {jargonSubs.length > 0 && (
        <div className="panel-section">
          <h3>🔤 Language Audit ({jargonSubs.length} terms rewritten)</h3>
          {jargonSubs.map((sub, i) => (
            <div key={i} className="lang-card">
              <span className="lang-original">{sub.original}</span>
              <span className="lang-arrow">→</span>
              <span className="lang-replacement">{sub.replacement}</span>
              <span className={`lang-category ${sub.category}`}>{sub.category.replace(/_/g, " ")}</span>
            </div>
          ))}
        </div>
      )}

      {/* Raw Data */}
      {rawData && rawData.length > 0 && (
        <div className="panel-section">
          <h3>🗃️ Raw Data</h3>
          <DataTable rows={rawData} />
        </div>
      )}

      {/* SQL */}
      {charts.some((c) => c.sql) && (
        <div className="panel-section">
          <h3>🔍 Generated SQL</h3>
          {charts
            .filter((c) => c.sql)
            .map((c, i) => (
              <SqlBlock key={i} sql={c.sql!} label={charts.length > 1 ? `Query ${i + 1}${c.title ? ` — ${c.title}` : ""}` : "Snowflake SQL"} />
            ))}
        </div>
      )}

      {/* Single SQL fallback */}
      {data.transparency?.sql && !charts.some((c) => c.sql) && (
        <div className="panel-section">
          <h3>🔍 Generated SQL</h3>
          <SqlBlock sql={data.transparency.sql} label="Snowflake SQL" />
        </div>
      )}

      {/* Confidence */}
      {data.confidence_score != null && (
        <div className="panel-section">
          <h3>🛡️ Confidence</h3>
          <ConfidencePanel score={data.confidence_score} tier={data.confidence_tier || "green"} charts={charts} rawData={rawData} />
        </div>
      )}
    </div>
  );
}

/* ################################################################
   Chart Card (renders each chart with Chart.js)
   ################################################################ */

function ChartCard({ chart, colorIdx }: { chart: ChartPanel; colorIdx: number }) {
  if (!chart.data?.length) return null;

  // Number card
  if (chart.chart_type === "number") {
    const row = chart.data[0];
    const keys = Object.keys(row);
    const numKey = keys.find((k) => {
      const v = row[k];
      if (typeof v === "number") return true;
      if (typeof v === "string") {
        const cleanVal = v.replace(/[%£$€,]/g, "");
        return cleanVal !== "" && !isNaN(Number(cleanVal));
      }
      return false;
    }) || keys[keys.length - 1];
    
    let val = 0;
    const rawVal = row[numKey];
    if (typeof rawVal === "number") {
      val = rawVal;
    } else if (typeof rawVal === "string") {
      val = parseFloat(rawVal.replace(/[%£$€,]/g, "")) || 0;
    }
    return (
      <div className="chart-container">
        {chart.title && (
          <div className="chart-title">
            <span>{chart.title}</span>
            <span className={`conf-pill ${chart.confidence_tier}`}>{Math.round(chart.confidence_score * 100)}%</span>
          </div>
        )}
        <div className="number-card">
          <div className="value">{formatNumber(val)}</div>
          <div className="label">{(numKey || "").replace(/_/g, " ")}</div>
        </div>
      </div>
    );
  }

  // Chart
  const keys = Object.keys(chart.data[0]);
  const labelKey = keys[0];
  const numericKeys = keys.filter((k) => {
    const v = chart.data[0][k];
    if (k === labelKey) return false;
    if (typeof v === "number") return true;
    if (typeof v === "string") {
      const cleanVal = v.replace(/[%£$€,]/g, "");
      return cleanVal !== "" && !isNaN(Number(cleanVal));
    }
    return false;
  });

  if (!numericKeys.length) return null;

  const labels = chart.data.map((r) => {
    let v = String(r[labelKey] ?? "");
    if (v.match(/^\d{4}-\d{2}/)) v = v.substring(0, 7);
    return v;
  });

  const chartType = chart.chart_type === "line" ? "line" : chart.chart_type === "pie" || chart.chart_type === "doughnut" ? "doughnut" : "bar";

  const datasets = numericKeys.slice(0, 3).map((key, j) => {
    const c = CHART_COLORS[(colorIdx + j) % CHART_COLORS.length];
    const values = chart.data.map((r) => {
      const v = r[key];
      if (typeof v === "number") return v;
      const cleanVal = String(v).replace(/[%£$€,]/g, "");
      return parseFloat(cleanVal) || 0;
    });

    return {
      label: key.replace(/_/g, " "),
      data: values,
      backgroundColor:
        chartType === "doughnut"
          ? chart.data.map((_, idx) => CHART_COLORS[idx % CHART_COLORS.length] + "90")
          : chartType === "bar"
          ? c + "80"
          : c + "20",
      borderColor: chartType === "doughnut" ? "#0a0e1a" : c,
      borderWidth: 2,
      tension: 0.3,
      pointRadius: chartType === "line" ? 3 : 0,
      pointBackgroundColor: c,
      fill: chartType === "line",
    };
  });

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "#94a3b8", font: { family: "Inter", size: 10 } },
        position: (chartType === "doughnut" ? "bottom" : "top") as const,
      },
    },
    scales:
      chartType === "doughnut"
        ? {}
        : {
            x: {
              ticks: { color: "#64748b", font: { size: 9 }, maxRotation: 45 },
              grid: { color: "#1e293b40" },
            },
            y: {
              ticks: { color: "#64748b", font: { size: 9 } },
              grid: { color: "#1e293b40" },
            },
          },
  };

  const chartData = { labels, datasets };
  const ChartComponent = chartType === "line" ? Line : chartType === "doughnut" ? Pie : Bar;

  return (
    <div className="chart-container">
      {(chart.title || true) && (
        <div className="chart-title">
          <span>{chart.title || `Chart ${colorIdx + 1}`}</span>
          <span className={`conf-pill ${chart.confidence_tier}`}>{Math.round(chart.confidence_score * 100)}%</span>
        </div>
      )}
      <div style={{ height: 180 }}>
        <ChartComponent data={chartData} options={options as any} />
      </div>
    </div>
  );
}

/* ################################################################
   RAG Doc Card
   ################################################################ */

function RagCard({ doc }: { doc: RagDoc }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round(doc.relevance * 100);

  let excerpt = doc.excerpt || "";
  const titleEnd = excerpt.indexOf("\n\n");
  if (titleEnd > 0 && titleEnd < 100) excerpt = excerpt.substring(titleEnd + 2);

  return (
    <div className={`rag-card${expanded ? " expanded" : ""}`}>
      <div className="rag-card-header">
        <span className="rag-card-title">{doc.title}</span>
        <span className="rag-card-score">{scorePct}% match</span>
      </div>
      <div className="rag-card-space">📁 {doc.space || "AURA"}</div>
      <div className="rag-card-excerpt">{excerpt.substring(0, 400)}</div>
      <button className="rag-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Show less ▲" : "Show more ▼"}
      </button>
    </div>
  );
}

/* ################################################################
   Web Card
   ################################################################ */

function WebCard({ result }: { result: WebResult }) {
  const [expanded, setExpanded] = useState(false);
  const scorePct = Math.round(result.score * 100);
  let domain = "";
  try { domain = new URL(result.url).hostname.replace("www.", ""); } catch { domain = result.url; }

  return (
    <div className={`web-card${expanded ? " expanded" : ""}`}>
      <div className="web-card-header">
        <span className="web-card-title"><a href={result.url} target="_blank" rel="noopener noreferrer">{result.title}</a></span>
        <span className="web-card-score">{scorePct}%</span>
      </div>
      <div className="web-card-url">🔗 {domain}</div>
      <div className="web-card-content">{result.content}</div>
      <button className="web-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Show less ▲" : "Show more ▼"}
      </button>
    </div>
  );
}

/* ################################################################
   Salesforce Card
   ################################################################ */

function SFCard({ record }: { record: SFRecord }) {
  const scorePct = Math.round(record.relevance * 100);
  return (
    <div className="rag-card">
      <div className="rag-card-header">
        <span className="rag-card-title">🏢 {record.account_name}</span>
        <span className="rag-card-score">{scorePct}%</span>
      </div>
      <div className="rag-card-space">{record.object_type}</div>
      <div className="rag-card-excerpt" style={{ maxHeight: "none" }}>{record.excerpt}</div>
    </div>
  );
}

/* ################################################################
   SQL Block
   ################################################################ */

function SqlBlock({ sql, label }: { sql: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="sql-block">
      <div className="sql-header">
        <span>{label}</span>
        <button className="copy-btn" onClick={() => { navigator.clipboard.writeText(sql); setCopied(true); setTimeout(() => setCopied(false), 2000); }}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="sql-code">{sql}</pre>
    </div>
  );
}

/* ################################################################
   Data Table
   ################################################################ */

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows?.length) return null;
  const keys = Object.keys(rows[0]);
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>{keys.map((k) => <th key={k}>{k.replace(/_/g, " ")}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 50).map((row, i) => (
            <tr key={i}>
              {keys.map((k) => {
                let v = row[k];
                if (typeof v === "number") v = formatNumber(v);
                return <td key={k}>{String(v ?? "")}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ################################################################
   Confidence Panel
   ################################################################ */

function ConfidencePanel({
  score,
  tier,
  charts,
  rawData,
}: {
  score: number;
  tier: string;
  charts: ChartPanel[];
  rawData: Record<string, unknown>[] | null;
}) {
  const color =
    tier === "green" ? "var(--accent-green)" : tier === "amber" ? "var(--accent-amber)" : "var(--accent-red)";
  const label = tier === "green" ? "HIGH" : tier === "amber" ? "MEDIUM" : "LOW";
  const chartCount = charts.length || 1;
  const totalRows = charts.reduce((s, c) => s + (c.row_count || 0), 0) || rawData?.length || 0;

  return (
    <div className="confidence-panel">
      <div className="confidence-header">
        <span className={`confidence-badge ${tier}`}>
          <span className={`confidence-dot ${tier}`} />
          {label}
        </span>
        <span className="confidence-score-big" style={{ color }}>
          {score.toFixed(3)}
        </span>
      </div>
      <div className="confidence-meter">
        <div className="confidence-meter-fill" style={{ width: `${score * 100}%`, background: color }} />
      </div>
      <div className="signal-row">
        <span className="signal-label">Sub-queries</span>
        <span className="signal-value">{chartCount}</span>
      </div>
      <div className="signal-row">
        <span className="signal-label">Total Rows</span>
        <span className="signal-value">{totalRows}</span>
      </div>
    </div>
  );
}

/* ################################################################
   Utility Functions
   ################################################################ */



function formatNumber(n: number | unknown): string {
  if (typeof n !== "number") return String(n);
  if (Math.abs(n) > 1000)
    return "£" + n.toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n % 1 !== 0) return n.toFixed(2);
  return n.toLocaleString();
}
