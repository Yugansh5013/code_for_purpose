# OmniData — Frontend Build Prompt for Codex
**Version:** 1.0  
**Project:** NatWest Code for Purpose Hackathon — Talk to Data  
**Your role:** Build the complete frontend for OmniData, a multi-agent enterprise analytics terminal.  
**Reference implementation:** A working static HTML prototype exists at `omnidata-dashboard.html` in this repo. Use it as a visual reference only. All production code must be built in Next.js as specified below.

---

## 0. Read This First — How to Use This Document

This document is the single source of truth for building the OmniData frontend. It contains:

- **Section 1** — Project context and what OmniData does (read once, understand deeply)
- **Section 2** — Tech stack and file structure you must follow exactly
- **Section 3** — Design system: colours, typography, tokens (reference constantly)
- **Section 4** — Component-by-component build spec (the core of your work)
- **Section 5** — API contract: every endpoint the frontend calls and what it returns
- **Section 6** — State management: what lives in global state vs local state
- **Section 7** — Mock data: use this when the backend is not yet connected
- **Section 8** — Behaviour rules: edge cases, loading states, error states
- **Section 9** — Codex task list: ordered, specific tasks to execute

**When in doubt:** refer to the static prototype for visual intent, and this document for production behaviour.

---

## 1. Project Context

### What OmniData Does

OmniData lets non-technical business users ask questions about enterprise data in plain English and receive accurate, verifiable, jargon-free answers. No SQL. No dashboards to configure. No dependency on a data team.

Under the hood, a LangGraph multi-agent backend:
1. Routes the query to the right data sources (Snowflake SQL, Confluence RAG, Salesforce SOQL, Tavily web)
2. Executes queries, retrieves documents, runs visualisation code in a sandboxed environment
3. Synthesises all outputs into a single plain-English answer
4. Runs a final Semantic Validator pass to strip any remaining technical jargon
5. Returns a structured response payload the frontend renders

**The frontend's job** is to make this pipeline feel like a conversation — transparent, trustworthy, and fast — while exposing every underlying decision for users who want to verify the work.

### The Three Design Pillars (NatWest Judging Criteria)

| Pillar | What the frontend must show |
|---|---|
| **Clarity** | Plain-English answers lead every response. Temporal resolution notes show exactly what date range was used. Metric resolution notes show what alias was interpreted as what. |
| **Trust** | The Transparency Dashboard exposes every SQL query, SOQL query, raw data table, source document excerpt, Python viz code, confidence score breakdown, and semantic validator substitution log. Users can verify every answer. |
| **Speed** | Streaming responses where possible. Skeleton loaders, not spinners. Typing indicator during generation. Branch tags appear immediately, answer streams in. |

---

## 2. Tech Stack & File Structure

### Stack
```
Frontend:   Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
Charts:     Recharts
Icons:      lucide-react
HTTP:       fetch with SWR for polling/caching
State:      Zustand (global), useState/useReducer (local component)
Fonts:      IBM Plex Mono + IBM Plex Sans (Google Fonts)
```

### Required File Structure
```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout: font loading, global providers
│   ├── page.tsx                      # Entry point — renders <Dashboard />
│   ├── globals.css                   # CSS variables, base resets, scrollbar styles
│   └── components/
│       ├── Dashboard.tsx             # Root layout: 3-pane grid
│       ├── Topbar.tsx                # Logo, integration status pills, live clock
│       ├── Sidebar.tsx               # Nav, integration list, recent sessions
│       ├── ChatPane.tsx              # Centre pane: message list + input row
│       ├── MessageList.tsx           # Scrollable message thread
│       ├── MessageItem.tsx           # Single message — user or AI variant
│       ├── ThinkingTrace.tsx         # Collapsible node execution log
│       ├── BranchTags.tsx            # Colour-coded branch pills (SQL/RAG/SOQL/WEB)
│       ├── ResolutionNote.tsx        # Date + metric resolution inline notes
│       ├── SourceChips.tsx           # Integration source chips with confidence dot
│       ├── ClarificationCard.tsx     # Ambiguous metric prompt with option buttons
│       ├── TypingIndicator.tsx       # Animated 3-dot typing indicator
│       ├── InputRow.tsx              # Textarea + send button + hint chips
│       ├── ChartPane.tsx             # Right pane top: stat cards + chart
│       ├── StatCard.tsx              # Individual metric stat card
│       ├── ChartDisplay.tsx          # Recharts wrapper with type toggle
│       ├── TransparencyDashboard.tsx # Right pane bottom: 7-tab panel
│       ├── tabs/
│       │   ├── SqlTab.tsx            # Syntax-highlighted SQL
│       │   ├── SoqlTab.tsx           # Syntax-highlighted SOQL
│       │   ├── DataTab.tsx           # Raw results table
│       │   ├── CodeTab.tsx           # Python viz code block
│       │   ├── ContextTab.tsx        # Confluence + doc excerpts
│       │   ├── ConfidenceTab.tsx     # Three-signal score breakdown
│       │   └── LanguageTab.tsx       # Semantic validator substitution log
│       ├── MetricsGlossary.tsx       # Browsable, searchable metric dictionary
│       └── ConfidenceChip.tsx        # Reusable green/amber/red dot + label
├── lib/
│   ├── store.ts                      # Zustand global state
│   ├── api.ts                        # All fetch calls to backend
│   ├── types.ts                      # All TypeScript types and interfaces
│   ├── mockData.ts                   # Full mock API responses for offline dev
│   └── utils.ts                      # Formatters, colour helpers, date utils
├── public/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── .env.example
```

---

## 3. Design System

### Philosophy
Bloomberg terminal meets enterprise SaaS. Dark, data-dense, monospace-heavy. Every colour carries meaning. No decorative gradients. No rounded-everything. Precision over flair.

### Fonts
```css
/* Load in app/layout.tsx via next/font/google */
IBM Plex Mono — monospace: labels, tags, code, numbers, timestamps, status pills
IBM Plex Sans — sans-serif: body text, AI responses, navigation, descriptions
```

**Rules:**
- All labels, tags, timestamps, column names, numbers in tables → IBM Plex Mono
- All natural language (AI responses, descriptions, nav items) → IBM Plex Sans
- Never use system fonts, Inter, Roboto, or any sans-serif for monospace contexts

### CSS Variables (define in globals.css)
```css
:root {
  --bg-0: #080a0c;       /* page background, deepest */
  --bg-1: #0d0f13;       /* sidebar, topbar, panel backgrounds */
  --bg-2: #111418;       /* hover states, secondary surfaces */
  --bg-3: #161b22;       /* active states, tertiary surfaces */

  --border-0: #1c2230;   /* default border */
  --border-1: #243040;   /* hover/emphasis border */

  --text-0: #dde3ee;     /* primary text */
  --text-1: #8a96a8;     /* secondary text */
  --text-2: #4a5668;     /* muted text, metadata */
  --text-3: #2e3848;     /* very muted, placeholders */

  /* Integration colours */
  --blue:          #3b82f6;
  --blue-dim:      #162032;
  --blue-border:   #1e3a5c;
  --blue-text:     #60a5fa;

  --green:         #22c55e;
  --green-dim:     #0e2018;
  --green-border:  #1a3824;

  --amber:         #f59e0b;
  --amber-dim:     #1c1408;
  --amber-border:  #2e2010;

  --purple:        #a855f7;
  --purple-dim:    #1a0f1a;
  --purple-border: #2a1a2e;

  --red:           #ef4444;
  --red-dim:       #1f0a0a;
  --red-border:    #3a1414;

  --orange:        #fb923c;
  --orange-dim:    #1a100a;
  --orange-border: #2e1c10;
}
```

### Integration Colour Mapping
| Integration | Accent colour | Usage |
|---|---|---|
| Snowflake | `--green` | Source chips, branch tags, SQL tab accent |
| Confluence | `--amber` | Source chips, branch tags, Context tab accent |
| Salesforce | `--blue` / `--blue-text` | Source chips, branch tags, SOQL tab accent |
| Tavily | `--purple` | Source chips, branch tags |
| Uploaded docs | `--orange` | Source chips |

This mapping must be consistent everywhere — branch tags, source chips, transparency tab headers, integration status dots in the sidebar, topbar pills.

### Confidence Colour Mapping
| Score | Colour | Label |
|---|---|---|
| ≥ 0.80 | `--green` | GREEN |
| 0.50 – 0.79 | `--amber` | AMBER |
| < 0.50 | `--red` | RED |

### Spacing & Sizing
```
Topbar height:        38px
Sidebar width:        196px
Right pane width:     310px
Border width:         1px solid var(--border-0)
Border radius:        3px (tags, badges, inputs), 4px (cards, bubbles), 0px (code blocks)
Font size — labels:   8–9px
Font size — body:     13px
Font size — stat val: 17–18px
```

---

## 4. Component Build Specifications

### 4.1 `Dashboard.tsx` — Root Layout
```
Layout: CSS Grid — 3 columns: 196px | 1fr | 310px
Height: 100vh, overflow hidden
Children: <Topbar /> (full width, above grid), <Sidebar />, <ChatPane />, <RightPanel />
```
The grid must never scroll as a whole. Each pane manages its own internal scroll.

---

### 4.2 `Topbar.tsx`
```
Height: 38px
Background: var(--bg-1)
Border-bottom: 1px solid var(--border-0)
Layout: flex, space-between
```

**Left side — Logo:**
```
Text: "OMNIDATA"
Font: IBM Plex Mono, 13px, weight 500
Colour: #e8edf5
The "DATA" portion: colour var(--blue)
Subtitle after logo: "v1.0 · ENTERPRISE ANALYTICS TERMINAL"
Subtitle font: IBM Plex Mono, 9px, colour var(--text-3)
```

**Right side — Status pills + clock:**

Each integration status pill:
```
Layout: flex, align-items center, gap 5px
Font: IBM Plex Mono, 9px, letter-spacing 0.06em, colour var(--text-2)
Dot: 5px × 5px circle, animation: pulse opacity 1→0.35→1 on loop
```

| Pill label | Dot colour | Pulse speed |
|---|---|---|
| SNOWFLAKE LIVE | var(--green) | 2s |
| CONFLUENCE SYNC | var(--amber) | 2.5s |
| SALESFORCE OK | var(--blue) | 3s |
| TAVILY WEB | var(--purple) | no pulse |

**Live clock:**
```
Font: IBM Plex Mono, 10px, colour var(--text-3)
Format: HH:MM:SS (24hr, en-GB locale)
Update: setInterval every 1000ms
```

---

### 4.3 `Sidebar.tsx`
```
Width: 196px
Background: var(--bg-1)
Border-right: 1px solid var(--border-0)
Overflow-y: auto (thin scrollbar, 3px)
```

**Sections (in order, each separated by border-bottom):**

**1. New Session button:**
```
Full width minus 28px horizontal margin
Background: var(--blue-dim), border: var(--blue-border)
Font: IBM Plex Mono, 10px, colour var(--blue), letter-spacing 0.06em
Text: "+ NEW SESSION"
Hover: background #1e3a5c
```

**2. Navigation:**
Section label: "NAVIGATION" — IBM Plex Mono, 8px, colour var(--text-3), letter-spacing 0.14em, uppercase

Nav items:
```
Height: ~32px, padding: 7px 14px
Layout: flex, align-items center, gap 8px
Font: IBM Plex Sans, 12px, colour var(--text-1)
Left border: 2px solid transparent (default), var(--blue) when active
Background: var(--bg-2) when active or hover
Active text colour: #e8edf5
Icon: 13×13px SVG, opacity 0.55
```

Nav items (in order):
- Chat (message bubble icon) — default active
- Agents (person icon)
- History (clock icon)
- Metrics Glossary (document icon)
- Profile (person icon)

Clicking "Metrics Glossary" replaces the chat view in the centre pane with `<MetricsGlossary />`. All other nav items show the chat view.

**3. Integrations:**
Section label: "INTEGRATIONS"

Each row:
```
Padding: 5px 14px
Layout: flex, space-between
Left: dot (5px) + integration name (IBM Plex Sans, 11px, var(--text-1))
Right: badge (IBM Plex Mono, 8px, 2px 5px padding, 2px border-radius)
```

| Integration | Dot colour | Badge text | Badge bg / text colour |
|---|---|---|---|
| Snowflake | green | LIVE | green-dim / green |
| Confluence | amber | SYNC | amber-dim / amber |
| Salesforce | blue | OK | blue-dim / blue-text |
| Tavily | purple | WEB | purple-dim / purple |

**4. Recent Sessions:**
Section label: "RECENT SESSIONS"

Items: IBM Plex Mono, 10px, colour var(--text-2), 6px 14px padding, truncated with ellipsis
Hover: colour var(--text-1), background var(--bg-2)
Clicking a recent item: pre-fills the input textarea with the query text

---

### 4.4 `ChatPane.tsx` — Centre Pane
```
Layout: flex column, flex:1, overflow hidden
Children (top to bottom):
  1. <MessageList /> — flex:1, overflow-y auto
  2. <HintBar />     — flex-shrink 0 (optional quick-query chips)
  3. <InputRow />    — flex-shrink 0
```

When "Metrics Glossary" is active in nav: hide `<MessageList />`, `<HintBar />`, `<InputRow />` and show `<MetricsGlossary />` instead.

---

### 4.5 `MessageList.tsx`
```
Flex column, gap 14px, padding 14px 16px
Overflow-y: auto, scroll to bottom on new message
Thin scrollbar (3px)
```

Each message: rendered by `<MessageItem type="user"|"ai" message={...} />`

After submitting a query, immediately show `<TypingIndicator />` as the last item. Replace it with the AI `<MessageItem />` when the response arrives.

---

### 4.6 `MessageItem.tsx`

**User message:**
```
Align: flex-end (right-align)
Max-width: 78%
Bubble: background var(--blue-dim), border var(--blue-border), colour #c8d8f0
Padding: 9px 13px
Border-radius: 8px 8px 2px 8px
Font: IBM Plex Sans, 13px, line-height 1.55
```

**AI message — full structure (top to bottom):**

```
1. Top meta row (flex, space-between):
   Left: <BranchTags branches={message.branches} />
   Right: <ThinkingTrace trace={message.trace} /> — collapsible

2. <ThinkingTrace /> expanded content (hidden by default)

3. <ResolutionNote /> — if message.date_resolution or message.metric_resolution

4. Answer bubble:
   Background: var(--bg-1)
   Border: 1px solid var(--border-0)
   Border-radius: 4px
   Padding: 12px 14px
   Font: IBM Plex Sans, 13px, colour var(--text-0), line-height 1.65
   Bold terms: colour #e8edf5, font-weight 500

5. <SourceChips chips={message.sources} /> — below bubble
```

---

### 4.7 `ThinkingTrace.tsx`
```
Trigger: "▾ TRACE" button (IBM Plex Mono, 9px, var(--text-3))
Toggle: click shows/hides the trace block, label changes to "▴ TRACE"
Button position: right side of the top meta row
```

Trace block when expanded:
```
Background: var(--bg-0)
Border: 1px solid var(--border-0)
Border-radius: 3px
Padding: 10px 12px
Font: IBM Plex Mono, 10px, line-height 1.9
```

Each trace line format:
```
→ [node_name]:  [description]
```
Node name colour: var(--text-1)
Description colour: var(--text-3)
Special: semantic_validator line uses var(--green) for both

Example lines to render (populated from API response `trace` array):
```
→ intent_router:    sql_likely=true, rag_present=true
→ temporal_resolver: "last month" → 2026-03-01 to 2026-03-31
→ metric_resolver:  "return rates" → RETURN_RATE (unambiguous)
→ e2b_sandbox:      pre-warmed (sql_likely=true, async)
→ branch_sql:       schema_rag → sql_gen → sqlglot_validate → execute
→ branch_rag:       confluence_search → 3 chunks [score: 0.89]
→ branch_soql:      sf_schema_rag → soql_gen → validate → execute
→ synthesis_node:   merging 3 branch outputs → jargon audit
→ semantic_validator: rag_present=true → 2 terms rewritten
```

---

### 4.8 `BranchTags.tsx`
```
Layout: flex, gap 5px, flex-wrap wrap
```

Each tag:
```
Font: IBM Plex Mono, 9px, letter-spacing 0.04em
Padding: 2px 7px
Border-radius: 2px
Border: 1px solid (integration colour border variable)
```

| Branch key | Display text | Colours |
|---|---|---|
| `sql` | SQL · SNOWFLAKE | green-dim bg, green text, green-border |
| `rag_confluence` | RAG · CONFLUENCE | amber-dim bg, amber text, amber-border |
| `rag_salesforce` | SOQL · SALESFORCE | blue-dim bg, blue-text text, blue-border |
| `web` | WEB · TAVILY | purple-dim bg, purple text, purple-border |

---

### 4.9 `ResolutionNote.tsx`
```
Font: IBM Plex Mono, 10px, colour var(--text-3), letter-spacing 0.02em
Margin: 3px 0
```

Two variants:

**Date resolution:**
```
Resolved "last month" → 2026-03-01 to 2026-03-31
```
Original phrase in quotes, resolved value in plain text.

**Metric resolution:**
```
Interpreting [alias] as [display_name] [COLUMN_NAME badge]
```
Alias in italic (var(--text-2)), display_name in italic.
Column name badge: IBM Plex Mono, 8px, blue-dim bg, blue-text colour, blue-border, 1px 5px padding.

---

### 4.10 `SourceChips.tsx`
```
Layout: flex, gap 5px, flex-wrap wrap, margin-top 8px
```

Each chip:
```
Layout: flex, align-items center, gap 4px
Padding: 3px 7px
Border-radius: 3px
Border: 1px solid (integration border colour)
Font: IBM Plex Mono, 8px, letter-spacing 0.04em
```

**Chip variants:**

| source_type | bg | text | border | Shows confidence dot? |
|---|---|---|---|---|
| `snowflake` | green-dim | green | green-border | Yes |
| `confluence` | amber-dim | amber | amber-border | No |
| `salesforce` | blue-dim | blue-text | blue-border | Yes |
| `tavily` | purple-dim | purple | purple-border | No |
| `upload` | orange-dim | orange | orange-border | No |

**Confidence dot** (only on snowflake and salesforce chips):
```
Size: 5px × 5px circle
Colour: based on confidence score (green ≥0.8, amber 0.5–0.79, red <0.5)
Position: left of chip text
```

Chip label format: `[Integration name] · [table/object name]`
Example: `Snowflake · AURA_SALES`, `Confluence · Refund Policy`

---

### 4.11 `ClarificationCard.tsx`
Shown when `message.type === "clarification"` — Node 1 detected an ambiguous metric.

```
Background: var(--bg-1)
Border: 1px solid var(--blue-border)
Border-radius: 4px
Padding: 12px 14px
```

Question text:
```
Font: IBM Plex Sans, 12px, colour #c8d8f0
The ambiguous term: bold, colour var(--blue-text)
```

Option buttons:
```
Layout: flex, gap 7px, flex-wrap wrap
Each button: padding 5px 12px, blue-dim bg, blue-border, 3px border-radius
Font: IBM Plex Mono, 9px, blue-text colour, letter-spacing 0.04em
Hover: background #1e3a5c
```

On button click:
- Add a user message with the selection
- Send `POST /api/chat` with `{ session_id, clarification_answer: selectedOption }`

---

### 4.12 `InputRow.tsx`
```
Padding: 10px 14px
Border-top: 1px solid var(--border-0)
Background: var(--bg-1)
Layout: flex, gap 8px, align-items flex-end
```

**Textarea:**
```
Background: var(--bg-0)
Border: 1px solid var(--border-0)
Border-radius: 4px
Padding: 9px 12px
Font: IBM Plex Sans, 13px, colour var(--text-0)
Placeholder: "Ask your data in plain English...", colour var(--text-3)
Min-height: 38px, max-height: 110px
Auto-resize on input (adjust scrollHeight)
Focus: border-color var(--blue-border)
On Enter (no Shift): submit. On Shift+Enter: new line.
```

**Send button:**
```
Size: 35×35px
Background: var(--blue-dim), border: var(--blue-border), border-radius: 3px
Icon: right-arrow SVG, colour var(--blue-text), 13px
Hover: background #1e3a5c
Disabled when input is empty or request is in-flight
```

**Hint chips (above input row):**
```
Chips: "Revenue by region", "Churn risk accounts", "YTD sales vs target",
       "Refund policy summary", "Upload a CSV"
Font: IBM Plex Mono, 9px, colour var(--text-2), letter-spacing 0.04em
Background: var(--bg-2), border: var(--border-0), border-radius: 2px, padding: 3px 9px
On click: pre-fill the textarea with the chip text
```

---

### 4.13 `ChartPane.tsx` — Right Pane Top
```
Flex: 1 (takes remaining height above the transparency dashboard)
Border-bottom: 1px solid var(--border-0)
Layout: flex column
```

**Panel header:**
```
Height: 32px, padding 7px 12px
Border-bottom: 1px solid var(--border-0)
Left: "VISUAL CONTEXT" label (IBM Plex Mono, 8px, var(--text-3), uppercase, letter-spacing 0.14em)
Right: chart type toggle buttons (BAR | LINE | DONUT)
```

Chart type toggle buttons:
```
Font: IBM Plex Mono, 8px, letter-spacing 0.06em
Padding: 2px 7px, border: 1px solid var(--border-0), border-radius: 2px
Default: transparent bg, var(--text-2)
Active: var(--bg-3), var(--text-0), border-color var(--border-1)
```

**Stat cards row:**
```
Display: grid, 3 columns equal width, gap 8px
Padding: 10px 12px 6px
Flex-shrink: 0
```

Each `<StatCard />`:
```
Background: var(--bg-0), border: var(--border-0), border-radius: 3px, padding: 9px
Label: IBM Plex Mono, 8px, var(--text-3), uppercase, letter-spacing 0.1em
Value: IBM Plex Mono, 17px, weight 500, #e8edf5
Delta: IBM Plex Mono, 9px — red for negative (▼), green for positive (▲)
```

Initial stat cards (update dynamically from last AI response):
- Return Rate / 4.2% / ▲ +1.4pp QoQ (red delta)
- Q1 Total Sales / £3.8M / ▼ −11% (red delta)
- High-Risk Accts / 3 / ▲ 2 new (red delta)

**Chart area:**
```
Flex: 1, padding: 8px 12px, min-height 0
Chart: Recharts BarChart / LineChart / PieChart based on toggle
Chart background: transparent (inherits var(--bg-1))
Grid lines: var(--border-0) colour, no border on axes
Axis tick font: IBM Plex Mono, 9px, colour var(--text-2)
Tooltip: dark themed (bg var(--bg-0), border var(--border-0), mono font)
```

Chart data (static mock until backend connected):
```
North: £1,420K
East:  £840K
West:  £560K
South: £980K (highlight red — highest return rate)
```

Bar colours: green for North (best performer), blue for East/West (neutral), red for South (worst).

When last response is RAG-only or web-only (no SQL branch): show "No chart available for this query" placeholder text in the chart area.

---

### 4.14 `TransparencyDashboard.tsx` — Right Pane Bottom
```
Height: 268px, flex-shrink: 0
Layout: flex column
```

**7 tabs — always visible, conditionally populated:**

| Tab | Label | Show content when | Empty state |
|---|---|---|---|
| SQL | SQL | Branch 1 (sql) fired | "No SQL query for this response" |
| SOQL | SOQL | Branch 2B (rag_salesforce) fired | "No SOQL query for this response" |
| Data | DATA | Branch 1 or 2B fired | "No structured data for this response" |
| Code | CODE | Branch 1 with chart | "No visualisation code for this response" |
| Context | CONTEXT | Branch 2A (rag_confluence) fired | "No document context for this response" |
| Confidence | CONF. | Branch 1 or 2B fired | "No confidence data for this response" |
| Language | LANGUAGE | Node 3 fired (rag_present=true) | "No jargon detected — response is clean." |

Tab styling:
```
Font: IBM Plex Mono, 8px, letter-spacing 0.08em
Padding: 8px 9px
Default: var(--text-3)
Hover: var(--text-2)
Active: var(--blue-text), border-bottom 1.5px solid var(--blue)
Tabs row: overflow-x auto, no scrollbar visible (hide with CSS)
```

---

### 4.15 Tab Content Components

#### `SqlTab.tsx`
Syntax-highlighted SQL code block.
```
Font: IBM Plex Mono, 10px, line-height 1.75
Background: none (inherits)
White-space: pre, overflow-x: auto
Colour tokens:
  Keywords (SELECT, FROM, WHERE, GROUP BY, ORDER BY, BETWEEN, AND, LIMIT): var(--blue-text)
  Table names (fully qualified): var(--green)
  String literals ('2026-01-01'): var(--amber)
  Functions (SUM, AVG, COUNT): var(--purple)
  Comments, aliases: var(--text-2)
  Default text: var(--text-1)
```

Implement syntax highlighting as a simple token-based regex highlighter (no external library needed for this scope). Wrap matched tokens in `<span>` with appropriate colour classes.

#### `SoqlTab.tsx`
Same layout and colour system as SqlTab. Salesforce-specific keywords: `SELECT`, `FROM`, `WHERE`, `ORDER BY`, `LIMIT`, `AND`. Object names (Account, Opportunity): use var(--blue-text). Custom fields ending in `__c`: var(--amber).

#### `DataTab.tsx`
```
Table: width 100%, border-collapse collapse
Font: IBM Plex Mono, 10px
Header: var(--text-3), 9px, uppercase, border-bottom var(--border-0)
Cells: padding 4px 8px, border-bottom #111418
Numeric cells: text-align right, colour var(--text-0), font-weight 500
Positive delta cells: var(--green)
Negative delta cells: var(--red)
```

#### `CodeTab.tsx`
Same monospace code block style as SqlTab. Python keyword colour: var(--blue-text). String literals: var(--amber). Function names: var(--purple).

#### `ContextTab.tsx`
Each source document excerpt:
```
Padding: 8px 0, border-bottom: var(--border-0)

Title row:
  Integration badge (matching sidebar badge style) + page/document title
  Font: IBM Plex Sans, 11px, weight 500, colour var(--text-0)

Body:
  Font: IBM Plex Sans, 10px, colour var(--text-1), line-height 1.6

Metadata:
  Font: IBM Plex Mono, 9px, colour var(--text-3)
  Format: "[SPACE_KEY] · Updated [date] · chunk [n] of [total] · score: [0.xx]"
```

#### `ConfidenceTab.tsx`
```
Overall score: IBM Plex Mono, 11px, colour matching tier (green/amber/red)
Format: "● CONFIDENCE: [score] — [TIER]"

Three signal rows:
  Label:   IBM Plex Sans, 10px, var(--text-1), width 110px
  Bar:     flex:1, height 2px, background var(--border-0), filled portion in tier colour
  Value:   IBM Plex Mono, 9px, tier colour, width 30px, text-align right

Explanation note:
  IBM Plex Mono, 10px, var(--text-3), margin-top 6px, line-height 1.6
  Shows: "Strong schema match · 0 retries needed · non-empty result returned"
  Shows weighted formula: (signal1×0.4) + (signal2×0.4) + (signal3×0.2) = [total]
```

#### `LanguageTab.tsx`
When substitutions exist:
```
Header: IBM Plex Mono, 8px, var(--text-3), letter-spacing 0.1em
Format: "[N] TERMS REWRITTEN BY SEMANTIC VALIDATOR · NODE 3"

Each substitution row:
  Background: var(--bg-0), border var(--border-0), border-radius 3px, padding 5px 8px, margin-bottom 5px
  Layout: flex, align-items center, gap 7px
  Original term:  IBM Plex Mono, 10px, var(--red), text-decoration line-through
  Arrow:          IBM Plex Mono, var(--text-3)
  Replacement:    IBM Plex Mono, 10px, var(--green)
  Location:       IBM Plex Mono, 8px, var(--text-3), margin-left auto

Validation status line:
  IBM Plex Mono, 10px, var(--bg-0) bg, border, padding 5px 8px
  Content: "validation_passed: true · model: llama-3.3-8b · latency: [n]ms"
```

When no substitutions:
```
"No technical terms found — response is clean." in var(--text-3)
```

---

### 4.16 `MetricsGlossary.tsx`
Shown in the centre pane when "Metrics Glossary" is selected in nav.

```
Layout: flex column, flex:1, overflow hidden
```

**Search bar:**
```
Width: calc(100% - 24px), margin: 12px
Background: var(--bg-0), border: var(--border-0), border-radius 3px
Font: IBM Plex Mono, 11px, colour var(--text-0)
Placeholder: "Search metrics..."
Focus: border var(--blue-border)
Filter: live filter on metric name and aliases as user types
```

**Metric list:**
```
Overflow-y: auto, padding 0 14px 12px
Each item: border-bottom var(--border-0), padding 8px 0
```

Each metric entry:
```
Name: IBM Plex Mono, 10px, weight 500, var(--text-0) + unit in brackets (var(--text-3))
Column: IBM Plex Mono, 9px, var(--blue-text), prefix "→ "
Description: IBM Plex Sans, 10px, var(--text-2), line-height 1.5
Aliases: IBM Plex Mono, 9px, var(--text-3), prefix "aliases: "
```

Metric dictionary entries to include:
```
Total Sales       | ACTUAL_SALES        | GBP   | money, income, earnings, revenue, turnover
Return Rate       | RETURN_RATE         | %     | returns, refund rate, reversal rate
Customer Churn    | CHURN_FLAG          | count | lost customers, attrition, cancellations
Active Customers  | IS_ACTIVE           | count | DAU, MAU, engaged users
Pipeline Value    | Opportunity.Amount  | GBP   | deals, opportunities, potential revenue
Transaction Volume| TXN_COUNT           | count | txn count, transactions, digital volume
Unit Sales        | UNITS_SOLD          | count | units, items sold, quantity
```

---

## 5. API Contract

All requests go to `NEXT_PUBLIC_API_URL` (set in `.env`). In development, this is `http://localhost:8000`.

### `POST /api/chat`

**Request:**
```typescript
{
  session_id: string;           // UUID, generated client-side per session
  message: string;              // User's natural language query
  clarification_answer?: string; // Only when responding to a ClarificationCard
}
```

**Response:**
```typescript
{
  message_id: string;
  type: "answer" | "clarification";

  // Present when type === "answer"
  answer?: {
    text: string;                  // Plain-English answer (HTML allowed for <strong>)
    branches: BranchKey[];         // ["sql", "rag_confluence", "rag_salesforce", "web"]
    trace: TraceEntry[];           // Array of node execution log entries
    date_resolution?: string;      // e.g. '"last month" → 2026-03-01 to 2026-03-31'
    metric_resolution?: {
      alias: string;
      display_name: string;
      column_name: string;
    };
    sources: SourceChip[];
    transparency: TransparencyPayload;
    chart_data?: ChartData;        // null if no SQL branch
    stat_updates?: StatUpdate[];   // New values for the 3 stat cards
  };

  // Present when type === "clarification"
  clarification?: {
    question: string;
    ambiguous_term: string;
    options: string[];
  };
}
```

**Supporting types:**
```typescript
type BranchKey = "sql" | "rag_confluence" | "rag_salesforce" | "web";

interface TraceEntry {
  node: string;       // e.g. "intent_router"
  detail: string;     // e.g. "sql_likely=true, rag_present=true"
  highlight?: boolean; // true for semantic_validator (renders green)
}

interface SourceChip {
  source_type: "snowflake" | "confluence" | "salesforce" | "tavily" | "upload";
  label: string;       // e.g. "AURA_SALES" or "Refund Policy"
  confidence?: number; // 0–1, only for snowflake and salesforce
}

interface TransparencyPayload {
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

interface ContextChunk {
  source_type: "confluence" | "upload";
  title: string;
  space_key?: string;
  body: string;
  updated_at: string;
  chunk_index: number;
  total_chunks: number;
  score: number;
}

interface ConfidenceScore {
  score: number;         // blended 0–1
  tier: "green" | "amber" | "red";
  signals: {
    schema_cosine: number;   // weight 0.4
    retry_score: number;     // weight 0.4 (1.0=0 retries, 0.5=1, 0=2)
    row_sanity: number;      // weight 0.2
  };
  explanation: string;
}

interface SemanticSubstitution {
  original: string;
  replaced_with: string;
  location: string;      // e.g. "paragraph 2"
}

interface ChartData {
  type: "bar" | "line" | "doughnut";
  labels: string[];
  values: number[];
  colours?: string[];    // Optional override; frontend uses integration colours if absent
  y_label?: string;
}

interface StatUpdate {
  label: string;
  value: string;
  delta: string;
  delta_direction: "pos" | "neg" | "neutral";
}
```

### `GET /api/metrics`
Returns the full Metric Dictionary for the Glossary view.

**Response:**
```typescript
{
  metrics: MetricEntry[];
}

interface MetricEntry {
  name: string;
  display_name: string;
  canonical_column: string;
  unit: string;
  description: string;
  aliases: string[];
  ambiguous: boolean;
}
```

### `GET /api/status`
Returns integration connection status for the topbar and sidebar dots.

**Response:**
```typescript
{
  snowflake: "live" | "error" | "connecting";
  confluence: "live" | "syncing" | "error";
  salesforce: "live" | "error" | "connecting";
  tavily: "live" | "error";
}
```

---

## 6. State Management (Zustand)

### Global store — `lib/store.ts`

```typescript
interface OmniDataStore {
  // Session
  sessionId: string;               // UUID, initialised on mount
  
  // Messages
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;

  // Pending state
  isLoading: boolean;
  setLoading: (v: boolean) => void;

  // Active transparency data (from last AI response)
  activeTransparency: TransparencyPayload | null;
  setActiveTransparency: (t: TransparencyPayload | null) => void;

  // Active chart data
  activeChartData: ChartData | null;
  setActiveChartData: (c: ChartData | null) => void;

  // Active stat cards
  activeStats: StatUpdate[];
  setActiveStats: (s: StatUpdate[]) => void;

  // Integration status
  integrationStatus: IntegrationStatus;
  setIntegrationStatus: (s: IntegrationStatus) => void;

  // Nav
  activeNav: "chat" | "agents" | "history" | "glossary" | "profile";
  setActiveNav: (n: ActiveNav) => void;
}

interface Message {
  id: string;
  role: "user" | "ai" | "clarification";
  content: string;                  // For user messages
  answer?: AnswerPayload;           // For AI messages
  clarification?: ClarificationPayload;
  timestamp: Date;
}
```

**What lives locally (useState):**
- Active transparency tab selection (SqlTab, DataTab, etc.)
- Chart type toggle (bar/line/doughnut)
- ThinkingTrace open/closed state per message
- Glossary search filter text
- Textarea value and height

---

## 7. Mock Data

Use this when the backend is not yet running. Import from `lib/mockData.ts` and return it from `lib/api.ts` when `process.env.NEXT_PUBLIC_USE_MOCK === "true"`.

```typescript
// lib/mockData.ts

export const MOCK_RESPONSE_1 = {
  message_id: "msg-001",
  type: "answer",
  answer: {
    text: "Your refund policy sets a <strong>30-day window</strong> for standard returns and <strong>90 days</strong> for enterprise accounts. In Q1 2026, your <strong>Return Rate</strong> reached <strong>4.2%</strong> — up from 2.8% in Q4 2025. The South Region drove the majority of returns (+22%), correlating with delayed shipments in your Operations runbook. Three enterprise accounts in Salesforce exceed the 90-day policy threshold.",
    branches: ["sql", "rag_confluence", "rag_salesforce"],
    trace: [
      { node: "intent_router", detail: "sql_likely=true, rag_present=true" },
      { node: "temporal_resolver", detail: "no date phrase detected" },
      { node: "metric_resolver", detail: '"return rates" → RETURN_RATE (unambiguous)' },
      { node: "e2b_sandbox", detail: "pre-warmed (sql_likely=true, async)" },
      { node: "branch_sql", detail: "schema_rag → sql_gen → sqlglot_validate → execute" },
      { node: "branch_rag", detail: "confluence_search → 3 chunks [score: 0.89]" },
      { node: "branch_soql", detail: "sf_schema_rag → soql_gen → validate → execute" },
      { node: "synthesis_node", detail: "merging 3 branch outputs → jargon audit" },
      { node: "semantic_validator", detail: "rag_present=true → 2 terms rewritten", highlight: true },
    ],
    metric_resolution: {
      alias: "return rates",
      display_name: "Return Rate (%)",
      column_name: "RETURN_RATE",
    },
    sources: [
      { source_type: "snowflake", label: "AURA_SALES", confidence: 0.87 },
      { source_type: "confluence", label: "Refund Policy" },
      { source_type: "salesforce", label: "Accounts", confidence: 0.81 },
    ],
    transparency: {
      sql: `SELECT\n  geo_territory,\n  SUM(actual_sales) AS total_sales,\n  AVG(return_rate) AS avg_return_rate\nFROM\n  OMNIDATA_DB.SALES.AURA_SALES\nWHERE\n  sale_date BETWEEN '2026-01-01' AND '2026-03-31'\nGROUP BY geo_territory\nORDER BY total_sales DESC;`,
      soql: `SELECT\n  Id, Name, AnnualRevenue,\n  ChurnRisk__c, ReturnRate__c\nFROM Account\nWHERE\n  ReturnRate__c > 0.05\n  AND Type = 'Enterprise'\nORDER BY ChurnRisk__c DESC\nLIMIT 10;`,
      raw_data: [
        { geo_territory: "North", total_sales: 1420000, avg_return_rate: 0.021, delta: "-0.3pp" },
        { geo_territory: "South", total_sales: 980000,  avg_return_rate: 0.078, delta: "+4.2pp" },
        { geo_territory: "East",  total_sales: 840000,  avg_return_rate: 0.034, delta: "+0.8pp" },
        { geo_territory: "West",  total_sales: 560000,  avg_return_rate: 0.029, delta: "-0.1pp" },
      ],
      python_code: `import matplotlib.pyplot as plt\nimport pandas as pd\n\ndf = pd.DataFrame(results)\nfig, ax = plt.subplots(figsize=(6, 4))\ncolors = ['#22c55e', '#ef4444', '#3b82f6', '#3b82f6']\nax.barh(df['geo_territory'], df['total_sales'], color=colors, height=0.6)\nax.set_facecolor('#080a0c')\nfig.patch.set_facecolor('#080a0c')\nplt.tight_layout()\nplt.savefig('chart.png', dpi=150)`,
      context_chunks: [
        {
          source_type: "confluence",
          title: "Enterprise Customer Refund Policy",
          space_key: "CUSTOPS",
          body: "Enterprise accounts are eligible for returns within 90 calendar days of purchase date, subject to account manager approval for values exceeding £50K.",
          updated_at: "2026-03-14",
          chunk_index: 2,
          total_chunks: 5,
          score: 0.91,
        },
        {
          source_type: "confluence",
          title: "Operations Runbook — South Region",
          space_key: "OPS",
          body: "Delayed shipment events exceeding 5 business days in the South Region must be escalated to the logistics team. Return rates above 5% trigger an automatic review workflow.",
          updated_at: "2026-02-28",
          chunk_index: 1,
          total_chunks: 3,
          score: 0.83,
        },
      ],
      confidence: {
        score: 0.87,
        tier: "green",
        signals: { schema_cosine: 0.92, retry_score: 1.0, row_sanity: 0.75 },
        explanation: "Strong schema match · 0 retries needed · non-empty result returned",
      },
      semantic_substitutions: [
        { original: "ChurnRisk__c", replaced_with: "Churn Risk Score", location: "paragraph 2" },
        { original: "IS_ACTIVE = 1", replaced_with: "active customers", location: "bullet 3" },
      ],
      validation_passed: true,
      validator_model: "llama-3.3-8b",
      validator_latency_ms: 312,
    },
    chart_data: {
      type: "bar",
      labels: ["North", "East", "West", "South"],
      values: [1420, 840, 560, 980],
      colours: ["#22c55e", "#3b82f6", "#3b82f6", "#ef4444"],
      y_label: "Total Sales (£K)",
    },
    stat_updates: [
      { label: "Return Rate", value: "4.2%", delta: "▲ +1.4pp QoQ", delta_direction: "neg" },
      { label: "Q1 Total Sales", value: "£3.8M", delta: "▼ −11%", delta_direction: "neg" },
      { label: "High-Risk Accts", value: "3", delta: "▲ 2 new", delta_direction: "neg" },
    ],
  },
};

export const MOCK_CLARIFICATION = {
  message_id: "msg-002",
  type: "clarification",
  clarification: {
    question: 'Which metric did you mean by "performance"? This term maps to multiple metrics.',
    ambiguous_term: "performance",
    options: ["Total Sales (GBP)", "Units Sold", "Customer Count"],
  },
};

export const MOCK_METRICS = {
  metrics: [
    { name: "Total Sales", display_name: "Total Sales", canonical_column: "ACTUAL_SALES", unit: "GBP", description: "Total transaction value before returns or adjustments.", aliases: ["money", "income", "earnings", "revenue", "turnover"], ambiguous: false },
    { name: "Return Rate", display_name: "Return Rate (%)", canonical_column: "RETURN_RATE", unit: "%", description: "Percentage of transactions resulting in a return within the policy window.", aliases: ["returns", "refund rate", "reversal rate"], ambiguous: false },
    { name: "Customer Churn", display_name: "Customer Churn", canonical_column: "CHURN_FLAG", unit: "count / rate", description: "Customers who did not renew or cancelled in the measurement period.", aliases: ["lost customers", "attrition", "cancellations", "drop-off"], ambiguous: false },
    { name: "Active Customers", display_name: "Active Customers", canonical_column: "IS_ACTIVE", unit: "count", description: "Customers with at least one transaction or login in the period.", aliases: ["DAU", "MAU", "engaged users", "active users"], ambiguous: false },
    { name: "Sales Pipeline Value", display_name: "Sales Pipeline Value", canonical_column: "Opportunity.Amount", unit: "GBP", description: "Total value of open Salesforce Opportunities not yet closed.", aliases: ["deals", "opportunities", "potential revenue", "open deals"], ambiguous: false },
    { name: "Transaction Volume", display_name: "Transaction Volume", canonical_column: "TXN_COUNT", unit: "count", description: "Total number of digital transactions processed in the period.", aliases: ["txn count", "transactions", "digital volume"], ambiguous: false },
    { name: "Unit Sales", display_name: "Unit Sales", canonical_column: "UNITS_SOLD", unit: "count", description: "Number of individual product units sold in the period.", aliases: ["units", "items sold", "quantity sold"], ambiguous: false },
  ],
};
```

---

## 8. Behaviour Rules

### Loading States
- On query submit: immediately append the user message, then show `<TypingIndicator />` at the bottom of the message list.
- Do not disable the input while loading (allow the user to type their next query).
- Do disable the send button while a request is in-flight.
- On response arrival: remove `<TypingIndicator />`, append the AI message with a fade-in animation (`opacity 0 → 1, translateY 5px → 0` over 250ms).

### Error States
- If `POST /api/chat` returns a non-200: append an AI message with an error bubble.
- Error bubble: same style as AI bubble but border-color var(--red-border), text: "Something went wrong. Please try again."
- Do not expose raw error messages to the user.
- Log the full error to `console.error`.

### Empty States
- If a Transparency tab has no data for the current response: show the empty state text from Section 4.14, centred, IBM Plex Mono, 10px, var(--text-3).
- If the chart has no data: show "No chart available for this query" in the chart area.
- If stat cards have no update: keep the previous values (do not reset to zero).

### Scroll Behaviour
- Message list: always auto-scroll to bottom on new message. Never auto-scroll if the user has manually scrolled up.
- Transparency dashboard tab content: scroll independently, does not affect message list.

### Responsive Behaviour
The layout is designed for a 1280px+ viewport (desktop / laptop). On smaller viewports, it is acceptable to show a "Please use a wider screen" message. Do not attempt mobile layout — this is an enterprise tool.

### New Session
- Clicking "+ NEW SESSION": generate a new UUID for `sessionId`, clear `messages`, clear `activeTransparency`, `activeChartData`, `activeStats`.
- Add a session separator message: `"— NEW SESSION · [HH:MM:SS] —"` in monospace, muted, centred.

---

## 9. Codex Task List

Execute these tasks in order. Each task is self-contained. Do not proceed to the next task until the current one builds without TypeScript errors.

```
Task 01 — Project bootstrap
  Create Next.js 14 app with TypeScript, Tailwind CSS, shadcn/ui.
  Install: zustand, recharts, lucide-react.
  Configure Google Fonts: IBM Plex Mono + IBM Plex Sans in app/layout.tsx.
  Set up globals.css with all CSS variables from Section 3.

Task 02 — Types
  Create lib/types.ts with all interfaces from Section 5.
  Create lib/mockData.ts with all mock data from Section 7.
  Create lib/utils.ts with: formatCurrency(), formatDelta(), confidenceTier(), branchColour().

Task 03 — Zustand store
  Create lib/store.ts with the full store from Section 6.
  Initialise sessionId as a UUID on store creation.

Task 04 — API layer
  Create lib/api.ts.
  Implement postChat(), getMetrics(), getStatus().
  When NEXT_PUBLIC_USE_MOCK=true, return mock data instead of fetching.

Task 05 — Dashboard layout
  Build app/page.tsx → renders <Dashboard />.
  Build Dashboard.tsx: 3-column grid + topbar. Confirm layout renders.

Task 06 — Topbar
  Build Topbar.tsx: logo, 4 status pills, live clock.
  Fetch /api/status on mount, update dot colours accordingly.

Task 07 — Sidebar
  Build Sidebar.tsx: new session button, nav items, integrations, recent sessions.
  Wire nav clicks to store.setActiveNav().
  Wire new session button to store.clearMessages() + new UUID.

Task 08 — Input row
  Build InputRow.tsx: textarea (auto-resize, Enter to submit), send button, hint chips.
  Wire submit to store.setLoading(true) + api.postChat() + store.addMessage().

Task 09 — Typing indicator
  Build TypingIndicator.tsx: 3 animated dots.
  Show when store.isLoading === true, hide on response.

Task 10 — Message rendering
  Build MessageList.tsx: scrollable list, auto-scroll behaviour from Section 8.
  Build MessageItem.tsx: user and AI variants.
  User variant: blue bubble, right-aligned.
  AI variant: branch tags row, thinking trace toggle, resolution note, answer bubble, source chips.

Task 11 — Branch tags
  Build BranchTags.tsx using the colour mapping from Section 4.8.

Task 12 — Thinking trace
  Build ThinkingTrace.tsx: collapsed by default, click to expand, trace lines with colour rules.

Task 13 — Resolution notes
  Build ResolutionNote.tsx: date variant and metric variant with column name badge.

Task 14 — Source chips
  Build SourceChips.tsx: colour-coded chips, confidence dot logic, label format.

Task 15 — Clarification card
  Build ClarificationCard.tsx: question, option buttons, click handler that calls api.postChat() with clarification_answer.

Task 16 — Metrics Glossary
  Build MetricsGlossary.tsx: search bar, filtered metric list.
  Fetch /api/metrics on mount. Show in centre pane when nav === 'glossary'.

Task 17 — Chart pane
  Build ChartPane.tsx: panel header + type toggle.
  Build StatCard.tsx.
  Build ChartDisplay.tsx using Recharts. Implement bar, line, doughnut modes.
  Wire chart data to store.activeChartData.

Task 18 — Transparency dashboard
  Build TransparencyDashboard.tsx: 7-tab panel.
  Build all 7 tab components from Section 4.15.
  Wire to store.activeTransparency. Show empty states per Section 4.14.

Task 19 — SQL syntax highlighter
  Implement token-based regex highlighter in lib/utils.ts: highlightSql(), highlightSoql(), highlightPython().
  Used by SqlTab, SoqlTab, CodeTab.

Task 20 — End-to-end wiring
  Ensure that on each AI response:
    - store.activeTransparency updates → TransparencyDashboard re-renders
    - store.activeChartData updates → ChartDisplay re-renders
    - store.activeStats updates → StatCards re-render
  Test with MOCK data: submit a query, confirm all panes update correctly.

Task 21 — Polish
  Fade-in animation on new AI messages (Section 8).
  Scrollbar styles (3px, bg var(--border-0)).
  Disable send button while loading.
  Empty states for all tabs.
  "No chart available" state.
  Verify all font usages: mono vs sans.
  Verify all colour usages match integration mapping.
  Responsive guard: show message if viewport < 1100px.
```

---

## 10. Environment Variables

Create `.env.example`:
```bash
# Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Development
NEXT_PUBLIC_USE_MOCK=true   # Set to false when backend is live
```

---

## 11. Do Not Do List

- Do not use `any` TypeScript type — use the interfaces in `lib/types.ts`
- Do not use inline styles for colours — use Tailwind classes or CSS variables
- Do not use Arial, Inter, system-ui, or any font other than IBM Plex Mono and IBM Plex Sans
- Do not add gradients, drop shadows, blur effects, or glow
- Do not use rounded-full on anything except confidence dots (which are circles)
- Do not show raw SQL column names (like `ACTUAL_SALES`) in the chat response bubbles — those belong only in the Transparency Dashboard
- Do not auto-open ThinkingTrace — it must always start collapsed
- Do not show all 7 transparency tabs with content — only populate tabs whose data exists in the current response; others show empty states
- Do not use any chart library other than Recharts
- Do not use any state management library other than Zustand
