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
import dynamic from 'next/dynamic';

// Dynamic import for Plotly (heavy bundle — only loaded when E2B charts are present)
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false, loading: () => (
  <div className="flex items-center justify-center h-[300px] bg-surface-container-low rounded-2xl">
    <div className="flex flex-col items-center gap-3">
      <span className="material-symbols-outlined text-3xl text-primary animate-pulse">insights</span>
      <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">Loading Interactive Chart...</span>
    </div>
  </div>
)});
import { 
  Zap, 
  BarChart2, 
  FileText, 
  Cloud, 
  Globe, 
  Sparkles, 
  Clock, 
  Bot, 
  BookOpen, 
  Database, 
  User, 
  Activity, 
  Type, 
  Code, 
  Shield, 
  ChevronDown, 
  ChevronUp,
  ChevronRight,
  Send,
  Check,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Workflow,
  HelpCircle,
  ShieldCheck,
} from "lucide-react";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";

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
  status?: "running" | "success" | "error" | "recovering" | "suggestion";
  latency_ms?: number | null;
  highlight?: boolean;
  metadata?: {
    sql?: string;
    row_count?: number;
    confidence?: number;
    search_query?: string;
    document_count?: number;
    python_code?: string;
    error_message?: string;
    record_count?: number;
    top_score?: number;
    [key: string]: unknown;
  };
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
    python_code?: string;
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
  suggested_followups?: string[];
  rag_documents?: RagDoc[];
  web_results?: WebResult[];
  salesforce_records?: SFRecord[];
  jargon_substitutions?: JargonSub[];
  confidence_score?: number;
  confidence_tier?: string;
  processing_time_ms?: number;
  e2b_plotly_json?: string;
  e2b_chart_image?: string;
  security_context?: {
    role: string;
    region_filter: string | null;
    label: string;
    restricted_tables: string[];
  };
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

interface SavedSession {
  id: string;
  title: string;
  messages: ChatMsg[];
  panelData: AnswerPayload | null;
  createdAt: number;
}

/* ################################################################
   Main Page Component
   ################################################################ */

export default function OmniDataPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => "session-" + Date.now());
  const [health, setHealth] = useState<string>("connecting");
  const [healthServices, setHealthServices] = useState<Record<string,string>>({});
  const [panelData, setPanelData] = useState<AnswerPayload | null>(null);
  const [savedSessions, setSavedSessions] = useState<SavedSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState(() => "session-" + Date.now());
  const [activeView, setActiveView] = useState<"chat" | "glossary" | "jargon" | "upload">("chat");
  const [activeRole, setActiveRole] = useState<"ceo" | "north_manager" | "south_manager">(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("omnidata_user");
        if (stored) {
          const u = JSON.parse(stored);
          if (u.role === "north_manager" || u.role === "south_manager") return u.role;
        }
      } catch {}
    }
    return "ceo";
  });
  const [userLabel, setUserLabel] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("omnidata_user");
        if (stored) return JSON.parse(stored).label || "CEO";
      } catch {}
    }
    return "CEO";
  });
  const [userEmail, setUserEmail] = useState(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem("omnidata_user");
        if (stored) return JSON.parse(stored).email || "";
      } catch {}
    }
    return "";
  });
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  const ROLE_CONFIG = {
    ceo: { label: "CEO", icon: "verified_user", color: "#c5a000", badge: "Full Access", region: null },
    north_manager: { label: "North Manager", icon: "shield_person", color: "#4488cc", badge: "North Only", region: "North" },
    south_manager: { label: "South Manager", icon: "shield_person", color: "#426565", badge: "South Only", region: "South" },
  };

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
            session_id: sessionId,
            message: query,
            clarification_answer: clarificationAnswer,
            user_role: activeRole,
            conversation_history: messages
              .filter(m => m.role === "user" || (m.role === "bot" && m.content))
              .slice(-6)
              .map(m => ({
                role: m.role === "user" ? "user" : "assistant",
                content: m.role === "user" ? m.content : (m.content || "").slice(0, 200),
              })),
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
                        const newEntry: TraceEntry = {
                          node: data.node,
                          detail: data.detail,
                          status: data.status || "running",
                          latency_ms: data.latency_ms ?? null,
                          metadata: data.metadata ?? undefined,
                        };
                        return { ...msg, streamingTrace: [...(msg.streamingTrace || []), newEntry] };
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
    [loading, sessionId]
  );

  const askSuggested = (text: string) => {
    setInput("");
    sendQuery(text);
  };

  const lastMessage = messages[messages.length - 1];
  const latestFollowUps = !loading && lastMessage?.role === "bot" && lastMessage.answer?.suggested_followups
    ? lastMessage.answer.suggested_followups
    : [];

  return (
    <div className="text-on-surface bg-surface overflow-hidden h-screen flex flex-col fade-slide-in">
      {/* TopNavBar */}
      <nav className="fixed top-0 w-full z-50 bg-surface/70 dark:bg-[#2d3435]/70 backdrop-blur-xl flex justify-between items-center px-8 h-16 border-b border-outline-variant/10">
        <div className="flex items-center gap-8">
          <span className="text-xl font-bold tracking-tighter text-primary dark:text-[#c3eaea] font-headline">OmniData</span>
          <div className="hidden md:flex items-center gap-6 font-headline text-sm tracking-tight">
            <button className={`transition-colors font-medium ${activeView === 'chat' ? 'text-primary font-bold border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`} onClick={() => setActiveView('chat')}>Chat</button>
            <button className={`transition-colors font-medium ${activeView === 'glossary' ? 'text-primary font-bold border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`} onClick={() => setActiveView('glossary')}>Glossary</button>
            <button className={`transition-colors font-medium ${activeView === 'jargon' ? 'text-primary font-bold border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`} onClick={() => setActiveView('jargon')}>Language</button>
            <button className={`transition-colors font-medium ${activeView === 'upload' ? 'text-primary font-bold border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`} onClick={() => setActiveView('upload')}>Upload</button>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* RBAC Identity Badge (read-only, set at login) */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm"
            style={{ borderLeft: `3px solid ${ROLE_CONFIG[activeRole].color}` }}
          >
            <span className="material-symbols-outlined text-base" style={{ color: ROLE_CONFIG[activeRole].color }}>{ROLE_CONFIG[activeRole].icon}</span>
            <span className="font-semibold text-on-surface hidden lg:inline">{ROLE_CONFIG[activeRole].label}</span>
            <span className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded" style={{ background: `${ROLE_CONFIG[activeRole].color}20`, color: ROLE_CONFIG[activeRole].color }}>{ROLE_CONFIG[activeRole].badge}</span>
          </div>

          <div className="w-px h-6 bg-outline-variant/20" />

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              className="h-8 w-8 rounded-full overflow-hidden bg-primary-container hover:ring-2 hover:ring-primary/30 transition-all cursor-pointer"
            >
              <img alt="User profile" className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAcY87chJy7yW6tRTn7eQQbM5-aWfpDkZwRMSWLPBWEhLEtzIOjo65s6liGKIagJN2tpM6--MN5j_R_dA1Rir7WfnBo4VX93RBI3SoqzLyJBpFhP4JM1wSmo9jSPiirOJGAc2c_EpycFKNoq53_f1XDdJv_LcM9itNnESP1JIeEZnzaJXBQ-QQqqLRtIj1o16o5FuTWZ6qAF63nJl61AFxHD6sTayLeQNMoxiXlNPTAjJJ-sZGBz_3jTpbLP0lLjKCaMFj0XCUpV6I"/>
            </button>
            {showRoleMenu && (
              <div className="absolute right-0 top-full mt-2 w-64 bg-surface-container-lowest rounded-xl shadow-2xl border border-outline-variant/10 py-2 z-[100]">
                <div className="px-4 py-3 border-b border-outline-variant/10">
                  <div className="text-xs font-bold text-on-surface">{userLabel}</div>
                  <div className="text-[10px] text-on-surface-variant font-mono mt-0.5">{userEmail || "ceo@auraretail.co.uk"}</div>
                  <div className="mt-2 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-xs" style={{ color: ROLE_CONFIG[activeRole].color }}>{ROLE_CONFIG[activeRole].icon}</span>
                    <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: ROLE_CONFIG[activeRole].color }}>
                      {ROLE_CONFIG[activeRole].region ? `${ROLE_CONFIG[activeRole].region} Region Access` : "Unrestricted Access"}
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    localStorage.removeItem("omnidata_user");
                    window.location.href = "/login";
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/8 transition-colors"
                >
                  <span className="material-symbols-outlined text-base">logout</span>
                  <span className="font-semibold">Sign Out</span>
                </button>
                <button
                  onClick={() => {
                    localStorage.removeItem("omnidata_user");
                    window.location.href = "/login";
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-[10px] text-on-surface-variant hover:bg-surface-container transition-colors"
                >
                  <span className="material-symbols-outlined text-xs">swap_horiz</span>
                  <span className="font-semibold">Switch Account</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      <main className="flex flex-1 pt-16 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar
          onNewSession={() => {
            setActiveView('chat');
            if (messages.length > 0) {
              const firstUserMsg = messages.find(m => m.role === "user");
              const title = firstUserMsg
                ? firstUserMsg.content.slice(0, 35) + (firstUserMsg.content.length > 35 ? "..." : "")
                : "Untitled Chat";
              setSavedSessions(prev => {
                const alreadySaved = prev.find(s => s.id === sessionId);
                if (alreadySaved) {
                  return prev.map(s => s.id === sessionId
                    ? { ...s, messages: [...messages], panelData }
                    : s
                  );
                }
                return [{ id: sessionId, title, messages: [...messages], panelData, createdAt: Date.now() }, ...prev];
              });
            }
            const newId = "session-" + Date.now();
            setMessages([]);
            setPanelData(null);
            setInput("");
            setSessionId(newId);
            setActiveSessionId(newId);
          }}
          onRestoreSession={(session: SavedSession) => {
            setActiveView('chat');
            if (messages.length > 0 && sessionId !== session.id) {
              const firstUserMsg = messages.find(m => m.role === "user");
              const title = firstUserMsg
                ? firstUserMsg.content.slice(0, 35) + (firstUserMsg.content.length > 35 ? "..." : "")
                : "Untitled Chat";
              setSavedSessions(prev => {
                const exists = prev.find(s => s.id === sessionId);
                if (exists) return prev;
                return [{ id: sessionId, title, messages: [...messages], panelData, createdAt: Date.now() }, ...prev];
              });
            }
            setMessages(session.messages);
            setPanelData(session.panelData);
            setSessionId(session.id);
            setActiveSessionId(session.id);
          }}
          savedSessions={savedSessions}
          activeSessionId={activeSessionId}
          healthServices={healthServices}
          activeView={activeView}
          onViewChange={setActiveView}
        />

        {/* Main Content — view-switched */}
        {activeView === 'chat' && (
          <>
            <section className="flex-1 flex flex-col relative bg-surface min-w-0">
              <div className="flex-1 overflow-y-auto px-4 md:px-8 pt-10 pb-64 hide-scrollbar max-w-3xl mx-auto w-full space-y-10" ref={chatRef}>
                {messages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center fade-slide-in pb-10">
                    <div className="w-16 h-16 rounded-2xl bg-primary-container flex items-center justify-center text-primary mb-6"><Zap size={32} /></div>
                    <h1 className="text-3xl font-headline font-extrabold text-on-surface mb-3">Ask anything about <span className="text-primary uppercase">your data</span></h1>
                    <p className="text-on-surface-variant font-medium max-w-md mx-auto mb-8">
                      Query sales data, internal policies, market intelligence, and more.
                    </p>
                    <div className="flex flex-wrap gap-3 justify-center max-w-2xl">
                      {[
                        "Revenue excluding partner discounts?",
                        "Which product had the highest return rate?",
                        "Compare churn across all regions",
                        "AuraSound Pro sales trend",
                        "Summarise the February trading update",
                      ].map((q) => (
                        <button key={q} className="bg-surface-container-low hover:bg-surface-container text-on-surface text-sm font-medium px-4 py-2 rounded-xl transition-all shadow-sm border border-outline-variant/10" onClick={() => askSuggested(q)}>
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
                    onSuggest={setInput}
                  />
                ))}
              </div>

              {/* Floating Input Dock */}
              <div className="absolute bottom-0 left-0 w-full z-10 transition-all pt-16 pb-6 px-4 md:pb-8 pointer-events-none flex flex-col gap-3">
                {latestFollowUps.length > 0 && (
                  <div className="max-w-3xl mx-auto w-full pointer-events-auto flex gap-2 overflow-x-auto hide-scrollbar pb-2 px-1">
                    {latestFollowUps.map((followUp, idx) => (
                      <button
                        key={idx}
                        onClick={() => askSuggested(followUp)}
                        className="whitespace-nowrap flex-shrink-0 text-sm py-2 px-4 bg-surface hover:bg-primary-container hover:text-on-primary-container border border-outline-variant/30 text-on-surface-variant font-medium rounded-full shadow-sm transition-colors"
                      >
                        {followUp}
                      </button>
                    ))}
                  </div>
                )}
                <div className="max-w-3xl mx-auto w-full relative group pointer-events-auto">
                  <input
                    className="w-full bg-surface border border-outline-variant/20 shadow-[0_8px_30px_rgba(0,0,0,0.12)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.4)] rounded-full px-7 py-4 pr-16 focus:ring-4 focus:ring-primary/20 text-on-surface placeholder:text-outline-variant/80 transition-all font-medium text-base hover:shadow-[0_12px_40px_rgba(0,0,0,0.18)] dark:hover:shadow-[0_12px_40px_rgba(0,0,0,0.6)]"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about sales, churn, products..."
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendQuery(input);
                      }
                    }}
                  />
                  <button
                    className="absolute right-2 top-1/2 -translate-y-1/2 h-[42px] w-[42px] rounded-full bg-primary text-on-primary flex items-center justify-center transition-transform hover:scale-[1.05] active:scale-95 disabled:opacity-50 disabled:hover:scale-100 shadow-md"
                    disabled={!input.trim() || loading}
                    onClick={() => sendQuery(input)}
                  >
                    <span className="material-symbols-outlined text-lg">arrow_upward</span>
                  </button>
                </div>
                <p className="max-w-3xl mx-auto text-center text-[10px] text-outline-variant mt-4 uppercase tracking-widest font-bold">OmniData can make mistakes. Verify important metrics.</p>
              </div>
            </section>
            <RightPanel data={panelData} />
          </>
        )}
        {activeView === 'glossary' && <GlossaryPage />}
        {activeView === 'jargon' && <JargonPage />}
        {activeView === 'upload' && <UploadPage />}
      </main>
    </div>
  );
}

/* ################################################################
   Sidebar
   ################################################################ */

function Sidebar({ 
  onNewSession, 
  onRestoreSession,
  savedSessions,
  activeSessionId,
  healthServices,
  activeView,
  onViewChange,
}: { 
  onNewSession: () => void;
  onRestoreSession: (session: SavedSession) => void;
  savedSessions: SavedSession[];
  activeSessionId: string;
  healthServices: Record<string, string>;
  activeView: string;
  onViewChange: (view: "chat" | "glossary" | "jargon" | "upload") => void;
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <aside className={`transition-all duration-300 flex-shrink-0 bg-surface-container flex flex-col pt-6 pb-8 border-r border-outline-variant/15 relative ${isCollapsed ? 'w-20' : 'w-64'}`}>
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-20 bg-surface border border-outline-variant/20 rounded-full p-1 z-10 hover:bg-surface-container shadow-sm flex items-center justify-center text-outline transition-transform hover:scale-110 active:scale-95"
      >
        <span className="material-symbols-outlined text-[14px]">{isCollapsed ? 'chevron_right' : 'chevron_left'}</span>
      </button>

      <div className={`mb-6 transition-all ${isCollapsed ? 'px-3' : 'px-6'}`}>
        <button onClick={onNewSession} className={`w-full py-3 ${isCollapsed ? 'px-0 justify-center' : 'px-4 justify-center'} rounded-xl bg-gradient-to-r from-primary to-primary-dim text-on-primary font-semibold flex items-center gap-2 shadow-lg shadow-primary/10 transition-transform active:scale-95 duration-300 hover:scale-[1.02]`}>
          <span className="material-symbols-outlined text-sm">add</span>
          {!isCollapsed && <span className="text-sm">New Query</span>}
        </button>
      </div>

      {/* Saved Sessions List */}
      <div className="flex-1 overflow-y-auto hide-scrollbar px-3">
        {!isCollapsed && (
          <div className="px-3 mb-2 transition-opacity duration-200">
            <p className="text-[10px] font-bold uppercase tracking-widest text-outline">Chat History</p>
          </div>
        )}
        {savedSessions.length === 0 ? (
          <div className="px-3 py-4 text-center">
            <span className="material-symbols-outlined text-2xl text-outline-variant/40 block mb-1">forum</span>
            {!isCollapsed && <p className="text-[11px] text-outline-variant/60 font-medium whitespace-nowrap">No saved chats</p>}
          </div>
        ) : (
          <div className="space-y-1">
            {savedSessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const msgCount = session.messages.filter(m => m.role === "user").length;
              const timeAgo = _formatTimeAgo(session.createdAt);
              return (
                <button
                  key={session.id}
                  onClick={() => onRestoreSession(session)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-all group ${
                    isActive
                      ? "bg-primary-container/40 text-primary border border-primary/15 shadow-sm"
                      : "text-on-surface-variant hover:bg-surface-container-high border border-transparent"
                  }`}
                >
                  <div className={`flex items-start ${isCollapsed ? 'justify-center' : 'gap-2.5'}`}>
                    <span className={`material-symbols-outlined text-[16px] mt-0.5 shrink-0 ${isActive ? "text-primary" : "text-outline-variant"}`}
                      style={{fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0"}}
                    >chat_bubble</span>
                    {!isCollapsed && (
                      <div className="min-w-0 flex-1">
                        <p className={`text-[13px] font-medium truncate ${isActive ? "text-primary" : ""}`}>
                          {session.title}
                        </p>
                        <p className="text-[10px] text-outline-variant mt-0.5">
                          {msgCount} {msgCount === 1 ? "message" : "messages"} · {timeAgo}
                        </p>
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Nav Links */}
        {!isCollapsed && (
          <div className="px-3 mt-6 mb-2 transition-opacity duration-200">
            <p className="text-[10px] font-bold uppercase tracking-widest text-outline">Tools</p>
          </div>
        )}
        <div className={isCollapsed ? "mt-6 space-y-2 flex flex-col items-center" : "space-y-1"}>
          <button onClick={() => onViewChange('glossary')} title="Metrics Glossary" className={`w-full flex items-center ${isCollapsed ? 'justify-center w-10 h-10 px-0' : 'px-3 py-2.5 gap-3'} rounded-lg transition-all ${activeView === 'glossary' ? 'bg-primary-container/40 text-primary font-semibold' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>
            <span className="material-symbols-outlined">book</span>
            {!isCollapsed && <span className="text-sm whitespace-nowrap">Metrics Glossary</span>}
          </button>
          <button onClick={() => onViewChange('jargon')} title="Language Rules" className={`w-full flex items-center ${isCollapsed ? 'justify-center w-10 h-10 px-0' : 'px-3 py-2.5 gap-3'} rounded-lg transition-all ${activeView === 'jargon' ? 'bg-primary-container/40 text-primary font-semibold' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>
            <span className="material-symbols-outlined">translate</span>
            {!isCollapsed && <span className="text-sm whitespace-nowrap">Language Rules</span>}
          </button>
          <button onClick={() => onViewChange('chat')} title="AI Chat" className={`w-full flex items-center ${isCollapsed ? 'justify-center w-10 h-10 px-0' : 'px-3 py-2.5 gap-3'} rounded-lg transition-all ${activeView === 'chat' ? 'bg-primary-container/40 text-primary font-semibold' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>
            <span className="material-symbols-outlined">chat</span>
            {!isCollapsed && <span className="text-sm whitespace-nowrap">AI Chat</span>}
          </button>
          <button onClick={() => onViewChange('upload')} title="Upload Document" className={`w-full flex items-center ${isCollapsed ? 'justify-center w-10 h-10 px-0' : 'px-3 py-2.5 gap-3'} rounded-lg transition-all ${activeView === 'upload' ? 'bg-primary-container/40 text-primary font-semibold' : 'text-on-surface-variant hover:bg-surface-container-high'}`}>
            <span className="material-symbols-outlined">upload_file</span>
            {!isCollapsed && <span className="text-sm whitespace-nowrap">Upload Doc</span>}
          </button>
        </div>
      </div>

      <div className={`px-6 pt-6 border-t border-outline-variant/10 ${isCollapsed ? 'px-2 items-center flex flex-col' : ''}`}>
        {!isCollapsed ? (
          <div className="mb-4 transition-opacity duration-200">
            <div className="text-[10px] font-bold uppercase tracking-widest text-outline mb-2">System Status</div>
            <div className="flex flex-col gap-2">
              <StatusItem label="Snowflake DWH" status={healthServices.snowflake || 'live'} icon="database" />
              <StatusItem label="Salesforce CRM" status={healthServices.salesforce || 'syncing'} icon="cloud" />
              <StatusItem label="Tavily Search" status="live" icon="travel_explore" />
              <StatusItem label="Confluence Doc" status="live" icon="feed" />
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3 mb-4">
            <StatusIconOnly status={healthServices.snowflake || 'live'} icon="database" title="Snowflake DWH" />
            <StatusIconOnly status={healthServices.salesforce || 'syncing'} icon="cloud" title="Salesforce CRM" />
            <StatusIconOnly status="live" icon="travel_explore" title="Tavily Search" />
            <StatusIconOnly status="live" icon="feed" title="Confluence Doc" />
          </div>
        )}
        {!isCollapsed && (
          <div className="bg-primary-container/30 p-4 rounded-xl border border-primary-container/50 transition-opacity duration-200">
            <p className="text-xs font-bold text-primary mb-1 flex items-center gap-1"><span className="material-symbols-outlined text-sm">workspace_premium</span> PRO PLAN</p>
            <p className="text-[11px] text-on-primary-container leading-relaxed">Unlock advanced predictive modeling and real-time streams.</p>
          </div>
        )}
      </div>
    </aside>
  );
}

function _formatTimeAgo(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function StatusItem({ label, status, icon }: { label: string; status?: string; icon: string | React.ReactNode }) {
  const isLive = status === "live" || (status && status.startsWith("ok"));
  const isSyncing = status === "syncing" || status === "connecting";
  
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-surface-container-lowest border border-outline-variant/10 shadow-sm">
      <div className="flex items-center gap-2">
        {typeof icon === "string" ? (
          <span className="material-symbols-outlined text-[16px] text-tertiary">{icon}</span>
        ) : (
          <span className="text-tertiary flex items-center">{icon}</span>
        )}
        <span className="text-xs font-semibold text-on-surface-variant">{label}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className={`w-2 h-2 rounded-full ${(isLive || isSyncing) ? 'bg-secondary animate-pulse' : 'bg-red-500'}`}></div>
        <span className="text-[10px] font-bold uppercase text-outline tracking-wider">{isLive ? 'Live' : isSyncing ? 'Sync' : 'Err'}</span>
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
  onSuggest,
}: {
  msg: ChatMsg;
  onClarify: (oq: string, cv: string) => void;
  onSuggest?: (q: string) => void;
}) {
  const [clickedOption, setClickedOption] = useState<string | null>(null);

  if (msg.role === "user") {
    return (
      <div className="flex flex-col items-end w-full fade-slide-in">
        <div className="bg-primary/5 border border-primary/10 rounded-[2rem] rounded-tr-sm px-6 py-4 max-w-[85%] text-on-surface shadow-sm">
          <p className="text-[15px] leading-relaxed font-medium">{msg.content}</p>
        </div>
      </div>
    );
  }

  if (msg.role === "clarification") {
    return (
      <div className="flex gap-4 w-full fade-slide-in">
        <div className="h-8 w-8 rounded-lg bg-tertiary flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-on-tertiary text-sm">help</span>
        </div>
        <div className="flex-1 space-y-4">
          <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/20 shadow-sm w-full max-w-2xl">
            <h4 className="text-on-surface font-semibold mb-2">⚡ Which metric did you mean?</h4>
            <p className="text-on-surface-variant text-sm mb-4">{msg.content}</p>
            <div className="flex flex-col gap-2 relative z-20">
              {(msg.clarificationOptions as string[] || []).map((opt) => (
                <button
                  key={String(opt)}
                  disabled={clickedOption !== null}
                  className={`w-full text-left py-3 px-4 rounded-xl font-medium text-sm transition-colors border cursor-pointer pointer-events-auto 
                    ${clickedOption === String(opt) 
                      ? 'bg-primary/10 border-primary/30 text-primary' 
                      : clickedOption !== null 
                        ? 'bg-surface-container border-outline-variant/5 text-on-surface-variant/40 cursor-not-allowed opacity-50' 
                        : 'bg-surface-container-lowest hover:bg-surface-container border-outline-variant/10 text-primary'}`}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (clickedOption === null) {
                      setClickedOption(String(opt));
                      onClarify(msg.originalQuery || "", String(opt));
                    }
                  }}
                >
                  {String(opt)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const a = msg.answer;
  const tier = a?.confidence_tier || "green";
  const score = a?.confidence_score || 0;
  const timeStr = a?.processing_time_ms ? `${(a.processing_time_ms / 1000).toFixed(1)}s` : "";
  const tierColor = tier === "green" ? "text-secondary" : tier === "amber" ? "text-orange-500" : "text-red-500";
  const tierBg = tier === "green" ? "bg-secondary-container" : tier === "amber" ? "bg-orange-100" : "bg-red-100";

  return (
    <div className="flex gap-4 w-full fade-slide-in">
      <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0 shadow-md shadow-primary/20">
        <span className="material-symbols-outlined text-on-primary text-sm" style={{fontVariationSettings: "'FILL' 1"}}>bubble_chart</span>
      </div>
      <div className="flex-1 space-y-3 min-w-0">
        <div className="flex flex-col md:flex-row md:items-center gap-2 mb-1">
          <span className="text-sm font-bold text-on-surface">OmniData AI</span>
          <div className="flex flex-wrap gap-2">
            {a?.sources?.map((s, i) => (
              <span key={i} className="flex items-center gap-1 bg-surface-container-high px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest text-on-surface-variant">
                <span className="material-symbols-outlined text-[10px]">database</span>
                {s.label}
              </span>
            ))}
            {a?.confidence_score && (
              <span className={`flex items-center gap-1 ${tierBg} px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest ${tierColor}`}>
                <span className="material-symbols-outlined text-[10px]">shield</span>
                {Math.round(score * 100)}% Confidence
              </span>
            )}
            {timeStr && (
              <span className="flex items-center gap-1 bg-surface-container-high px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest text-on-surface-variant">
                {timeStr}
              </span>
            )}
            {a?.date_resolution && (
              <span className="flex items-center gap-1 bg-surface-container-high px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-widest text-on-surface-variant">
                {a.date_resolution}
              </span>
            )}
          </div>
        </div>

        {/* Chain of Thought Audit Trail */}
        {(a?.trace || msg.streamingTrace) && (
          <ChainOfThoughtTrace trace={a?.trace || msg.streamingTrace || []} isComplete={!!a} onSuggest={onSuggest} />
        )}

        <div className="w-full">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({node, ...props}) => <p className="text-[15px] leading-relaxed text-on-surface-variant font-medium mb-4 last:mb-0" {...props} />,
              h1: ({node, ...props}) => <h1 className="text-2xl font-headline font-extrabold tracking-tight text-on-surface mt-6 mb-3" {...props} />,
              h2: ({node, ...props}) => <h2 className="text-xl font-headline font-bold tracking-tight text-on-surface mt-5 mb-2" {...props} />,
              h3: ({node, ...props}) => <h3 className="text-lg font-headline font-semibold text-on-surface mt-4 mb-2" {...props} />,
              h4: ({node, ...props}) => <h4 className="text-base font-headline font-semibold text-on-surface mt-3 mb-2" {...props} />,
              ul: ({node, ...props}) => <ul className="flex flex-col gap-2 my-4 pl-0" {...props} />,
              ol: ({node, ...props}) => <ol className="list-decimal list-outside ml-5 my-4 space-y-2 text-on-surface-variant text-[15px]" {...props} />,
              li: ({node, ...props}) => (
                <li className="flex items-start gap-2.5 text-[15px] leading-relaxed text-on-surface-variant font-medium">
                  {(node as any)?.parent?.tagName === 'ul' && <span className="material-symbols-outlined text-[14px] text-primary mt-1 shrink-0" style={{fontVariationSettings: "'FILL' 1"}}>check_circle</span>}
                  <span className="flex-1 max-w-full"><span {...props} /></span>
                </li>
              ),
              strong: ({node, ...props}) => <strong className="font-bold text-on-surface" {...props} />,
              blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-primary/40 pl-4 py-1 my-4 bg-primary/5 rounded-r-lg italic text-on-surface-variant" {...props} />,
              code: ({node, className, children, ...props}: any) => {
                const match = /language-(\w+)/.exec(className || '');
                const isInline = !match && !className?.includes('language-');
                return isInline ? (
                  <code className="px-1.5 py-0.5 rounded-md bg-surface-container-high border border-outline-variant/20 text-primary text-sm font-mono tracking-tight" {...props}>{children}</code>
                ) : (
                  <div className="rounded-xl overflow-hidden border border-outline-variant/15 shadow-sm bg-slate-900 my-4 transform transition-all hover:shadow-md">
                    <div className="flex justify-between items-center px-4 py-2 border-b border-white/10 bg-slate-800/80 backdrop-blur-md">
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-400">{match?.[1] || 'code'}</span>
                    </div>
                    <div className="p-4 overflow-x-auto">
                      <pre className="text-sm font-mono text-slate-300 leading-relaxed"><code {...props}>{children}</code></pre>
                    </div>
                  </div>
                );
              }
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

/* ################################################################
   Chain of Thought — Node metadata maps
   ################################################################ */

const NODE_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  intent_router:      { label: "Intent Classification",   icon: <Workflow size={13} />,    color: "text-violet-400" },
  clarification:      { label: "Query Disambiguation",    icon: <HelpCircle size={13} />,  color: "text-amber-400" },
  branch_sql:         { label: "Snowflake Query",         icon: <Database size={13} />,    color: "text-blue-400" },
  branch_rag:         { label: "Knowledge Search",        icon: <BookOpen size={13} />,    color: "text-emerald-400" },
  branch_salesforce:  { label: "CRM Lookup",              icon: <Cloud size={13} />,       color: "text-sky-400" },
  branch_soql:        { label: "CRM Lookup",              icon: <Cloud size={13} />,       color: "text-sky-400" },
  branch_web:         { label: "Web Intelligence",        icon: <Globe size={13} />,       color: "text-pink-400" },
  e2b_sandbox:        { label: "Data Visualisation",      icon: <BarChart2 size={13} />,   color: "text-orange-400" },
  synthesis:          { label: "Answer Synthesis",        icon: <Sparkles size={13} />,    color: "text-primary" },
  synthesis_node:     { label: "Answer Synthesis",        icon: <Sparkles size={13} />,    color: "text-primary" },
  semantic_validator: { label: "Jargon Audit",            icon: <ShieldCheck size={13} />, color: "text-teal-400" },
  temporal_resolver:  { label: "Date Resolution",         icon: <Clock size={13} />,       color: "text-indigo-400" },
  metric_resolver:    { label: "Metric Resolution",       icon: <Activity size={13} />,    color: "text-rose-400" },
  reasoning:          { label: "AI Reasoning",            icon: <span className="text-[13px]">🧠</span>, color: "text-fuchsia-400" },
  recovery:           { label: "Smart Recovery",          icon: <RefreshCw size={13} />,    color: "text-amber-400" },
  security_context:   { label: "Security Context",        icon: <Shield size={13} />,       color: "text-yellow-500" },
};

function getNodeMeta(node: string) {
  return NODE_META[node] ?? { label: node.replace(/_/g, " "), icon: <Bot size={13} />, color: "text-outline-variant" };
}

/* ################################################################
   Chain of Thought — Individual Step
   ################################################################ */

function ChainOfThoughtStep({ step, index, isActive, onSuggest }: { step: TraceEntry; index: number; isActive: boolean; onSuggest?: (q: string) => void }) {
  const [open, setOpen] = useState(false);
  const meta = getNodeMeta(step.node);
  const hasMetadata = step.metadata && Object.keys(step.metadata).length > 0;
  const status = step.status ?? (isActive ? "running" : "success");

  const statusIcon = () => {
    if (status === "running") return <Loader2 size={14} className="animate-spin text-primary" />;
    if (status === "error")   return <AlertTriangle size={14} className="text-red-400" />;
    if (status === "recovering") return <RefreshCw size={14} className="text-amber-400 animate-spin" />;
    return <Check size={14} className="text-emerald-400" />;
  };

  const statusColor = () => {
    if (status === "running")    return "border-primary/40 bg-primary/5";
    if (status === "error")      return "border-red-500/30 bg-red-500/5";
    if (status === "recovering") return "border-amber-500/30 bg-amber-500/5";
    return "border-outline-variant/15 bg-surface-container-lowest/60";
  };

  // Recovery / suggestion node renders as an amber action card
  if (step.node === "recovery" || step.status === "suggestion") {
    const suggestion = step.metadata?.suggestion as string | undefined;
    return (
      <div className="fade-slide-in" style={{ animationDelay: `${index * 60}ms` }}>
        <div className="flex items-start gap-3 px-3 py-2.5 rounded-xl border border-amber-500/30 bg-amber-500/5">
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
            <RefreshCw size={14} className="text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400 block mb-1">Recovering</span>
            <p className="text-[12px] text-on-surface-variant font-medium leading-relaxed">{step.detail}</p>
            {suggestion && onSuggest && (
              <button
                onClick={() => onSuggest(suggestion)}
                className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-amber-400 hover:text-amber-300 transition-colors group"
              >
                <span className="underline underline-offset-2">{suggestion}</span>
                <ChevronRight size={11} className="group-hover:translate-x-0.5 transition-transform" />
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="fade-slide-in" style={{ animationDelay: `${index * 60}ms` }}>
      <Collapsible open={open} onOpenChange={hasMetadata ? setOpen : undefined}>
        <CollapsibleTrigger
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all duration-200 text-left
            ${statusColor()}
            ${hasMetadata ? "cursor-pointer hover:border-primary/30 hover:bg-primary/5" : "cursor-default"}
          `}
        >
            {/* Status icon */}
            <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
              {statusIcon()}
            </div>

            {/* Node icon + label */}
            <div className={`flex items-center gap-1.5 flex-shrink-0 ${meta.color}`}>
              {meta.icon}
              <span className="text-[11px] font-bold uppercase tracking-wider whitespace-nowrap">{meta.label}</span>
            </div>

            {/* Divider */}
            <div className="w-px h-3 bg-outline-variant/30 flex-shrink-0" />

            {/* Detail text */}
            <span className="text-[12px] text-on-surface-variant flex-1 truncate font-medium">{step.detail}</span>

            {/* Right side: latency + expand hint */}
            <div className="flex items-center gap-2 flex-shrink-0 ml-2">
              {step.latency_ms != null && (
                <Badge
                  className="text-[10px] px-1.5 py-0 font-mono border-outline-variant/20 bg-surface-container text-outline"
                  variant="outline"
                >
                  {step.latency_ms < 1000
                    ? `${step.latency_ms}ms`
                    : `${(step.latency_ms / 1000).toFixed(1)}s`}
                </Badge>
              )}
              {hasMetadata && (
                <ChevronRight
                  size={13}
                  className={`text-outline-variant/60 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
                />
              )}
            </div>
        </CollapsibleTrigger>

        {hasMetadata && (
          <CollapsibleContent className="overflow-hidden data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2">
            <div className="mx-1 mt-1 mb-1 rounded-xl border border-outline-variant/15 bg-surface-container overflow-hidden">
              {step.metadata?.sql && (
                <div>
                  <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1">
                    <Code size={11} className="text-blue-400" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">SQL</span>
                  </div>
                  <pre className="px-3 pb-3 text-[11px] font-mono text-emerald-300/90 whitespace-pre-wrap break-all leading-relaxed bg-transparent overflow-x-auto">
                    {step.metadata.sql}
                  </pre>
                </div>
              )}
              {step.metadata?.python_code && (
                <div>
                  <div className="flex items-center gap-1.5 px-3 pt-2.5 pb-1">
                    <Code size={11} className="text-orange-400" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-orange-400">Python</span>
                  </div>
                  <pre className="px-3 pb-3 text-[11px] font-mono text-orange-300/90 whitespace-pre-wrap break-all leading-relaxed overflow-x-auto">
                    {step.metadata.python_code}
                  </pre>
                </div>
              )}
              {step.metadata?.search_query && (
                <div className="flex items-center gap-2 px-3 py-2.5">
                  <Globe size={11} className="text-pink-400 flex-shrink-0" />
                  <span className="text-[11px] text-on-surface-variant font-mono">"{step.metadata.search_query}"</span>
                </div>
              )}
              {step.metadata?.error_message && (
                <div className="flex items-start gap-2 px-3 py-2.5">
                  <AlertTriangle size={11} className="text-red-400 flex-shrink-0 mt-0.5" />
                  <span className="text-[11px] text-red-300/90 font-mono leading-relaxed">{step.metadata.error_message}</span>
                </div>
              )}
              <div className="flex flex-wrap gap-3 px-3 py-2 border-t border-outline-variant/10">
                {step.metadata?.row_count != null && (
                  <span className="text-[10px] text-outline font-medium">{step.metadata.row_count} rows</span>
                )}
                {step.metadata?.record_count != null && (
                  <span className="text-[10px] text-outline font-medium">{step.metadata.record_count} records</span>
                )}
                {step.metadata?.document_count != null && (
                  <span className="text-[10px] text-outline font-medium">{step.metadata.document_count} docs</span>
                )}
                {step.metadata?.confidence != null && (
                  <span className="text-[10px] text-outline font-medium">{Math.round((step.metadata.confidence as number) * 100)}% confidence</span>
                )}
                {step.metadata?.top_score != null && (
                  <span className="text-[10px] text-outline font-medium">top score {(step.metadata.top_score as number).toFixed(2)}</span>
                )}
              </div>
            </div>
          </CollapsibleContent>
        )}
      </Collapsible>
    </div>
  );
}

/* ################################################################
   Chain of Thought — Container
   ################################################################ */

function ChainOfThoughtTrace({ trace, isComplete, onSuggest }: { trace: TraceEntry[]; isComplete: boolean; onSuggest?: (q: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const totalMs = trace.reduce((sum, t) => sum + (t.latency_ms ?? 0), 0);

  // Collapsed pill (after completion)
  if (isComplete && !expanded) {
    const successCount = trace.filter(t => (t.status ?? "success") === "success").length;
    const errorCount = trace.filter(t => t.status === "error").length;
    return (
      <button
        onClick={() => setExpanded(true)}
        className="group flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-surface-container border border-outline-variant/20 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 mb-3 shadow-sm cursor-pointer text-left"
      >
        <span className="material-symbols-outlined text-primary text-[16px]" style={{fontVariationSettings: "'FILL' 1"}}>bolt</span>
        <span className="text-[12px] font-bold text-primary">Actions Trace</span>
        <div className="w-px h-3 bg-outline-variant/30" />
        <span className="text-[11px] text-outline-variant font-medium">{trace.length} steps</span>
        {errorCount > 0 && (
          <Badge className="text-[10px] px-1.5 py-0 border-red-500/30 bg-red-500/10 text-red-400" variant="outline">
            {errorCount} error{errorCount > 1 ? "s" : ""}
          </Badge>
        )}
        {totalMs > 0 && (
          <Badge className="text-[10px] px-1.5 py-0 font-mono border-outline-variant/20 bg-surface-container-high text-outline" variant="outline">
            {(totalMs / 1000).toFixed(1)}s total
          </Badge>
        )}
        <ChevronRight size={13} className="text-outline-variant/60 ml-auto group-hover:text-primary transition-colors" />
      </button>
    );
  }

  return (
    <div className="mb-4 bg-surface-container-low rounded-2xl border border-outline-variant/15 overflow-hidden shadow-sm" style={{ minWidth: 340, maxWidth: 560 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/10">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[16px]" style={{fontVariationSettings: "'FILL' 1"}}>bolt</span>
          <span className="text-[11px] font-bold uppercase tracking-widest text-primary">
            {isComplete ? "Actions Trace" : "Working…"}
          </span>
          {!isComplete && (
            <div className="flex gap-0.5 ml-1">
              {[0,1,2].map(i => (
                <span key={i} className="w-1 h-1 rounded-full bg-primary animate-bounce" style={{animationDelay: `${i * 150}ms`}} />
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isComplete && totalMs > 0 && (
            <Badge className="text-[10px] px-1.5 py-0 font-mono border-outline-variant/20 bg-surface-container text-outline" variant="outline">
              {(totalMs / 1000).toFixed(1)}s
            </Badge>
          )}
          {isComplete && (
            <button
              onClick={() => setExpanded(false)}
              className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-outline-variant hover:text-primary transition-colors"
            >
              <ChevronUp size={13} /> Collapse
            </button>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="p-3 flex flex-col gap-1.5">
        {trace.length === 0 && !isComplete && (
          <div className="flex items-center gap-3 px-3 py-2.5">
            <Loader2 size={14} className="animate-spin text-primary flex-shrink-0" />
            <span className="text-[12px] text-on-surface-variant font-medium">Initializing pipeline…</span>
          </div>
        )}
        {trace.map((step, i) => (
          <ChainOfThoughtStep
            key={`${step.node}-${i}`}
            step={step}
            index={i}
            isActive={!isComplete && i === trace.length - 1}
            onSuggest={onSuggest}
          />
        ))}
      </div>

      {isComplete && (
        <div className="px-4 py-2.5 border-t border-outline-variant/10 flex items-center gap-2">
          <Check size={12} className="text-emerald-400" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400/80">Pipeline complete</span>
          <span className="text-[10px] text-outline ml-auto">{trace.length} nodes executed</span>
        </div>
      )}
    </div>
  );
}


/* ################################################################
   Thinking Dots
   ################################################################ */

function ThinkingDots() {
  return (
    <div className="thinking">
      <div className="thinking-avatar"><Zap size={18} /></div>
      <div className="thinking-dots">
        <div className="thinking-dot" />
        <div className="thinking-dot" />
        <div className="thinking-dot" />
      </div>
    </div>
  );
}

/* ################################################################
   Glossary Page — full-screen metric dictionary browser
   ################################################################ */

interface GlossaryEntry {
  term: string;
  replacement: string;
  source: string;
  editable: boolean;
  category?: string;
}

function GlossaryPage() {
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [syncStatus, setSyncStatus] = useState<{ overrides_count: number; source: string; last_sync: string | null } | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/jargon`).then(r => r.json()).then(d => d.terms || []),
      fetch(`${API_URL}/api/sync-status`).then(r => r.json()).catch(() => null),
    ]).then(([jargon, status]) => {
      setEntries(jargon);
      setSyncStatus(status);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const sources = Array.from(new Set(entries.map(e => e.source)));
  const filtered = entries.filter(e => {
    const matchesSearch = !search || 
      e.term.toLowerCase().includes(search.toLowerCase()) || 
      e.replacement.toLowerCase().includes(search.toLowerCase());
    const matchesSource = sourceFilter === "all" || e.source === sourceFilter;
    return matchesSearch && matchesSource;
  });

  const metricDictEntries = filtered.filter(e => e.source === "metric_dictionary");
  const overrideEntries = filtered.filter(e => e.source !== "metric_dictionary");

  return (
    <section className="flex-1 flex flex-col bg-surface min-w-0 overflow-hidden fade-slide-in">
      <div className="flex-1 overflow-y-auto hide-scrollbar">
        <div className="max-w-5xl mx-auto px-8 py-10">
          {/* Header */}
          <div className="flex items-start justify-between mb-8">
            <div>
              <h1 className="text-3xl font-headline font-extrabold text-on-surface mb-2 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-4xl">book</span>
                Metrics Glossary
              </h1>
              <p className="text-on-surface-variant font-medium max-w-lg">
                A complete catalog of every business metric, column alias, and data source available in OmniData. 
                Sourced from Snowflake column metadata and the curated YAML dictionary.
              </p>
            </div>
            {syncStatus && (
              <div className="flex flex-col items-end gap-1 shrink-0">
                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${syncStatus.source === 'snowflake' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                  <span className="w-2 h-2 rounded-full bg-current"></span>
                  {syncStatus.source === 'snowflake' ? 'Live from Snowflake' : 'Local YAML'}
                </div>
                <span className="text-[10px] text-on-surface-variant">{entries.length} total entries</span>
              </div>
            )}
          </div>

          {/* Search & Filters */}
          <div className="flex gap-3 mb-6">
            <div className="relative flex-1">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline-variant text-xl">search</span>
              <input
                className="w-full bg-surface-container-low border border-outline-variant/15 rounded-xl pl-12 pr-4 py-3.5 text-on-surface placeholder:text-outline-variant focus:ring-2 focus:ring-primary/20 focus:border-primary/30 transition-all font-medium"
                placeholder="Search metrics, aliases, columns..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <select
              className="bg-surface-container-low border border-outline-variant/15 rounded-xl px-4 py-3.5 text-on-surface font-medium text-sm focus:ring-2 focus:ring-primary/20 cursor-pointer min-w-[160px]"
              value={sourceFilter}
              onChange={e => setSourceFilter(e.target.value)}
            >
              <option value="all">All Sources</option>
              {sources.map(s => (
                <option key={s} value={s}>{s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</option>
              ))}
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
            </div>
          ) : (
            <>
              {/* Metric Dictionary Section */}
              {metricDictEntries.length > 0 && (
                <div className="mb-8">
                  <h2 className="text-[11px] font-bold uppercase tracking-widest text-outline mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[14px] text-primary">analytics</span>
                    Metric Dictionary ({metricDictEntries.length})
                  </h2>
                  <div className="grid gap-3">
                    {metricDictEntries.map((entry, i) => (
                      <div key={i} className="bg-surface-container-low/60 border border-outline-variant/10 rounded-xl p-4 hover:border-primary/20 hover:shadow-md transition-all group">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <code className="text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-lg font-bold tracking-wide">{entry.term}</code>
                            <span className="material-symbols-outlined text-[14px] text-outline-variant">arrow_right_alt</span>
                            <span className="text-sm font-semibold text-on-surface">{entry.replacement}</span>
                          </div>
                          <span className="text-[9px] uppercase tracking-widest text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-md font-bold">dictionary</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Override Entries Section */}
              {overrideEntries.length > 0 && (
                <div>
                  <h2 className="text-[11px] font-bold uppercase tracking-widest text-outline mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[14px] text-tertiary">translate</span>
                    User Overrides ({overrideEntries.length})
                  </h2>
                  <div className="grid gap-2">
                    {overrideEntries.map((entry, i) => (
                      <div key={i} className="bg-surface-container-low/60 border border-outline-variant/10 rounded-xl p-4 hover:border-tertiary/20 hover:shadow-md transition-all">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <code className="text-xs bg-tertiary/10 text-tertiary px-2.5 py-1 rounded-lg font-bold tracking-wide">{entry.term}</code>
                            <span className="material-symbols-outlined text-[14px] text-outline-variant">arrow_right_alt</span>
                            <span className="text-sm font-semibold text-on-surface">{entry.replacement}</span>
                          </div>
                          <span className={`text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-md font-bold ${
                            entry.category === 'snowflake' ? 'bg-blue-500/10 text-blue-400' :
                            entry.category === 'salesforce' ? 'bg-purple-500/10 text-purple-400' :
                            entry.category === 'sql' ? 'bg-orange-500/10 text-orange-400' :
                            entry.category === 'internal' ? 'bg-emerald-500/10 text-emerald-400' :
                            'bg-surface-container text-on-surface-variant'
                          }`}>{entry.category || 'custom'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {filtered.length === 0 && (
                <div className="text-center py-16 text-on-surface-variant">
                  <span className="material-symbols-outlined text-5xl mb-3 block opacity-40">search_off</span>
                  <p className="font-medium">No entries match your search.</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}


/* ################################################################
   Jargon Page — CRUD jargon overrides with Snowflake sync
   ################################################################ */

function JargonPage() {
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("all");
  const [newTerm, setNewTerm] = useState("");
  const [newReplacement, setNewReplacement] = useState("");
  const [newCategory, setNewCategory] = useState("custom");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const fetchEntries = () => {
    setLoading(true);
    fetch(`${API_URL}/jargon`)
      .then(r => r.json())
      .then(d => {
        const all = d.terms || [];
        setEntries(all.filter((e: GlossaryEntry) => e.source === "user_override"));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchEntries(); }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 4000);
  };

  const handleAdd = async () => {
    if (!newTerm.trim() || !newReplacement.trim()) return;
    setSaving(true);
    try {
      await fetch(`${API_URL}/jargon`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: newTerm.trim(), replacement: newReplacement.trim(), category: newCategory }),
      });
      setNewTerm("");
      setNewReplacement("");
      showToast(`Added: "${newTerm.trim()}" rule`);
      fetchEntries();
    } catch {
      showToast("Failed to add rule");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (term: string) => {
    try {
      await fetch(`${API_URL}/jargon/${encodeURIComponent(term)}`, { method: "DELETE" });
      showToast(`Removed: "${term}"`);
      fetchEntries();
    } catch {
      showToast("Failed to remove rule");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_URL}/api/sync-semantics`, { method: "POST" });
      const data = await res.json();
      showToast(`Synced ${data.overrides_count} rules + ${data.dictionary_count} dict entries from Snowflake`);
      fetchEntries();
    } catch {
      showToast("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const categories = Array.from(new Set(entries.map(e => e.category || "custom")));
  const filtered = entries.filter(e => {
    const matchesSearch = !search ||
      e.term.toLowerCase().includes(search.toLowerCase()) ||
      e.replacement.toLowerCase().includes(search.toLowerCase());
    const matchesCat = catFilter === "all" || (e.category || "custom") === catFilter;
    return matchesSearch && matchesCat;
  });

  const catColors: Record<string, string> = {
    snowflake: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    salesforce: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    sql: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    internal: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    custom: "bg-pink-500/10 text-pink-400 border-pink-500/20",
  };

  return (
    <section className="flex-1 flex flex-col bg-surface min-w-0 overflow-hidden fade-slide-in">
      <div className="flex-1 overflow-y-auto hide-scrollbar">
        <div className="max-w-5xl mx-auto px-8 py-10">
          {/* Header */}
          <div className="flex items-start justify-between mb-8">
            <div>
              <h1 className="text-3xl font-headline font-extrabold text-on-surface mb-2 flex items-center gap-3">
                <span className="material-symbols-outlined text-tertiary text-4xl">translate</span>
                Language Rules
              </h1>
              <p className="text-on-surface-variant font-medium max-w-lg">
                Manage jargon translation rules. When the AI generates a response containing a matched term,
                it will be automatically rewritten using the human-friendly replacement.
              </p>
            </div>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary/10 text-primary font-bold text-sm hover:bg-primary/20 transition-all disabled:opacity-50 shrink-0"
            >
              <span className={`material-symbols-outlined text-lg ${syncing ? 'animate-spin' : ''}`}>
                {syncing ? 'progress_activity' : 'sync'}
              </span>
              {syncing ? 'Syncing...' : 'Sync from Snowflake'}
            </button>
          </div>

          {/* Add New Rule */}
          <div className="bg-surface-container-low/80 border border-outline-variant/15 rounded-2xl p-6 mb-8">
            <h2 className="text-[11px] font-bold uppercase tracking-widest text-outline mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-[14px] text-primary">add_circle</span>
              Add New Rule
            </h2>
            <div className="flex gap-3 items-end">
              <div className="flex-1">
                <label className="text-[10px] font-bold uppercase tracking-widest text-outline-variant mb-1.5 block">Technical Term</label>
                <input
                  className="w-full bg-surface border border-outline-variant/15 rounded-xl px-4 py-3 text-on-surface placeholder:text-outline-variant focus:ring-2 focus:ring-primary/20 font-mono text-sm"
                  placeholder="e.g. PRODUCT_SKU or ChurnRisk__c"
                  value={newTerm}
                  onChange={e => setNewTerm(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAdd()}
                />
              </div>
              <div className="flex-1">
                <label className="text-[10px] font-bold uppercase tracking-widest text-outline-variant mb-1.5 block">Human Replacement</label>
                <input
                  className="w-full bg-surface border border-outline-variant/15 rounded-xl px-4 py-3 text-on-surface placeholder:text-outline-variant focus:ring-2 focus:ring-primary/20 text-sm"
                  placeholder="e.g. product code"
                  value={newReplacement}
                  onChange={e => setNewReplacement(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleAdd()}
                />
              </div>
              <div className="w-40">
                <label className="text-[10px] font-bold uppercase tracking-widest text-outline-variant mb-1.5 block">Category</label>
                <select
                  className="w-full bg-surface border border-outline-variant/15 rounded-xl px-4 py-3 text-on-surface text-sm cursor-pointer focus:ring-2 focus:ring-primary/20"
                  value={newCategory}
                  onChange={e => setNewCategory(e.target.value)}
                >
                  <option value="custom">Custom</option>
                  <option value="snowflake">Snowflake</option>
                  <option value="salesforce">Salesforce</option>
                  <option value="sql">SQL</option>
                  <option value="internal">Internal</option>
                </select>
              </div>
              <button
                onClick={handleAdd}
                disabled={saving || !newTerm.trim() || !newReplacement.trim()}
                className="px-6 py-3 bg-primary text-on-primary rounded-xl font-bold text-sm hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:hover:scale-100 shadow-md shrink-0"
              >
                {saving ? 'Adding...' : 'Add Rule'}
              </button>
            </div>
          </div>

          {/* Search & Filters */}
          <div className="flex gap-3 mb-6">
            <div className="relative flex-1">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline-variant text-xl">search</span>
              <input
                className="w-full bg-surface-container-low border border-outline-variant/15 rounded-xl pl-12 pr-4 py-3.5 text-on-surface placeholder:text-outline-variant focus:ring-2 focus:ring-primary/20 font-medium"
                placeholder="Search rules..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCatFilter("all")}
                className={`px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border ${catFilter === 'all' ? 'bg-primary/10 text-primary border-primary/20' : 'bg-surface-container-low text-on-surface-variant border-outline-variant/15 hover:bg-surface-container'}`}
              >All ({entries.length})</button>
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setCatFilter(cat)}
                  className={`px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border ${catFilter === cat ? (catColors[cat] || catColors.custom) + ' border' : 'bg-surface-container-low text-on-surface-variant border-outline-variant/15 hover:bg-surface-container'}`}
                >{cat} ({entries.filter(e => (e.category || 'custom') === cat).length})</button>
              ))}
            </div>
          </div>

          {/* Rules List */}
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <span className="material-symbols-outlined text-4xl text-primary animate-spin">progress_activity</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-on-surface-variant">
              <span className="material-symbols-outlined text-5xl mb-3 block opacity-40">rule</span>
              <p className="font-medium">{search ? 'No rules match your search.' : 'No language rules yet. Add one above!'}</p>
            </div>
          ) : (
            <div className="grid gap-2">
              {filtered.map((entry, i) => (
                <div key={i} className="bg-surface-container-low/60 border border-outline-variant/10 rounded-xl p-4 hover:border-outline-variant/25 transition-all group flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <code className="text-xs bg-surface-container px-2.5 py-1 rounded-lg font-bold tracking-wide text-on-surface shrink-0">{entry.term}</code>
                    <span className="material-symbols-outlined text-[14px] text-outline-variant shrink-0">arrow_right_alt</span>
                    <span className="text-sm font-medium text-on-surface truncate">{entry.replacement}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-[9px] uppercase tracking-widest px-2 py-0.5 rounded-md font-bold border ${catColors[entry.category || 'custom'] || catColors.custom}`}>
                      {entry.category || 'custom'}
                    </span>
                    <button
                      onClick={() => handleDelete(entry.term)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 hover:bg-red-500/10 rounded-lg text-red-400"
                      title="Delete rule"
                    >
                      <span className="material-symbols-outlined text-lg">delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 fade-slide-in">
          <div className={`px-6 py-3 rounded-xl shadow-2xl font-medium text-sm ${toast.includes('Failed') || toast.includes('failed') ? 'bg-red-500 text-white' : 'bg-emerald-500 text-white'}`}>
            {toast}
          </div>
        </div>
      )}
    </section>
  );
}


/* ################################################################
   Right Panel
   ################################################################ */


function StatusIconOnly({ status, icon, title }: { status?: string; icon: string; title: string }) {
  const isLive = status === "live" || (status && status.startsWith("ok"));
  const isSyncing = status === "syncing" || status === "connecting";
  return (
    <div title={`${title} - ${isLive ? 'Live' : isSyncing ? 'Sync' : 'Error'}`} className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-surface-container-lowest border border-outline-variant/10 shadow-sm text-tertiary">
      <span className="material-symbols-outlined text-[16px]">{icon}</span>
      <div className={`absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full ${(isLive || isSyncing) ? 'bg-secondary animate-pulse' : 'bg-red-500'}`}></div>
    </div>
  );
}

function RightPanel({ data }: { data: AnswerPayload | null }) {
  const [activeTab, setActiveTab] = useState("Visuals");
  const [width, setWidth] = useState(400);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth >= 300 && newWidth <= 800) {
        setWidth(newWidth);
      }
    };
    const handleMouseUp = () => setIsDragging(false);

    if (isDragging) {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  const wrapPanel = (children: React.ReactNode) => (
    <section 
      style={{ width }} 
      className="hidden xl:flex flex-shrink-0 bg-surface-container-lowest border-l border-outline-variant/15 flex-col shadow-xl relative z-20 transition-transform"
    >
      {/* Drag Handle */}
      <div 
        onMouseDown={() => setIsDragging(true)}
        className="absolute left-0 top-0 w-1.5 h-full cursor-col-resize hover:bg-primary/20 hover:w-2 transition-all z-30 group flex items-center justify-center"
      >
        <div className="w-[2px] h-8 bg-outline-variant/50 rounded-full group-hover:bg-primary/50" />
      </div>
      <div className="flex-1 w-full flex flex-col pt-6 relative overflow-hidden">
        {children}
      </div>
    </section>
  );

  if (!data) {
    return wrapPanel(
      <>
        <div className="px-6 mb-6 text-center">
          <h2 className="text-xl font-headline font-extrabold text-on-surface">Transparency Dashboard</h2>
          <p className="text-xs text-on-surface-variant mt-2 font-medium">Under the hood metrics and sources.</p>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-on-surface-variant opacity-60">
          <span className="material-symbols-outlined text-6xl mb-4">settings_input_component</span>
          <p className="text-sm">Initiate a query to populate telemetry.</p>
        </div>
      </>
    );
  }

  const charts = data.charts || [];
  const ragDocs = data.rag_documents || [];
  const webResults = data.web_results || [];
  const sfRecords = data.salesforce_records || [];
  const jargonSubs = data.jargon_substitutions || [];
  const rawData = data.transparency?.raw_data || (charts.length > 0 ? charts[0].data as Record<string,unknown>[] : null);

  const tabs = ["Visuals", "SQL", "Docs", "Insights"];
  const fallbackSql = data.transparency?.sql && !charts.some((c) => c.sql) ? data.transparency.sql : null;

  return wrapPanel(
    <>
      <div className="px-6 mb-4 flex justify-between items-center">
        <h2 className="text-lg font-headline font-extrabold text-on-surface tracking-tight">Details</h2>
        {data.confidence_tier && (
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest shadow-sm ${data.confidence_tier === 'green' ? 'bg-secondary-container text-secondary-dim border border-secondary/20' : 'bg-orange-100 text-orange-700 border border-orange-200'}`}>
            <span className="material-symbols-outlined text-[14px]">verified</span>
            {Math.round((data.confidence_score || 0) * 100)}%
          </div>
        )}
      </div>

      <div className="px-6 mb-2">
        <div className="flex gap-2 border-b border-outline-variant/20 overflow-x-auto hide-scrollbar">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-xs font-semibold whitespace-nowrap transition-colors relative tracking-wide ${activeTab === tab ? 'text-primary' : 'text-on-surface-variant hover:text-on-surface'}`}
            >
              {tab}
              {activeTab === tab && <div className="absolute bottom-[-1px] left-0 w-full h-[2px] bg-primary rounded-t-full"></div>}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 hide-scrollbar pb-12 fade-slide-in">
        {/* Security Context Card */}
        {data.security_context && (
          <div className="mb-4 p-3 rounded-xl border flex items-center gap-3" style={{
            borderColor: data.security_context.region_filter ? '#4488cc30' : '#c5a00030',
            background: data.security_context.region_filter ? '#4488cc08' : '#c5a00008',
          }}>
            <span className="material-symbols-outlined text-xl" style={{
              color: data.security_context.region_filter ? '#4488cc' : '#c5a000'
            }}>
              {data.security_context.region_filter ? 'shield_lock' : 'verified_user'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Security Context</div>
              <div className="text-xs font-semibold text-on-surface truncate">{data.security_context.label}</div>
              {data.security_context.region_filter && (
                <div className="text-[10px] text-on-surface-variant mt-0.5">Data restricted to <strong>{data.security_context.region_filter}</strong> region</div>
              )}
            </div>
            <span className="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded-full" style={{
              background: data.security_context.region_filter ? '#4488cc18' : '#c5a00018',
              color: data.security_context.region_filter ? '#4488cc' : '#c5a000',
            }}>
              {data.security_context.region_filter ? 'RLS Active' : 'Unrestricted'}
            </span>
          </div>
        )}

        {activeTab === "Visuals" && (
          <div className="space-y-6">
            {/* E2B Rich Visualization (priority render) */}
            {(data.e2b_plotly_json || data.e2b_chart_image) && (
              <div className="space-y-3">
                <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[12px] text-tertiary">auto_awesome</span>
                  AI-Generated Analysis
                </h3>
                <E2BChart plotlyJson={data.e2b_plotly_json} fallbackImage={data.e2b_chart_image} />
              </div>
            )}
            {/* Standard Chart.js charts */}
            {charts.length === 0 && !data.e2b_plotly_json && !data.e2b_chart_image ? (
               <p className="text-center text-on-surface-variant text-sm mt-8 opacity-70">No visuals available.</p>
            ) : (
               charts.map((c, i) => <ChartCard key={i} chart={c} colorIdx={i} />)
            )}
          </div>
        )}

        {activeTab === "SQL" && (
          <div className="space-y-6">
            {charts.some((c) => c.sql) ? (
              charts.filter((c) => c.sql).map((c, i) => (
                <SqlBlock key={i} sql={c.sql!} label={charts.length > 1 ? `Query ${i + 1}` : "Snowflake SQL"} />
              ))
            ) : fallbackSql ? (
              <SqlBlock sql={fallbackSql} label="Snowflake SQL" />
            ) : (
              <p className="text-center text-on-surface-variant text-sm mt-8 opacity-70">No SQL executed.</p>
            )}
            {/* E2B Generated Python Code */}
            {data.transparency?.python_code && (
              <div className="mt-4">
                <SqlBlock sql={data.transparency.python_code} label="E2B Sandbox — Generated Python" />
              </div>
            )}
          </div>
        )}

        {activeTab === "Docs" && (
          <div className="space-y-6">
            {ragDocs.length === 0 && webResults.length === 0 && sfRecords.length === 0 && !rawData ? (
               <p className="text-center text-on-surface-variant text-sm mt-8 opacity-70">No source documents retrieved.</p>
            ) : (
              <>
                {ragDocs.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Knowledge Base</h3>
                    {ragDocs.map((doc, i) => <RagCard key={i} doc={doc} />)}
                  </div>
                )}
                {webResults.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Web Intelligence</h3>
                    {webResults.map((wr, i) => <WebCard key={i} result={wr} />)}
                  </div>
                )}
                {sfRecords.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Salesforce CRM</h3>
                    {sfRecords.map((rec, i) => <SFCard key={i} record={rec} />)}
                  </div>
                )}
                {rawData && rawData.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Raw Data Output</h3>
                    <DataTable rows={rawData} />
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "Insights" && (
          <div className="space-y-6">
            {/* Semantic Status Panel */}
            <SemanticStatusPanel />

            {data.confidence_score == null && jargonSubs.length === 0 ? (
              <p className="text-center text-on-surface-variant text-sm mt-8 opacity-70">No deep insights generated.</p>
            ) : (
              <>
                {data.confidence_score != null && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Confidence Engine</h3>
                    <ConfidencePanel score={data.confidence_score} tier={data.confidence_tier || "green"} charts={charts} rawData={rawData} />
                  </div>
                )}
                {jargonSubs.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase mb-2">Dynamic Syntax Analysis ({jargonSubs.length} substitutions)</h3>
                    {jargonSubs.map((sub, i) => (
                      <div key={i} className="flex flex-col p-3 rounded-lg bg-surface border border-outline-variant/10 shadow-sm gap-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium line-through text-outline opacity-60">{sub.original}</span>
                          <span className="material-symbols-outlined text-[14px] text-tertiary">arrow_right_alt</span>
                          <span className="text-xs font-bold text-primary">{sub.replacement}</span>
                        </div>
                        <span className="text-[9px] uppercase tracking-widest text-primary/70">{sub.category.replace(/_/g, " ")}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </>
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
    const tierColors: Record<string, string> = {
      green: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
      amber: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
      red: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
    };
    const pillClass = `text-[10px] font-bold px-2 py-0.5 rounded-full border ${tierColors[chart.confidence_tier || "green"]}`;

    return (
      <div className="relative flex flex-col p-5 rounded-2xl bg-surface border border-outline-variant/15 shadow-sm gap-4 w-full">
        {chart.title && (
          <div className="flex items-start justify-between gap-4 mb-2">
            <span className="text-base font-headline font-semibold text-on-surface flex-1 leading-snug">{chart.title}</span>
            <span className={pillClass}>{Math.round(chart.confidence_score * 100)}%</span>
          </div>
        )}
        <div className="flex flex-col items-center justify-center py-6 bg-surface-container-low rounded-xl border border-outline-variant/10">
          <div className="text-4xl font-extrabold text-primary">{formatNumber(val)}</div>
          <div className="text-[10px] text-outline font-bold uppercase tracking-widest mt-2">{(numKey || "").replace(/_/g, " ")}</div>
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
        position: chartType === "doughnut" ? "bottom" : "top",
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

  const tierColors: Record<string, string> = {
    green: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
    amber: "bg-orange-500/20 text-orange-700 dark:text-orange-400 border-orange-500/30",
    red: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  };
  const pillClass = `text-[10px] font-bold px-2 py-0.5 rounded-full border ${tierColors[chart.confidence_tier || "green"]}`;

  return (
    <div className="relative flex flex-col p-5 rounded-2xl bg-surface border border-outline-variant/15 shadow-sm gap-4 w-full">
      {(chart.title || true) && (
        <div className="flex items-start justify-between gap-4 mb-2">
          <span className="text-base font-headline font-semibold text-on-surface flex-1 leading-snug">{chart.title || `Chart ${colorIdx + 1}`}</span>
          <span className={pillClass}>{Math.round(chart.confidence_score * 100)}%</span>
        </div>
      )}
      <div className="w-full" style={{ height: 260 }}>
        <ChartComponent data={chartData} options={options as any} />
      </div>
    </div>
  );
}

/* ################################################################
   E2B Chart (Plotly interactive / PNG fallback)
   ################################################################ */

function E2BChart({ plotlyJson, fallbackImage }: { plotlyJson?: string; fallbackImage?: string }) {
  if (plotlyJson) {
    try {
      const fig = JSON.parse(plotlyJson);
      return (
        <div className="rounded-2xl overflow-hidden bg-surface-container-lowest/50 backdrop-blur-sm p-4 border border-outline-variant/10 shadow-sm transition-all hover:shadow-md">
          <Plot
            data={fig.data}
            layout={{
              ...fig.layout,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
              font: { family: 'Manrope, sans-serif', color: '#2a3435', size: 12 },
              autosize: true,
              margin: { l: 50, r: 20, t: 40, b: 50 },
              legend: {
                ...fig.layout?.legend,
                bgcolor: 'rgba(0,0,0,0)',
                font: { family: 'Manrope, sans-serif', color: '#6b7d7e', size: 11 },
              },
              xaxis: {
                ...fig.layout?.xaxis,
                gridcolor: 'rgba(224, 231, 231, 0.4)',
                zerolinecolor: 'rgba(224, 231, 231, 0.4)',
              },
              yaxis: {
                ...fig.layout?.yaxis,
                gridcolor: 'rgba(224, 231, 231, 0.4)',
                zerolinecolor: 'rgba(224, 231, 231, 0.4)',
              },
            }}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: '100%', height: 350 }}
          />
        </div>
      );
    } catch (e) {
      console.error("Failed to parse Plotly JSON:", e);
      // Fall through to PNG fallback
    }
  }

  if (fallbackImage) {
    return (
      <div className="rounded-2xl overflow-hidden bg-surface-container-lowest/50 backdrop-blur-sm p-4 border border-outline-variant/10 shadow-sm">
        <img
          src={`data:image/png;base64,${fallbackImage}`}
          alt="AI-generated data analysis"
          className="w-full rounded-xl"
        />
      </div>
    );
  }

  return null;
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
    <div className={`p-5 rounded-2xl border transition-all duration-300 ${expanded ? "bg-surface-container-low border-primary/20 shadow-lg" : "bg-surface/50 border-outline-variant/10 shadow hover:shadow-md hover:border-outline-variant/20 backdrop-blur-sm"}`}>
      <div className="flex justify-between items-start mb-3">
        <span className="font-semibold text-on-surface line-clamp-2 pr-4">{doc.title}</span>
        <span className="shrink-0 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold ring-1 ring-primary/20">{scorePct}% match</span>
      </div>
      <div className="flex items-center text-xs font-bold tracking-widest uppercase text-tertiary mb-3"><Database size={12} className="mr-1.5"/> {doc.space || "AURA"}</div>
      <div className={`text-sm text-on-surface-variant leading-relaxed ${!expanded && "line-clamp-3"}`}>{expanded ? excerpt : excerpt.substring(0, 400)}</div>
      <button className="flex items-center gap-1.5 mt-4 text-sm font-semibold text-primary hover:text-primary-dim transition-colors" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Show less" : "Show more"}
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
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
    <div className={`p-5 rounded-2xl border transition-all duration-300 ${expanded ? "bg-surface-container-low border-primary/20 shadow-lg" : "bg-surface/50 border-outline-variant/10 shadow hover:shadow-md hover:border-outline-variant/20 backdrop-blur-sm"}`}>
      <div className="flex justify-between items-start mb-3">
        <span className="font-semibold text-primary hover:underline line-clamp-2 pr-4"><a href={result.url} target="_blank" rel="noopener noreferrer">{result.title}</a></span>
        <span className="shrink-0 px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-bold ring-1 ring-primary/20">{scorePct}% match</span>
      </div>
      <div className="flex items-center text-xs font-bold tracking-widest uppercase text-tertiary mb-3"><Globe size={12} className="mr-1.5"/> {domain}</div>
      <div className={`text-sm text-on-surface-variant leading-relaxed ${!expanded && "line-clamp-3"}`}>{result.content}</div>
      <button className="flex items-center gap-1.5 mt-4 text-sm font-semibold text-primary hover:text-primary-dim transition-colors" onClick={() => setExpanded(!expanded)}>
        {expanded ? "Show less" : "Show more"}
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
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
    <div className="p-5 rounded-2xl bg-surface/50 border border-outline-variant/10 shadow backdrop-blur-sm">
      <div className="flex justify-between items-start mb-3">
        <span className="font-semibold text-on-surface flex items-center gap-2"><Cloud size={16} className="text-secondary"/> {record.account_name}</span>
        <span className="shrink-0 px-2.5 py-1 rounded-full bg-secondary/10 text-secondary text-xs font-bold ring-1 ring-secondary/20">{scorePct}% match</span>
      </div>
      <div className="text-xs font-bold tracking-widest uppercase text-tertiary mb-3">{record.object_type}</div>
      <div className="text-sm text-on-surface-variant leading-relaxed">{record.excerpt}</div>
    </div>
  );
}

/* ################################################################
   SQL Block
   ################################################################ */

function SqlBlock({ sql, label }: { sql: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editedSql, setEditedSql] = useState(sql);
  const [isSaving, setIsSaving] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      setIsModalOpen(false);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    }, 1500);
  };

  return (
    <div className="relative">
      <div className="rounded-2xl overflow-hidden border border-outline-variant/15 shadow-sm bg-slate-900">
        <div className="flex justify-between items-center px-4 py-3 border-b border-white/10 bg-slate-800/80 backdrop-blur-md">
          <span className="text-xs font-medium text-slate-300">{label}</span>
          <div className="flex gap-2">
            <button 
              className="text-xs px-3 py-1.5 rounded-lg bg-primary/20 hover:bg-primary/30 text-primary transition-colors flex items-center gap-1 font-semibold"
              onClick={() => { setEditedSql(sql); setIsModalOpen(true); }}
            >
              <span className="material-symbols-outlined text-[14px]">model_training</span> Edit & Teach AI
            </button>
            <button 
              className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 transition-colors flex items-center gap-1"
              onClick={() => { navigator.clipboard.writeText(sql); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
            >
              {copied ? <Check size={14}/> : <Code size={14} />} {copied ? "Copied!" : "Copy SQL"}
            </button>
          </div>
        </div>
        <div className="p-5 overflow-x-auto custom-scrollbar">
          <pre className="text-sm font-mono text-slate-300 leading-relaxed">{sql}</pre>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 fade-slide-in">
          <div className="bg-surface-container rounded-2xl w-full max-w-2xl border border-outline-variant/30 overflow-hidden shadow-2xl flex flex-col">
            <div className="px-6 py-4 border-b border-outline-variant/20 flex justify-between items-center bg-surface-container-low">
              <h3 className="text-lg font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">model_training</span> Agent Training
              </h3>
              <button disabled={isSaving} onClick={() => setIsModalOpen(false)} className="text-on-surface-variant hover:text-on-surface">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="p-6">
              <p className="text-sm text-on-surface-variant mb-4">Correct the SQL output below to train the AI architecture for similar future queries.</p>
              <textarea 
                className="w-full h-48 bg-surface-container-lowest border border-outline-variant/30 rounded-xl p-4 text-sm font-mono text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
                value={editedSql}
                onChange={(e) => setEditedSql(e.target.value)}
                disabled={isSaving}
              />
            </div>
            <div className="px-6 py-4 border-t border-outline-variant/20 flex justify-end gap-3 bg-surface-container-low">
              <button disabled={isSaving} onClick={() => setIsModalOpen(false)} className="px-4 py-2 rounded-lg text-sm font-semibold text-on-surface-variant hover:bg-surface-container-high transition-colors">
                Cancel
              </button>
              <button disabled={isSaving} onClick={handleSave} className="px-4 py-2 rounded-lg text-sm font-semibold bg-primary text-on-primary hover:bg-primary/90 transition-colors flex items-center gap-2">
                {isSaving ? <><span className="w-4 h-4 rounded-full border-2 border-on-primary border-t-transparent animate-spin"></span> Saving...</> : "Save to Knowledge Base"}
              </button>
            </div>
          </div>
        </div>
      )}

      {showToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#1e4620] text-emerald-100 border border-emerald-500/30 px-4 py-3 rounded-xl shadow-lg flex items-center gap-3 fade-slide-in">
          <span className="text-emerald-400">🟢</span>
          <p className="text-sm font-medium">Query embedded and saved to Pinecone examples_store.</p>
        </div>
      )}
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
    <div className="rounded-2xl border border-outline-variant/20 overflow-hidden shadow-sm bg-surface">
      <div className="overflow-x-auto max-h-[400px] custom-scrollbar">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-surface-container-low text-on-surface-variant sticky top-0 backdrop-blur-md z-10 border-b border-outline-variant/20">
            <tr>{keys.map((k) => <th key={k} className="px-5 py-3 font-semibold text-xs uppercase tracking-wider">{k.replace(/_/g, " ")}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/10 text-on-surface">
            {rows.slice(0, 50).map((row, i) => (
              <tr key={i} className="hover:bg-surface-container-lowest/50 transition-colors">
                {keys.map((k) => {
                  let v = row[k];
                  if (typeof v === "number") v = formatNumber(v);
                  return <td key={k} className="px-5 py-3.5 align-middle">{String(v ?? "")}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ################################################################
   Semantic Status Panel (Snowflake Sync)
   ################################################################ */

function SemanticStatusPanel() {
  const [status, setStatus] = useState<{
    last_sync: string | null;
    overrides_count: number;
    source: string;
    connector_available: boolean;
  } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/sync-status`)
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch(`${API_URL}/api/sync-semantics`, { method: "POST" });
      const data = await res.json();
      setSyncResult(`Synced ${data.overrides_count} rules + ${data.dictionary_count} dictionary terms`);
      // Refresh status
      const statusRes = await fetch(`${API_URL}/api/sync-status`);
      setStatus(await statusRes.json());
    } catch {
      setSyncResult("Sync failed — check backend connection");
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncResult(null), 5000);
    }
  };

  const getTimeSince = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ago`;
  };

  const isConnected = status?.connector_available ?? false;
  const isRecent = status?.last_sync
    ? Date.now() - new Date(status.last_sync).getTime() < 5 * 60 * 1000
    : false;

  const statusColor = !isConnected
    ? "text-red-400"
    : isRecent
      ? "text-emerald-400"
      : "text-amber-400";

  const statusLabel = !isConnected
    ? "Snowflake unreachable — using cached rules"
    : isRecent
      ? "Synced with Snowflake Data Catalog"
      : "Sync recommended";

  const statusDot = !isConnected ? "🔴" : isRecent ? "🟢" : "🟡";

  return (
    <div className="rounded-xl border border-outline-variant/15 bg-surface-container-low/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-bold text-outline tracking-wider uppercase flex items-center gap-1.5">
          <span className="material-symbols-outlined text-[13px] text-primary">database</span>
          Semantic Catalog
        </h3>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary hover:bg-primary/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className={`material-symbols-outlined text-[13px] ${syncing ? "animate-spin" : ""}`}>
            {syncing ? "progress_activity" : "sync"}
          </span>
          {syncing ? "Syncing…" : "Sync Now"}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm">{statusDot}</span>
        <span className={`text-xs font-medium ${statusColor}`}>{statusLabel}</span>
      </div>

      {status && (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-surface-container-lowest/70 p-2.5 text-center">
            <div className="text-lg font-bold text-on-surface">{status.overrides_count}</div>
            <div className="text-[9px] uppercase tracking-widest text-on-surface-variant font-medium">Override Rules</div>
          </div>
          <div className="rounded-lg bg-surface-container-lowest/70 p-2.5 text-center">
            <div className="text-lg font-bold text-on-surface">{status.source === "snowflake" ? "Live" : "Local"}</div>
            <div className="text-[9px] uppercase tracking-widest text-on-surface-variant font-medium">Data Source</div>
          </div>
        </div>
      )}

      {status?.last_sync && (
        <p className="text-[10px] text-on-surface-variant/70 text-center">
          Last synced: {getTimeSince(status.last_sync)}
        </p>
      )}

      {syncResult && (
        <div className={`text-[10px] font-medium text-center px-3 py-1.5 rounded-lg ${syncResult.includes("failed") ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"} fade-slide-in`}>
          {syncResult}
        </div>
      )}
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
  const colorClass =
    tier === "green" ? "bg-green-500" : tier === "amber" ? "bg-amber-500" : "bg-red-500";
  const textClass =
    tier === "green" ? "text-green-500" : tier === "amber" ? "text-amber-500" : "text-red-500";
  const bgSoftClass =
    tier === "green" ? "bg-green-500/10" : tier === "amber" ? "bg-amber-500/10" : "bg-red-500/10";
  const label = tier === "green" ? "HIGH CONFIDENCE" : tier === "amber" ? "MEDIUM CONFIDENCE" : "LOW CONFIDENCE";
  const chartCount = charts.length || 1;
  const totalRows = charts.reduce((s, c) => s + (c.row_count || 0), 0) || rawData?.length || 0;

  return (
    <div className="bg-surface-container-low rounded-2xl p-6 border border-outline-variant/20 shadow-inner">
      <div className="flex justify-between items-end mb-6">
        <div className={`px-4 py-2 rounded-full inline-flex items-center gap-2 ${bgSoftClass} border border-${tier}-500/20`}>
          <div className={`w-2.5 h-2.5 rounded-full ${colorClass} animate-pulse shadow-[0_0_8px_currentColor]`} />
          <span className={`text-xs font-bold tracking-widest uppercase ${textClass}`}>{label}</span>
        </div>
        <div className={`text-5xl font-headline font-light tracking-tighter ${textClass}`}>
          {score.toFixed(3)}
        </div>
      </div>
      
      <div className="h-1.5 w-full bg-surface-container-highest rounded-full overflow-hidden mb-6">
        <div className={`h-full ${colorClass} rounded-full transition-all duration-1000 ease-out`} style={{ width: `${score * 100}%` }} />
      </div>
      
      <div className="flex justify-between items-center text-sm">
        <div className="flex flex-col gap-1">
          <span className="text-on-surface-variant text-xs uppercase tracking-widest font-semibold">Sources Combined</span>
          <span className="text-on-surface font-medium text-lg">{chartCount} Views</span>
        </div>
        <div className="flex flex-col gap-1 text-right">
          <span className="text-on-surface-variant text-xs uppercase tracking-widest font-semibold">Row Entropy</span>
          <span className="text-on-surface font-medium text-lg">{formatNumber(totalRows)} Scanned</span>
        </div>
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

/* ################################################################
   Upload Page — Upload documents to the knowledge base
   ################################################################ */

function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [space, setSpace] = useState("UPLOADS");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ status: string; title: string; chunks: number; total_chars: number; filename: string } | null>(null);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [kbStats, setKbStats] = useState<{ total_vectors: number; namespaces: Record<string, number> } | null>(null);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    fetch(`${API}/api/kb-stats`).then(r => r.json()).then(setKbStats).catch(() => {});
  }, [result]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title || file.name.replace(/\.[^.]+$/, ""));
    formData.append("space", space);

    try {
      const res = await fetch(`${API}/api/upload-document`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
      setResult(data);
      setFile(null);
      setTitle("");
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  return (
    <section className="flex-1 overflow-y-auto px-8 py-10 max-w-3xl mx-auto w-full fade-slide-in">
      <div className="mb-8">
        <h1 className="text-2xl font-headline font-extrabold text-on-surface mb-2">Upload to Knowledge Base</h1>
        <p className="text-sm text-on-surface-variant">Add documents to the RAG knowledge base. Uploaded files are chunked, embedded, and available for AI retrieval immediately.</p>
      </div>

      {/* KB Stats */}
      {kbStats && (
        <div className="mb-6 flex gap-4">
          <div className="flex-1 p-4 rounded-xl bg-primary-container/20 border border-primary-container/40">
            <div className="text-[10px] font-bold uppercase tracking-widest text-outline mb-1">Total Vectors</div>
            <div className="text-2xl font-bold text-primary">{kbStats.total_vectors.toLocaleString()}</div>
          </div>
          {Object.entries(kbStats.namespaces).map(([ns, count]) => (
            <div key={ns} className="flex-1 p-4 rounded-xl bg-surface-container border border-outline-variant/15">
              <div className="text-[10px] font-bold uppercase tracking-widest text-outline mb-1 truncate" title={ns}>{ns}</div>
              <div className="text-2xl font-bold text-on-surface">{(count as number).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
          dragOver
            ? "border-primary bg-primary-container/20 scale-[1.01]"
            : file
            ? "border-secondary bg-secondary-container/10"
            : "border-outline-variant/30 hover:border-primary/40 hover:bg-surface-container-low"
        }`}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".txt,.md,.csv,.pdf";
          input.onchange = (e) => {
            const f = (e.target as HTMLInputElement).files?.[0];
            if (f) setFile(f);
          };
          input.click();
        }}
      >
        <span className="material-symbols-outlined text-5xl mb-3 block" style={{ color: file ? '#426565' : '#6b7d7e' }}>
          {file ? 'description' : 'cloud_upload'}
        </span>
        {file ? (
          <div>
            <p className="text-on-surface font-semibold text-lg">{file.name}</p>
            <p className="text-on-surface-variant text-sm mt-1">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="text-on-surface font-semibold">Drag & drop a file here, or click to browse</p>
            <p className="text-on-surface-variant text-sm mt-1">Supports .txt, .md, .csv, .pdf</p>
          </div>
        )}
      </div>

      {/* Metadata Fields */}
      {file && (
        <div className="mt-6 space-y-4 fade-slide-in">
          <div>
            <label className="text-xs font-bold uppercase tracking-widest text-outline block mb-2">Document Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={file.name.replace(/\.[^.]+$/, "")}
              className="w-full bg-surface-container-low border-none rounded-xl px-5 py-3 focus:ring-4 focus:ring-primary/10 text-on-surface placeholder:text-outline-variant transition-all font-medium"
            />
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-widest text-outline block mb-2">Knowledge Space</label>
            <select
              value={space}
              onChange={(e) => setSpace(e.target.value)}
              className="w-full bg-surface-container-low border-none rounded-xl px-5 py-3 focus:ring-4 focus:ring-primary/10 text-on-surface transition-all font-medium"
            >
              <option value="UPLOADS">Uploads (General)</option>
              <option value="AURA">Aura (Retail Docs)</option>
              <option value="POLICY">Policy (Internal)</option>
              <option value="TRAINING">Training Materials</option>
            </select>
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-primary to-primary-dim text-on-primary font-semibold flex items-center justify-center gap-2 shadow-lg shadow-primary/10 transition-transform active:scale-95 hover:scale-[1.02] disabled:opacity-50 disabled:hover:scale-100"
          >
            {uploading ? (
              <><span className="material-symbols-outlined text-sm animate-spin">progress_activity</span> Uploading & Embedding...</>
            ) : (
              <><span className="material-symbols-outlined text-sm">upload</span> Upload to Knowledge Base</>
            )}
          </button>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mt-6 p-5 rounded-2xl bg-secondary-container/30 border border-secondary/20 fade-slide-in">
          <div className="flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-secondary">check_circle</span>
            <span className="font-semibold text-on-surface">Document Uploaded Successfully</span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-outline-variant">Title:</span> <span className="font-medium text-on-surface">{result.title}</span></div>
            <div><span className="text-outline-variant">File:</span> <span className="font-medium text-on-surface">{result.filename}</span></div>
            <div><span className="text-outline-variant">Chunks:</span> <span className="font-medium text-on-surface">{result.chunks}</span></div>
            <div><span className="text-outline-variant">Characters:</span> <span className="font-medium text-on-surface">{result.total_chars.toLocaleString()}</span></div>
          </div>
          <p className="text-xs text-on-surface-variant mt-3">This document is now searchable via the AI Chat. Try asking a question about its contents.</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 text-sm font-medium fade-slide-in flex items-center gap-2">
          <span className="material-symbols-outlined text-base">error</span>
          {error}
        </div>
      )}
    </section>
  );
}
