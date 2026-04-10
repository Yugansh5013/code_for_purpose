# OmniData — Product Requirements Document (v5.0)
**Hackathon:** NatWest Group — Code for Purpose: Talk to Data
**Status:** Final — Complete Architecture with Semantic Output Validation
**Last Updated:** April 2026

---

## 1. Product Overview

OmniData is an enterprise-grade, multi-agent AI system that democratises data access. Business users ask natural language questions and receive accurate, verifiable, and jargon-free insights — no SQL knowledge required, no exposure of sensitive data, no complex workflows.

The system uses a dynamic routing architecture built on LangGraph and the Model Context Protocol (MCP). It connects to the same enterprise tools that real organisations actually use: **Snowflake** for structured warehouse data, **Confluence** for internal policies and documentation, **Salesforce** for CRM and customer relationship data, and **Tavily** for live external market intelligence.

Every response passes through a **Semantic Output Validator** before reaching the user — a final LLM pass that audits the answer for technical jargon, replaces internal column names and object references with user-defined plain-English terms from the Metric Dictionary, and confirms the language matches how the user actually speaks about their data.

**Intended users:** Non-technical business analysts, operations teams, and leadership who need data answers without depending on an engineering or BI team.

**Real-world integrations (all live, not mocked):**

| Integration | Tool | Purpose |
|---|---|---|
| Structured data warehouse | Snowflake (free trial) | Revenue, sales, product data |
| Internal knowledge base | Confluence (free tier) | Policies, wikis, runbooks |
| CRM & customer data | Salesforce Developer Edition (free) | Accounts, opportunities, churn risk |
| External intelligence | Tavily Search API (free tier) | Market context, news |

---

## 2. Alignment with Hackathon Pillars

| Pillar | How OmniData Delivers It |
|---|---|
| **Clarity** | The Synthesis Node translates all results into plain English. The Semantic Output Validator makes a dedicated second pass to catch any jargon that slipped through — especially technical terms surfaced by RAG content. Temporal phrases are resolved to exact dates before any query runs. A surface-level summary always leads the response. |
| **Trust** | The Transparency Dashboard exposes the exact SQL and SOQL generated, the raw data, the Python visualisation code, and every source document excerpt. A Confidence Score chip (green / amber / red) appears on every structured-data result. The Metric Dictionary is publicly browsable. Every answer cites its exact source. The Semantic Validator log shows exactly which terms were rewritten and why. |
| **Speed** | The Intent Router sends queries only to the branches they need. DeepSeek R1 on Groq delivers sub-2-second SQL generation. The E2B sandbox is pre-warmed the moment the Router flags a SQL query. The Semantic Validator uses the fastest available model (`llama-3.3-8b`) and only fires when RAG content is present — it adds zero latency for pure SQL responses. |

---

## 3. System Architecture & Core Flows

The backend is orchestrated using **LangGraph** with a typed `StateGraph`. Full node execution order:

```
User Query
    ↓
Node 0: Intent Router              — classifies intent, sets branch flags
    ↓
Node 1: Clarification Node         — resolves temporal ambiguity
    ↓                                resolves metric aliases (Metric Dictionary)
    ↓                                pre-warms E2B if sql_likely = true
    ↓
┌──────────────────────────────────────────────────────────┐
│  Branch 1          Branch 2              Branch 3         │
│  Snowflake SQL     Confluence + SF CRM   Tavily Web       │
│  (if flagged)      (if flagged)          (if flagged)     │
│                    ├─ Sub-branch 2A                       │
│                    │  Confluence + Uploads                │
│                    └─ Sub-branch 2B                       │
│                       Salesforce SOQL                     │
└──────────────────────────────────────────────────────────┘
    ↓
Node 2: Synthesis Node             — merges all branch outputs
    ↓                                formats plain-English draft
    ↓                                strips jargon from structured data answers
    ↓                                cites all sources
Node 3: Semantic Output Validator  — fires only when Branch 2 output is present
    ↓                                audits RAG-sourced content for jargon
    ↓                                rewrites using Metric Dictionary terms
    ↓                                logs all substitutions for Transparency tab
User
```

---

### 3.1 Node 0: The Intent Router

- **Model:** `llama-3.3-8b` via Groq API
- **Function:** Classifies the user's intent and populates routing flags in LangGraph state.
- **Routing flags set:**
  - `sql_likely` (bool) — triggers sandbox pre-warm in Node 1
  - `branches` (list) — which of `["sql", "rag_confluence", "rag_salesforce", "web"]` to fire
  - `rag_sources` (list) — which RAG collections are relevant: `["confluence", "salesforce", "documents"]`
  - `rag_present` (bool) — true if any Branch 2 sub-branch will fire; used by Node 3 to decide whether to run
- **Output to state:**

```json
{
  "branches": ["sql", "rag_confluence"],
  "rag_sources": ["confluence", "documents"],
  "sql_likely": true,
  "rag_present": true,
  "original_query": "What does our refund policy say and how does it relate to our Q1 return rates?"
}
```

---

### 3.2 Node 1: Query Clarification & Normalisation

Sits between the Router and all branches. Resolves ambiguity before any downstream work begins.

#### 3.2.1 Temporal Resolution

All relative date phrases are resolved to explicit ISO 8601 date ranges using the server's current date:

| User phrase | Resolved to |
|---|---|
| "this month" | `date >= '2026-04-01' AND date <= '2026-04-30'` |
| "last quarter" | `date >= '2026-01-01' AND date <= '2026-03-31'` |
| "YTD" | `date >= '2026-01-01' AND date <= today` |
| "recent" | `date >= today - 30 days` |
| "last year" | `date >= '2025-01-01' AND date <= '2025-12-31'` |

The resolved constraint is injected as a `date_filter` string into the branch context and appended to the SQL/SOQL prompt as an annotated comment.

#### 3.2.2 Metric Dictionary Lookup

The Metric Dictionary (Section 3.3) is checked for alias matches in the user's query:

- **Unambiguous match:** resolved silently, injected into context, shown as a small UI note ("Interpreting *revenue* as `Total Sales (GBP)`")
- **Ambiguous match:** a single clarifying question is returned to the user with two clickable option buttons before any branch fires
- **No match:** proceeds without modification

#### 3.2.3 Conditional Sandbox Pre-Warming

If `sql_likely` is `true`, an async background task immediately creates a warm E2B sandbox stored in application state. Runs in parallel with the rest of Node 1 and completes before Branch 1 needs it.

The sandbox is only pre-warmed for SQL-flagged queries. Branch 2 and Branch 3 never touch E2B.

```python
if state["sql_likely"] and not app.state.warm_sandbox:
    asyncio.create_task(prewarm_sandbox(app.state))
```

---

### 3.3 The Metric Dictionary

A YAML file (`backend/src/config/metric_dictionary.yaml`) checked into the repository. The concrete implementation of Learning Outcome #2: *"Why shared definitions matter — ensuring 'revenue', 'orders', 'active users' always mean the same thing across teams."*

Used by three nodes: Node 1 (alias resolution before querying), Node 2 (jargon stripping in the Synthesis prompt), and Node 3 (term rewriting audit on RAG content). Exposed as a read-only `/metrics` endpoint powering the Metrics Glossary in the UI.

Each entry has a `display_name` field — the exact phrase that should appear in user-facing responses. This is what the Synthesis Node and Semantic Validator substitute in place of technical terms.

```yaml
metrics:

  revenue:
    display_name: "Total Sales"
    aliases: ["money", "income", "earnings", "sales", "turnover",
              "how much we made", "financials"]
    canonical_column: "ACTUAL_SALES"
    table: "OMNIDATA_DB.SALES.AURA_SALES"
    unit: "GBP"
    description: "Total transaction value before returns or adjustments."
    ambiguous: false
    jargon_terms: ["ACTUAL_SALES", "actual_sales"]

  performance:
    display_name: null
    aliases: ["results", "numbers", "how we did", "metrics", "kpis"]
    resolves_to: ["revenue", "unit_sales", "customer_count"]
    ambiguous: true
    clarification_prompt: "Which metric for 'performance'?
      Options: Total Sales (GBP), Units Sold, or Customer Count."

  churn:
    display_name: "Customer Churn"
    aliases: ["lost customers", "customer loss", "attrition",
              "drop-off", "cancellations"]
    canonical_column: "CHURN_FLAG"
    table: "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS"
    unit: "count / rate"
    description: "Customers who did not renew or cancelled in the period."
    ambiguous: false
    jargon_terms: ["CHURN_FLAG", "churn_flag", "ChurnRisk__c"]

  active_users:
    display_name: "Active Customers"
    aliases: ["active customers", "engaged users", "DAU", "MAU"]
    canonical_column: "IS_ACTIVE"
    table: "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS"
    unit: "count"
    description: "Customers with at least one transaction or login
      in the measurement period."
    ambiguous: false
    jargon_terms: ["IS_ACTIVE", "is_active"]

  pipeline_value:
    display_name: "Sales Pipeline Value"
    aliases: ["deals", "opportunities", "sales pipeline",
              "potential revenue", "open deals"]
    canonical_object: "Opportunity"
    salesforce_field: "Amount"
    source: "salesforce"
    unit: "GBP"
    description: "Total value of open Salesforce Opportunities
      not yet marked Closed Won or Closed Lost."
    ambiguous: false
    jargon_terms: ["Opportunity", "Amount", "OpportunityId",
                   "Closed Won", "Closed Lost", "StageName"]
```

The `jargon_terms` list is the key addition for Node 3. It enumerates the exact technical strings — column names, Salesforce field names, object names, API identifiers — that must never appear in a user-facing response. The Semantic Validator scans for these terms specifically.

---

### 3.4 Branch 1: Structured Data (Snowflake SQL)

Handles precise quantitative questions against the live Snowflake data warehouse.

**Snowflake connection:**

```python
import snowflake.connector
conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database="OMNIDATA_DB",
    schema="SALES"
)
```

#### Step 1: Semantic Schema Retrieval (Hybrid RAG)

**ChromaDB Collection: `schema_store`** — enriched table descriptions using natural language, never raw DDL:

```
Table Name: OMNIDATA_DB.SALES.AURA_SALES
Natural Language Description: This table tracks daily revenue, money
  made, total sales, and income broken down by geographic region,
  product line, and sales channel. Use this table for questions
  about revenue, earnings, profit, or financial performance by area.
Columns:
  - ACTUAL_SALES (NUMBER): Total revenue in GBP.
  - GEO_TERRITORY (VARCHAR): Geographic region (North, South, East, West).
  - PRODUCT_SKU (VARCHAR): Product identifier.
  - SALE_DATE (DATE): Transaction date.
  - CHANNEL (VARCHAR): Sales channel (Online, Retail, Partner).
Metadata: { "table_name": "AURA_SALES", "schema_hash": "a3f8c2d1..." }
```

**Hybrid Search:** Vector similarity (ChromaDB cosine) blended with BM25 keyword score (`rank_bm25`). Weights: BM25 0.6, vector 0.4. Top 3 tables retrieved. Schema version hash compared against live Snowflake introspection on every retrieval — stale documents excluded automatically.

#### Step 2: Few-Shot Example Retrieval

**ChromaDB Collection: `examples_store`** — verified Q→SQL pairs with metadata filtering by table name and schema hash. Top 2 examples after filter. Stale examples (hash mismatch) excluded automatically.

#### Step 3: Dynamic Prompt Construction

```
You are a senior SQL expert working with Snowflake.
Generate ONLY the SQL query. No explanation, no markdown, no preamble.
Use only the fully qualified table names provided (DATABASE.SCHEMA.TABLE).
Never use DROP, DELETE, UPDATE, INSERT, CREATE, ALTER, or TRUNCATE.

{date_filter_comment_if_applicable}

DATABASE TABLES:
{schema_chunk_1}
{schema_chunk_2}
{schema_chunk_3}

VERIFIED EXAMPLES:
Q: {similar_question_1}
SQL: {similar_sql_1}

Q: {similar_question_2}
SQL: {similar_sql_2}

QUESTION: {user_question}
SQL:
```

#### Step 4: SQL Generation

- **Model:** `deepseek-r1-distill-llama-70b` via Groq API
- **Temperature:** 0.0

#### Step 5: SQL Validation (Security Gate)

`sqlglot`-based validator. Checks: parse validity, SELECT/WITH allowlist, table whitelist. Retry loop up to 2 times with error feedback. All blocked queries logged.

#### Step 6: Confidence Scoring

Three-signal blended score:

| Signal | Weight | Threshold |
|---|---|---|
| Schema RAG top-1 cosine similarity | 40% | < 0.75 = low |
| Retry count | 40% | 0 = full, 1 = half, 2 = zero |
| Result row sanity | 20% | Zero rows on non-aggregate = low |

Tiers: Green ≥ 0.8, Amber 0.5–0.79, Red < 0.5. Score, tier, and one-line explanation included in output payload and shown as a chip in the UI.

#### Step 7: E2B Sandbox Execution & Visualisation

Single persistent `e2b.AsyncSandbox()` session claimed from pre-warmed pool.

Sub-step 7a: Execute validated SQL against Snowflake, load results into Pandas DataFrame inside sandbox.

Sub-step 7b: In the same sandbox session, run matplotlib/plotly visualisation script against the already-loaded DataFrame. Chart type selected by result shape:

| Result shape | Chart type |
|---|---|
| Single value | No chart — plain text |
| Two columns (label + numeric) | Horizontal bar chart |
| Date column + numeric | Line chart |
| Multi-group comparison | Grouped bar chart |
| More than 10 rows | Truncated to top 10 with note |

Returns chart as base64 PNG and Python code as string.

**Branch 1 Output Payload:**
```json
{
  "sql_query": "SELECT GEO_TERRITORY, SUM(ACTUAL_SALES)...",
  "raw_data": [{"GEO_TERRITORY": "North", "ACTUAL_SALES": 142000}],
  "chart_b64": "iVBORw0KGgo...",
  "python_code": "import matplotlib.pyplot as plt\n...",
  "tables_used": ["OMNIDATA_DB.SALES.AURA_SALES"],
  "confidence": {
    "score": 0.87,
    "tier": "green",
    "explanation": "Strong schema match, zero retries, non-empty result."
  },
  "date_resolution": "Resolved 'last month' → 2026-03-01 to 2026-03-31"
}
```

---

### 3.5 Branch 2: Unstructured Data & CRM Intelligence

Split into two parallel sub-branches controlled by `rag_sources` in state.

#### Sub-branch 2A: Confluence & Document RAG

**What it answers:** Questions about internal policies, compliance documents, runbooks, strategy documents, and any uploaded PDF or CSV.

##### Why Confluence

Confluence (Atlassian) is the industry-standard internal knowledge base across financial services. It has a free tier (up to 10 users), a well-documented REST API, and is immediately recognisable to NatWest judges as the correct enterprise tool.

##### Confluence MCP Server

Deployed as a FastAPI microservice on Railway. Endpoints:

```
GET  /confluence/search?query={text}&space_key={key}
     → Returns top 5 most relevant page excerpts with titles and URLs

POST /confluence/sync?space_key={key}
     → Fetches all pages, chunks, embeds, upserts into confluence_store
```

Authentication via `CONFLUENCE_API_TOKEN` and `CONFLUENCE_BASE_URL`.

**ChromaDB Collection: `confluence_store`**

```
Metadata: {
  "source": "confluence",
  "page_title": "Enterprise Customer Refund Policy",
  "space_key": "CUSTOPS",
  "page_url": "https://yourorg.atlassian.net/wiki/spaces/CUSTOPS/...",
  "last_synced": "2026-04-10T14:23:00Z",
  "chunk_index": 2
}
```

**ChromaDB Collection: `documents_store`** — user-uploaded PDFs and CSVs chunked (512 tokens, 64-token overlap), embedded, and stored with source metadata. Persists across restarts via Railway volume.

```
Metadata: {
  "source": "upload",
  "filename": "Q3_Marketing_Report.pdf",
  "page": 4,
  "upload_date": "2026-04-09",
  "chunk_index": 1
}
```

**Retrieval:** Parallel similarity search across `confluence_store` and `documents_store`. Top 3 from each merged and re-ranked by cosine score. Top 5 overall passed to Synthesis Node with full source metadata.

---

#### Sub-branch 2B: Salesforce CRM (SOQL Generation Path)

**What it answers:** Questions about customers, accounts, pipeline, churn risk, deal value, and relationship history.

##### Why Salesforce (not Zendesk)

Zendesk covers support tickets only. Salesforce holds accounts, contacts, deals, opportunities, renewal risk, and interaction history — the full commercial picture. Salesforce Financial Services Cloud is the standard CRM in large banks. NatWest judges will recognise it immediately. Salesforce Developer Edition is free and permanent.

##### Salesforce SOQL Generation Pipeline

Mirrors Branch 1 exactly but generates SOQL instead of SQL:

**ChromaDB Collection: `salesforce_schema_store`** — enriched Salesforce object descriptions:

```
Object: Account
Natural Language Description: Represents a company or organisation.
  Use for questions about customers, clients, churn risk, annual
  contract value, renewal status, or account health.
Fields:
  - Name (Text): The account or company name.
  - AnnualRevenue (Currency): Annual revenue or contract value in GBP.
  - ChurnRisk__c (Picklist): Custom churn risk score — High, Medium, Low.
  - Region__c (Text): Sales region.
  - LastActivityDate (Date): Most recent logged activity date.
Metadata: { "object_name": "Account", "schema_hash": "b2e9a1f4..." }
```

**ChromaDB Collection: `salesforce_examples_store`** — verified Q→SOQL pairs with object metadata filtering and schema hash.

**SOQL Generation:**
- **Model:** `deepseek-r1-distill-llama-70b` via Groq API
- **Temperature:** 0.0

**SOQL Validation:** Dedicated `soql_validator.py` enforcing:
- SELECT only — no DML (`INSERT`, `UPDATE`, `DELETE`, `UPSERT`)
- `LIMIT` clause mandatory on all queries (max 200 rows, enforced by validator)
- Aggregate functions require `GROUP BY`
- Object names checked against known Salesforce schema

**Salesforce MCP Server:** FastAPI microservice on Railway:

```
POST /salesforce/query
     Body: { "soql": "SELECT Name, AnnualRevenue FROM Account LIMIT 10" }
     → Executes via simple-salesforce, returns JSON records

GET  /salesforce/schema?object={ObjectName}
     → Returns field metadata for a Salesforce object
```

Authentication via Salesforce Connected App credentials (OAuth 2.0 username-password flow for Developer Edition).

**Sub-branch 2B Output Payload:**
```json
{
  "soql_query": "SELECT Name, AnnualRevenue, ChurnRisk__c FROM Account WHERE...",
  "raw_records": [
    {"Name": "Acme Corp", "AnnualRevenue": 250000, "ChurnRisk__c": "High"}
  ],
  "objects_used": ["Account"],
  "confidence": {
    "score": 0.91,
    "tier": "green",
    "explanation": "Strong object match, zero retries, 8 records returned."
  }
}
```

Salesforce results are formatted as a plain table by the Synthesis Node. Charts are not generated for SOQL results — E2B is only used for Snowflake Branch 1.

---

### 3.6 Branch 3: External Market Intelligence

Handles questions requiring live external context. The only change from previous versions is the addition of a **query refinement step** before the Tavily call.

**Why query refinement is necessary:** A raw question like "Why did our South region underperform last quarter?" contains internal context that Tavily cannot resolve — "our South region" means nothing to a public search engine, and "last quarter" without a resolved year produces stale results. Without refinement, Branch 3 returns irrelevant or generic results.

#### Step 1: Search Query Rewriter

Before calling Tavily, a lightweight LLM call rewrites the user's question into an effective public search query:

- **Model:** `llama-3.3-8b` via Groq API (fast, low token cost)
- **Prompt:**

```
You are a search query specialist. Rewrite the following business
question as a concise, public web search query. Remove all internal
company context ("our", "we", "last quarter" → use the resolved
year and quarter). Focus on the underlying business or economic
phenomenon the user wants to understand.

Original question: {user_question}
Resolved date context: {date_filter_if_present}

Output only the search query. No explanation.
```

**Example rewrite:**

| User question | Rewritten search query |
|---|---|
| "Why did our South region underperform last quarter?" | "UK South retail sales decline Q1 2026 causes" |
| "What macro factors explain our churn spike?" | "customer churn increase financial services UK 2026" |
| "Is our pricing competitive right now?" | "enterprise SaaS pricing benchmarks UK 2026" |

#### Step 2: Tavily Search

The rewritten query is submitted to Tavily. Top 3 results retrieved. Source URLs and publication dates captured.

#### Step 3: Summarisation

The 3 results are summarised into 2–3 bullet points by the Synthesis Node — not by a separate LLM call. This avoids a redundant model call and keeps Branch 3 fast.

**Branch 3 Output Payload:**
```json
{
  "original_query": "Why did our South region underperform last quarter?",
  "rewritten_query": "UK South retail sales decline Q1 2026 causes",
  "search_results": [
    {
      "title": "UK Regional Retail Trends Q1 2026",
      "snippet": "Southern regions saw a 14% decline in consumer spending...",
      "url": "https://...",
      "published_date": "2026-03-28"
    }
  ]
}
```

---

### 3.7 Node 2: The Synthesis Node

- **Model:** `llama-3.3-70b-versatile` via Groq API
- **Inputs:** All active branch payloads merged into a single context window
- **Two explicit jobs in one prompt:**

**Job 1 — Construct the answer:**
- Lead with a 1–2 sentence plain-English summary
- Follow with bullet-point breakdown of key drivers or findings
- If Branch 3 fired, integrate the external context naturally ("This aligns with broader UK market trends showing...")
- Cite every source inline: `[Snowflake: AURA_SALES]`, `[Confluence: Refund Policy]`, `[Salesforce: Account]`, `[Q3_Marketing_Report.pdf, p.4]`, `[Reuters, 28 Mar 2026]`
- If date resolution was applied: "Showing data for March 2026 (resolved from 'last month')"
- If confidence is amber or red: append a verification note

**Job 2 — Strip technical jargon from structured data content:**

The Synthesis prompt includes an explicit audit instruction for Branch 1 and 2B output:

```
JARGON AUDIT — apply to all structured data references in your answer:
The following technical terms must NEVER appear in your response.
Replace each with the display name shown.

{metric_dictionary_jargon_substitution_list}

Example substitutions:
  ACTUAL_SALES       → "Total Sales"
  GEO_TERRITORY      → "Region"
  CHURN_FLAG         → "Customer Churn"
  ChurnRisk__c       → "Churn Risk Score"
  AnnualRevenue      → "Annual Contract Value"
  StageName          → "Deal Stage"

After writing your answer, re-read every sentence and confirm
none of the forbidden terms above appear in the output.
```

The substitution list is dynamically generated at runtime from the `jargon_terms` fields in the Metric Dictionary, so it stays current as the dictionary is updated.

This handles jargon in Branch 1 and 2B structured outputs where the LLM is in full control of the language. It does not reliably catch jargon embedded inside quoted RAG content from Confluence or uploaded documents — that is handled by Node 3.

**Synthesis output includes a `jargon_audit_clean` boolean** — set to `true` if no jargon substitutions were needed, `false` if substitutions were made. Used by Node 3 to decide whether a full second pass is warranted.

---

### 3.8 Node 3: Semantic Output Validator

This node is the final quality gate before the response reaches the user. It is a dedicated LLM pass that audits the Synthesis Node's output specifically for jargon embedded in RAG-sourced content — the one category that Node 2 cannot fully control.

#### When Node 3 fires

Node 3 fires **only** when `rag_present = true` in state (set by Node 0). This means:

- **Pure SQL queries** (Branch 1 only): Node 3 does **not** fire. The Synthesis Node's built-in jargon audit is sufficient. Zero added latency.
- **Pure web queries** (Branch 3 only): Node 3 does **not** fire. External content uses plain English by nature.
- **Any query involving Branch 2** (Confluence, Salesforce, or uploaded docs): Node 3 **fires**. RAG content frequently contains technical field names, API identifiers, and internal system terminology that appear verbatim in retrieved chunks.

This conditional execution is the key design decision. It means the Semantic Validator adds latency **only when it is actually needed** — and never for the fast, high-frequency pure-SQL queries that are the most common use case.

#### What Node 3 does

- **Model:** `llama-3.3-8b` via Groq API (fastest available — this pass is intentionally lightweight)
- **Input:** The full text of the Synthesis Node's draft response
- **Process:**

```
You are a plain-language editor for a business intelligence tool.
Your job is to make responses readable for non-technical users.

STEP 1 — SCAN for any of the following technical terms:
{full_jargon_terms_list_from_metric_dictionary}

Also scan for:
- Salesforce API field names (anything ending in __c or containing Id)
- SQL keywords used as nouns (SELECT, JOIN, WHERE, NULL, VARCHAR)
- Database object names in ALL_CAPS
- Confluence page IDs or space keys
- Any term that a non-technical business user would not understand

STEP 2 — REWRITE any found terms using these substitutions:
{metric_dictionary_display_name_map}

For terms not in the dictionary, replace them with plain English
descriptions of what the concept means in business terms.

STEP 3 — OUTPUT the cleaned response text only.
Also output a JSON log of every substitution made:
{
  "substitutions": [
    {"original": "ChurnRisk__c", "replaced_with": "Churn Risk Score",
     "location": "paragraph 2"},
    {"original": "IS_ACTIVE = 1", "replaced_with": "active customers",
     "location": "bullet point 3"}
  ],
  "validation_passed": true
}
```

#### Node 3 outputs

- **Cleaned response text:** Replaces the Synthesis Node's draft in state. This is what the user sees.
- **Substitution log:** Stored in state and surfaced in the Transparency Dashboard under a new **"Language"** tab. This tab shows every term that was rewritten and what it was replaced with — a direct demonstration of the system's commitment to plain language.
- **`validation_passed` boolean:** If Node 3 finds no substitutions needed, it returns the original text unchanged and logs `"substitutions": []`. This means the system never silently alters a clean response.

#### Node 3 latency profile

Using `llama-3.3-8b` on Groq, a typical response audit completes in 300–600ms. Since Node 3 only fires for RAG-containing responses (which are already slower due to vector retrieval and multi-source synthesis), this is imperceptible relative to the total pipeline latency.

---

## 4. Complete Node Execution Summary

| Node | Model | Fires when | Purpose |
|---|---|---|---|
| Node 0: Intent Router | Llama 3.3 8B | Always | Classify intent, set routing flags |
| Node 1: Clarification | — (rule-based + dict lookup) | Always | Resolve dates, metrics, pre-warm sandbox |
| Branch 1: Snowflake SQL | DeepSeek R1 70B | `sql_likely = true` | Text-to-SQL → execute → visualise |
| Branch 2A: Confluence RAG | — (vector search) | `rag_confluence` flagged | Retrieve policy/wiki content |
| Branch 2B: Salesforce SOQL | DeepSeek R1 70B | `rag_salesforce` flagged | Text-to-SOQL → execute |
| Branch 3: Web Search | Llama 3.3 8B (rewriter) | `web_needed = true` | Refine query → Tavily → summarise |
| Node 2: Synthesis | Llama 3.3 70B | Always | Merge outputs, draft answer, strip SQL jargon |
| Node 3: Semantic Validator | Llama 3.3 8B | `rag_present = true` | Audit RAG jargon, rewrite, log substitutions |

---

## 5. ChromaDB Collections Reference

| Collection | Source | Purpose | Search type |
|---|---|---|---|
| `schema_store` | Snowflake schema | Enriched table descriptions | Hybrid (BM25 0.6 + vector 0.4) |
| `examples_store` | Hand-crafted | Verified Q→SQL pairs | Hybrid (BM25 0.6 + vector 0.4) |
| `confluence_store` | Confluence REST API | Synced policy and wiki content | Pure vector |
| `documents_store` | User uploads | Uploaded PDFs and CSVs | Pure vector |
| `salesforce_schema_store` | Salesforce metadata | Enriched object descriptions | Hybrid (BM25 0.6 + vector 0.4) |
| `salesforce_examples_store` | Hand-crafted | Verified Q→SOQL pairs | Hybrid (BM25 0.6 + vector 0.4) |

Schema version hashing applied to all four hybrid-search collections. Stale documents excluded from retrieval automatically.

---

## 6. Deployment Architecture

| Component | Service | Tier |
|---|---|---|
| Frontend (Next.js) | Vercel | Free |
| Backend / LangGraph (FastAPI) | Railway | Free ($5 credit) |
| Confluence MCP server | Railway (second service) | Free |
| Salesforce MCP server | Railway (third service) | Free |
| Snowflake (live data warehouse) | Snowflake | 30-day free trial ($400 credit) |
| Salesforce CRM | Salesforce Developer Edition | Free (permanent) |
| Confluence knowledge base | Confluence Cloud | Free (up to 10 users) |
| ChromaDB (persistent) | Railway volume (Docker) | Free |
| E2B code sandbox | E2B Cloud | Free tier, SQL branch only |
| LLM inference (all models) | Groq API | Free tier |
| Web search | Tavily API | Free (1k/mo) |

---

## 7. Model Selection Summary

| Node | Model | Reason |
|---|---|---|
| Intent Router (Node 0) | `llama-3.3-8b` (Groq) | Low latency, classification only |
| Branch 3 query rewriter | `llama-3.3-8b` (Groq) | Fast rewrite, minimal tokens needed |
| SQL Generation (Branch 1) | `deepseek-r1-distill-llama-70b` (Groq) | Reasoning model for multi-step logical deduction |
| SOQL Generation (Branch 2B) | `deepseek-r1-distill-llama-70b` (Groq) | Same reasoning requirements as SQL |
| Synthesis (Node 2) | `llama-3.3-70b-versatile` (Groq) | Best fluent natural language output |
| Semantic Validator (Node 3) | `llama-3.3-8b` (Groq) | Fast audit pass — speed over depth |
| Embeddings | `all-MiniLM-L6-v2` (local) | Free, no API dependency |

---

## 8. User Interface Specifications

### 8.1 Layout: Multi-Pane Dashboard

```
┌──────────────┬──────────────────────────────────┬──────────────────┐
│  Left Pane   │        Centre Pane                │   Right Pane     │
│  Navigation  │      Conversational Interface     │  (Top) Chart     │
│              │                                   │                  │
│ · New Chat   │  [Thinking completed ▾]           │  Bar chart...    │
│ · Agents     │  Branches: SQL, Confluence        │  ─────────────── │
│ · History    │  Language: 2 terms rewritten      │  (Bottom)        │
│ · Metrics    │                                   │  Transparency    │
│   Glossary   │  Total Sales dropped 11% in       │  Dashboard       │
│ · Profile    │  March. Showing data for March    │                  │
│              │  2026 (resolved from 'last         │  SQL | Data |    │
│              │  month').                          │  SOQL | Context  │
│              │                                   │  Code | Conf. |  │
│              │  Key drivers:                     │  Language        │
│              │  · South Region: -22%             │                  │
│              │  · Per Refund Policy [Confluence] │                  │
│              │                                   │                  │
│              │  [Snowflake: AURA_SALES] ● green  │                  │
│              │  [Confluence: Refund Policy]      │                  │
│              │                                   │                  │
│              │  ┌──────────────────────────────┐ │                  │
│              │  │  Ask your data...        [▾] │ │                  │
│              │  └──────────────────────────────┘ │                  │
└──────────────┴──────────────────────────────────┴──────────────────┘
```

### 8.2 Left Pane

- New Chat, agent selector, recent chat history
- Metrics Glossary — browsable, searchable Metric Dictionary view
- Integration status icons (Snowflake, Confluence, Salesforce — green when connected)

### 8.3 Centre Pane

- **Thinking state:** Collapsible, shows branches fired, retries, date and metric resolutions, whether Semantic Validator ran and how many terms were rewritten
- **Date and metric resolution notes** shown inline
- **Source chips** coloured by integration: blue (Snowflake), purple (Confluence), teal (Salesforce), orange (uploaded docs), gray (Tavily)
- **Confidence dot** on Snowflake and Salesforce chips only
- **Clarification prompt** when Node 1 detects an ambiguous metric

### 8.4 Right Pane (Top): Visual Context

- Chart from E2B sandbox (Branch 1 only)
- Chart type toggle, download, fullscreen
- "No chart available" shown for RAG-only or web-only responses

### 8.5 Right Pane (Bottom): Transparency & Trust Dashboard

| Tab | Shown when | Content |
|---|---|---|
| **SQL** | Branch 1 fired | Syntax-highlighted Snowflake SQL |
| **SOQL** | Branch 2B fired | Syntax-highlighted Salesforce SOQL |
| **Data** | Branch 1 or 2B | Raw results table |
| **Code** | Branch 1 with chart | Python visualisation code |
| **Context** | Branch 2A fired | Confluence excerpts and doc chunks with source links |
| **Confidence** | Branch 1 or 2B | Three-signal score breakdown |
| **Language** | Node 3 fired | Substitution log: every jargon term rewritten and what it became |

The **Language tab** is the visible proof of the Semantic Validator's work. It lists every substitution (e.g., `ChurnRisk__c` → `"Churn Risk Score"`) with its location in the response. When no substitutions were needed, it shows "No technical terms found — response is clean." Judges can click this tab to see the system actively enforcing plain language.

---

## 9. Tech Stack

| Category | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS, shadcn/ui |
| Backend | Python 3.11, FastAPI, LangGraph |
| LLM Inference | Groq API (Llama 3.3 8B, DeepSeek R1 70B, Llama 3.3 70B) |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, local) |
| Keyword search | `rank_bm25` (hybrid search for schema/examples collections) |
| Orchestration | LangGraph (StateGraph with typed state) |
| Vector DB | ChromaDB (persistent, Docker volume on Railway) |
| Structured data | Snowflake (live warehouse, 30-day free trial) |
| Snowflake connector | `snowflake-connector-python` |
| CRM | Salesforce Developer Edition (free, permanent) |
| Salesforce connector | `simple-salesforce` |
| Knowledge base | Confluence Cloud (free tier) |
| Confluence connector | Confluence REST API (API token auth) |
| SQL/SOQL validation | `sqlglot` |
| Code sandbox | E2B Cloud (SQL branch only, conditional pre-warm) |
| Web search | Tavily API |
| MCP transport | `mcp` Python SDK (FastAPI microservices) |
| Schema/metric config | YAML files checked into repo |
| Deployment: Frontend | Vercel |
| Deployment: Backend + MCP servers | Railway |

---

## 10. Repository Structure

```
omnidata/
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   └── components/
│   │       ├── ChatPane.tsx
│   │       ├── ChartPane.tsx
│   │       ├── TransparencyDashboard.tsx
│   │       ├── ConfidenceChip.tsx
│   │       ├── MetricsGlossary.tsx
│   │       ├── SourceChip.tsx
│   │       └── LanguageTab.tsx            # Semantic Validator substitution log
│   ├── package.json
│   └── .env.example
│
├── backend/
│   ├── src/
│   │   ├── main.py
│   │   ├── graph.py
│   │   ├── config/
│   │   │   ├── metric_dictionary.yaml
│   │   │   └── schema_descriptions.yaml
│   │   ├── router/
│   │   │   └── intent_router.py
│   │   ├── clarification/
│   │   │   ├── clarification_node.py
│   │   │   ├── temporal_resolver.py
│   │   │   └── metric_resolver.py
│   │   ├── branches/
│   │   │   ├── branch_sql.py
│   │   │   ├── branch_rag.py
│   │   │   ├── branch_salesforce.py
│   │   │   └── branch_web.py              # includes query rewriter step
│   │   ├── synthesis/
│   │   │   └── synthesis_node.py          # includes jargon audit prompt
│   │   ├── validation/
│   │   │   ├── semantic_validator.py      # Node 3
│   │   │   ├── sql_validator.py
│   │   │   ├── soql_validator.py
│   │   │   └── confidence_scorer.py
│   │   ├── vector/
│   │   │   ├── schema_store.py
│   │   │   ├── examples_store.py
│   │   │   ├── confluence_store.py
│   │   │   ├── documents_store.py
│   │   │   ├── salesforce_schema_store.py
│   │   │   ├── salesforce_examples_store.py
│   │   │   ├── hybrid_search.py
│   │   │   └── schema_hasher.py
│   │   ├── sandbox/
│   │   │   ├── e2b_runner.py
│   │   │   └── sandbox_pool.py
│   │   ├── snowflake/
│   │   │   └── connector.py
│   │   └── salesforce/
│   │       └── connector.py
│   ├── tests/
│   │   ├── test_sql_validator.py
│   │   ├── test_soql_validator.py
│   │   ├── test_schema_rag.py
│   │   ├── test_clarification_node.py
│   │   ├── test_temporal_resolver.py
│   │   ├── test_confidence_scorer.py
│   │   └── test_semantic_validator.py     # Node 3 unit tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── mcp_servers/
│   ├── confluence/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── salesforce/
│       ├── main.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── docs/
│   └── architecture.md
│
├── .env.example
└── README.md
```

---

## 11. Environment Variables Reference

```bash
# Groq
GROQ_API_KEY=

# Snowflake
SNOWFLAKE_ACCOUNT=               # e.g., xy12345.eu-west-1
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=             # e.g., COMPUTE_WH
SNOWFLAKE_DATABASE=              # OMNIDATA_DB
SNOWFLAKE_SCHEMA=                # SALES

# Salesforce (Developer Edition)
SALESFORCE_USERNAME=
SALESFORCE_PASSWORD=
SALESFORCE_SECURITY_TOKEN=
SALESFORCE_CONSUMER_KEY=
SALESFORCE_CONSUMER_SECRET=

# Confluence
CONFLUENCE_BASE_URL=             # e.g., https://yourorg.atlassian.net
CONFLUENCE_API_TOKEN=
CONFLUENCE_USER_EMAIL=
CONFLUENCE_DEFAULT_SPACE=        # e.g., CUSTOPS

# E2B
E2B_API_KEY=

# Tavily
TAVILY_API_KEY=

# ChromaDB
CHROMA_PERSIST_PATH=             # /data/chroma (Railway volume mount)

# MCP server URLs (set by Railway on deploy)
CONFLUENCE_MCP_URL=
SALESFORCE_MCP_URL=

# App
BACKEND_URL=
NEXT_PUBLIC_API_URL=
```

---

## 12. Hackathon Compliance Checklist

| Requirement | Notes |
|---|---|
| `README.md` with overview, features, install, tech stack, usage | Only list working features |
| `requirements.txt` and `package.json` | One per service |
| `.env.example` with all keys, no real values | See Section 11 |
| No hardcoded secrets | All via `os.environ` |
| `git commit -s` DCO sign-off on every commit | Apache License 2.0 |
| Repository private during hackathon | Make public after review |
| Logical folder structure | See Section 10 |
| All listed features working and honest | Label any partially-implemented features |
| Tests in `tests/` directory | Including `test_semantic_validator.py` |
| Architecture diagram in `docs/` | Full system flow |
| No plagiarism, original integration work | Open-source libraries permitted |

---

## 13. Known Limitations & Honest Scope

- **Salesforce Developer Edition data:** Sample data with synthetic accounts and custom churn risk fields. Not real customer data.
- **Confluence free tier:** One demo space pre-loaded with synthetic policy documents.
- **Single Snowflake schema:** Pre-loaded mock business data. Multi-warehouse routing not implemented.
- **No user authentication:** Single-tenant for demo purposes.
- **E2B concurrency:** One pre-warmed sandbox per server instance. Concurrent SQL requests cause the second to cold-start.
- **Metric Dictionary:** Manually maintained YAML. No automated sync from live data sources.
- **Confluence sync:** Manual trigger only. No automated scheduled sync.
- **Semantic Validator scope:** Only audits final response text. Does not audit intermediate chain-of-thought reasoning tokens from DeepSeek R1.

---

## 14. Future Improvements

- Scheduled Confluence sync (cron job)
- Salesforce OAuth 2.0 web flow replacing username-password
- Multi-tenant authentication with team-scoped ChromaDB namespaces
- Snowflake + Salesforce metadata auto-ingestion to keep Metric Dictionary in sync
- SharePoint / OneDrive as a third knowledge base source
- E2B sandbox pool for concurrent SQL requests
- Query result caching (Redis)
- Fine-tuned embedding model on financial services terminology
- Streaming SQL/SOQL generation to reduce perceived latency
- Automated example store re-validation on schema change
- Semantic Validator feedback loop — flagged substitutions used to improve the Metric Dictionary over time