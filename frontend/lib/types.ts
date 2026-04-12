export type BranchKey = "sql" | "rag_confluence" | "rag_salesforce" | "web";

export type SourceType =
  | "snowflake"
  | "confluence"
  | "salesforce"
  | "tavily"
  | "upload";

export type ChartType = "bar" | "line" | "doughnut";

export type ConfidenceTier = "green" | "amber" | "red";

export type ConfidenceTierLabel = "GREEN" | "AMBER" | "RED";

export type StatDeltaDirection = "pos" | "neg" | "neutral";

export type ActiveNav = "chat" | "agents" | "history" | "glossary" | "profile";

export type MessageRole = "user" | "ai" | "clarification" | "system";

export type IntegrationStatusValue = "live" | "error" | "connecting" | "syncing";

export type ClassNameValue = string | false | null | undefined;

export interface TraceEntry {
  node: string;
  detail: string;
  highlight?: boolean;
}

export interface SourceChip {
  source_type: SourceType;
  label: string;
  confidence?: number;
}

export interface ContextChunk {
  source_type: "confluence" | "upload";
  title: string;
  space_key?: string;
  body: string;
  updated_at: string;
  chunk_index: number;
  total_chunks: number;
  score: number;
}

export interface ConfidenceScore {
  score: number;
  tier: ConfidenceTier;
  signals: {
    schema_cosine: number;
    retry_score: number;
    row_sanity: number;
  };
  explanation: string;
}

export interface SemanticSubstitution {
  original: string;
  replaced_with: string;
  location: string;
}

export interface TransparencyPayload {
  sql?: string;
  soql?: string;
  raw_data?: Record<string, unknown>[];
  python_code?: string;
  context_chunks?: ContextChunk[];
  confidence?: ConfidenceScore;
  semantic_substitutions?: SemanticSubstitution[];
  validation_passed?: boolean;
  validator_model?: string;
  validator_latency_ms?: number;
}

export interface ChartData {
  type: ChartType;
  labels: string[];
  values: number[];
  colours?: string[];
  y_label?: string;
}

export interface ChartPanel {
  title: string;
  chart_type: string;
  data: Record<string, unknown>[];
  columns: string[];
  sql?: string;
  row_count: number;
  confidence_score: number;
  confidence_tier: string;
}

export interface RagDocument {
  title: string;
  space: string;
  excerpt: string;
  relevance: number;
  source_type?: string;
}

export interface WebResult {
  title: string;
  url: string;
  content: string;
  score: number;
}

export interface SalesforceRecord {
  account_name: string;
  object_type: string;
  excerpt: string;
  relevance: number;
}

export interface StatUpdate {
  label: string;
  value: string;
  delta: string;
  delta_direction: StatDeltaDirection;
}

export interface MetricResolution {
  alias: string;
  display_name: string;
  column_name: string;
}

export interface AnswerPayload {
  text: string;
  branches: BranchKey[];
  trace: TraceEntry[];
  date_resolution?: string;
  metric_resolution?: MetricResolution;
  sources: SourceChip[];
  transparency: TransparencyPayload;
  chart_data?: ChartData;
  charts?: ChartPanel[];
  rag_documents?: RagDocument[];
  web_results?: WebResult[];
  salesforce_records?: SalesforceRecord[];
  stat_updates?: StatUpdate[];
}

export interface ClarificationPayload {
  question: string;
  ambiguous_term: string;
  options: string[];
}

export interface ChatRequest {
  session_id: string;
  message: string;
  clarification_answer?: string;
}

export interface AnswerChatResponse {
  message_id: string;
  type: "answer";
  answer: AnswerPayload;
}

export interface ClarificationChatResponse {
  message_id: string;
  type: "clarification";
  clarification: ClarificationPayload;
}

export type ChatResponse = AnswerChatResponse | ClarificationChatResponse;

export interface MetricEntry {
  name: string;
  display_name: string;
  canonical_column: string;
  unit: string;
  description: string;
  aliases: string[];
  ambiguous: boolean;
}

export interface MetricsResponse {
  metrics: MetricEntry[];
}

export interface IntegrationStatus {
  snowflake: "live" | "error" | "connecting";
  confluence: "live" | "syncing" | "error";
  salesforce: "live" | "error" | "connecting";
  tavily: "live" | "error";
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  answer?: AnswerPayload;
  clarification?: ClarificationPayload;
  timestamp: Date;
}

export interface OmniDataStore {
  sessionId: string;
  resetSession: () => void;
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
  isLoading: boolean;
  setLoading: (v: boolean) => void;
  activeTransparency: TransparencyPayload | null;
  setActiveTransparency: (t: TransparencyPayload | null) => void;
  activeChartData: ChartData | null;
  setActiveChartData: (c: ChartData | null) => void;
  activeStats: StatUpdate[];
  setActiveStats: (s: StatUpdate[]) => void;
  integrationStatus: IntegrationStatus;
  setIntegrationStatus: (s: IntegrationStatus) => void;
  activeNav: ActiveNav;
  setActiveNav: (n: ActiveNav) => void;
  chartPanels: ChartPanel[];
  setChartPanels: (p: ChartPanel[]) => void;
  ragDocuments: RagDocument[];
  setRagDocuments: (d: RagDocument[]) => void;
  webResults: WebResult[];
  setWebResults: (w: WebResult[]) => void;
  salesforceRecords: SalesforceRecord[];
  setSalesforceRecords: (r: SalesforceRecord[]) => void;
}

export interface BranchColour {
  label: string;
  bgClass: string;
  textClass: string;
  borderClass: string;
  accentClass: string;
}

export interface FormatCurrencyOptions {
  currency?: string;
  compact?: boolean;
  maximumFractionDigits?: number;
}

export interface HighlightToken {
  value: string;
  className?: string;
}
