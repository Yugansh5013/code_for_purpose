# OmniData Backend Handoff Context

This repository now contains the OmniData frontend implementation under
`frontend/`. The frontend follows `CODEX_FRONTEND_PROMPT.md` and is ready to
connect to a backend that implements the API contract below.

## Frontend Status

- Next.js 14 App Router, TypeScript, Tailwind CSS.
- Zustand global store in `frontend/lib/store.ts`.
- API client in `frontend/lib/api.ts`.
- Mock responses in `frontend/lib/mockData.ts`.
- Core dashboard components in `frontend/app/components/`.
- Transparency tab components in `frontend/app/components/tabs/`.
- Verified with:
  - `npm run typecheck`
  - `npm run build`
  - local `curl -I http://localhost:3000` returning `200 OK`

The local frontend dev server expects:

```bash
cd frontend
npm run dev
```

Default URL:

```text
http://localhost:3000
```

## Environment

The frontend reads:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK=true
```

Set `NEXT_PUBLIC_USE_MOCK=false` when the backend is ready.

## Required Backend Endpoints

All paths are relative to `NEXT_PUBLIC_API_URL`.

### POST `/api/chat`

Request:

```ts
{
  session_id: string;
  message: string;
  clarification_answer?: string;
}
```

Response shape:

```ts
{
  message_id: string;
  type: "answer" | "clarification";
  answer?: AnswerPayload;
  clarification?: ClarificationPayload;
}
```

For `type: "answer"`, return:

```ts
{
  text: string;
  branches: ("sql" | "rag_confluence" | "rag_salesforce" | "web")[];
  trace: TraceEntry[];
  date_resolution?: string;
  metric_resolution?: {
    alias: string;
    display_name: string;
    column_name: string;
  };
  sources: SourceChip[];
  transparency: TransparencyPayload;
  chart_data?: ChartData;
  stat_updates?: StatUpdate[];
}
```

For `type: "clarification"`, return:

```ts
{
  question: string;
  ambiguous_term: string;
  options: string[];
}
```

### GET `/api/metrics`

Return:

```ts
{
  metrics: MetricEntry[];
}
```

Metric entries must include:

```ts
{
  name: string;
  display_name: string;
  canonical_column: string;
  unit: string;
  description: string;
  aliases: string[];
  ambiguous: boolean;
}
```

### GET `/api/status`

Return:

```ts
{
  snowflake: "live" | "error" | "connecting";
  confluence: "live" | "syncing" | "error";
  salesforce: "live" | "error" | "connecting";
  tavily: "live" | "error";
}
```

## Important Rendering Rules

- `answer.text` may contain `<strong>` tags only. Avoid raw SQL column names in
  user-facing answer text.
- Use `branches` to control visible branch pills and chart availability.
- If `branches` does not include `"sql"`, the frontend clears chart data and
  shows "No chart available for this query".
- `transparency` drives all right-pane verification tabs.
- Empty transparency fields are allowed. The frontend renders the required empty
  state for each tab.
- `trace` entries render in the collapsible trace block. Set
  `highlight: true` for the semantic validator line.
- `sources` supports these `source_type` values:
  - `snowflake`
  - `confluence`
  - `salesforce`
  - `tavily`
  - `upload`
- Snowflake and Salesforce chips should include `confidence` when available.

## Transparency Payload

The frontend supports:

```ts
{
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
```

Structured data tables render best when every row has the same keys.

## Frontend Mock Behavior

When `NEXT_PUBLIC_USE_MOCK=true`:

- `postChat()` returns `MOCK_CLARIFICATION` if the message includes
  `"performance"` and no `clarification_answer` is provided.
- Otherwise `postChat()` returns `MOCK_RESPONSE_1`.
- `getMetrics()` returns `MOCK_METRICS`.
- `getStatus()` returns `MOCK_STATUS`.

Use these mocks as the backend parity target.

## Backend Priority Checklist

1. Implement `/api/status` first so topbar and sidebar connection status works.
2. Implement `/api/metrics` so Metrics Glossary can run without mock mode.
3. Implement `/api/chat` with the exact response envelope.
4. Return complete `transparency` payloads for trust and verification.
5. Return clarification payloads for ambiguous metric terms.
6. Keep user-facing `answer.text` plain-English and jargon-free.
7. Use stable `message_id` values and echo no raw backend errors to the user.
