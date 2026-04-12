# OmniData — Product Requirements Document (v6.0)
**Hackathon:** NatWest Group — Code for Purpose: Talk to Data
**Status:** Final — GCP + Pinecone + Full Seed Data Specification
**Last Updated:** April 2026

---

## 1. Product Overview

OmniData is an enterprise-grade, multi-agent AI system that democratises data access. Business users ask natural language questions and receive accurate, verifiable, and jargon-free insights — no SQL knowledge required, no exposure of sensitive data, no complex workflows.

The system connects to the same enterprise tools that real organisations actually use: **Snowflake** for structured warehouse data, **Confluence** for internal policies and documentation, **Salesforce** for CRM and customer relationship data, and **Tavily** for live market intelligence. All vector search is powered by **Pinecone** serverless indexes. All backend services run on **Google Cloud Run**.

**The demo company:** All seed data represents **Aura Retail** — a fictional mid-sized UK omnichannel retailer selling consumer electronics across four regions through three sales channels. This fictional company provides a realistic, judge-friendly context where every query type from the hackathon brief has a compelling, pre-designed answer.

**Real-world integrations (all live, not mocked):**

| Integration | Tool | Tier |
|---|---|---|
| Structured data warehouse | Snowflake | 30-day trial ($400 credit) |
| Vector database | Pinecone serverless | Free (Starter plan, 100k vectors) |
| Internal knowledge base | Confluence Cloud | Free (up to 10 users) |
| CRM & customer data | Salesforce Developer Edition | Free (permanent) |
| External intelligence | Tavily Search API | Free (1k requests/month) |
| Backend compute | Google Cloud Run | Free ($300 GCP credit) |
| Frontend | Vercel | Free |
| LLM inference | Groq API | Free tier |
| Code sandbox | E2B Cloud | Free tier |

---

## 2. The Aura Retail Demo Narrative

Before any code is written, the seed data must tell a coherent business story. Judges remember narratives, not query results. Every piece of data across every integration is designed to support one of four interconnected story threads that play out across October 2025 to March 2026.

### Thread 1 — The South Region Crisis
South region revenue drops 28% in February 2026 because the regional marketing budget was cut in a January board decision. This single event is visible across every integration: as a revenue drop in Snowflake, as a budget reallocation memo in Confluence, and as a cluster of high-churn-risk accounts in Salesforce. The hackathon's flagship use case — "Why did revenue drop?" — is answered by pulling from all three simultaneously.

### Thread 2 — The North Region Success Story
North region launches **AuraSound Pro** headphones in January 2026 and drives a 34% revenue spike in Q1. This provides a positive contrast to the South story and is the answer to every "breakdown" and "comparison" demo query. The product launch announcement lives in Confluence. The sales uplift lives in Snowflake.

### Thread 3 — The SMB Churn Wave
Small and medium business customers begin churning in March 2026, concentrated in South and East regions, following a February price increase on the Partner channel. This is visible in Salesforce as accounts marked `ChurnRisk__c = High` and in Snowflake as declining repeat purchase rates in the Partner channel.

### Thread 4 — The Online Returns Spike
Online channel return rates spike to 18% in January 2026 for the Electronics category — double the normal rate — driven by a product defect batch in the AuraSound Pro launch. This connects Snowflake return data to a Confluence returns policy document and a Salesforce case cluster. It is the answer to every "what does policy say about X" hybrid query.

---

## 3. Seed Data Specification

### 3.1 Snowflake — Aura Retail Data Warehouse

**Database:** `OMNIDATA_DB`
**Schemas:** `SALES`, `CUSTOMERS`, `PRODUCTS`, `RETURNS`

---

#### Table: `OMNIDATA_DB.SALES.AURA_SALES`

The primary fact table. One row per day per region per product per channel combination. Approximately 2,160 rows covering October 2025 to March 2026 (6 months × 4 regions × 3 channels × 30 products = realistic size).

| Column | Type | Description |
|---|---|---|
| `SALE_ID` | VARCHAR | Primary key, e.g. `SALE-2026-001` |
| `SALE_DATE` | DATE | Transaction date |
| `GEO_TERRITORY` | VARCHAR | North, South, East, West |
| `CHANNEL` | VARCHAR | Online, Retail, Partner |
| `PRODUCT_SKU` | VARCHAR | e.g. `AURA-HP-001` |
| `PRODUCT_CATEGORY` | VARCHAR | Electronics, Accessories, Cables |
| `ACTUAL_SALES` | NUMBER(12,2) | Revenue in GBP |
| `UNITS_SOLD` | NUMBER | Number of units |
| `AD_SPEND` | NUMBER(10,2) | Marketing spend attributed to this row |
| `DISCOUNT_RATE` | NUMBER(4,2) | Discount percentage applied |

**Key patterns to embed in the data:**

- October–December 2025: All four regions performing normally. North £420k/month, South £380k/month, East £290k/month, West £260k/month. Use a random ±5% variance to make it look real.
- January 2026: North spikes to £510k (AuraSound Pro launch). Online returns also spike but that shows in the RETURNS table.
- February 2026: South drops to £274k (ad spend cut — set `AD_SPEND` to near-zero for South in Feb). All other regions flat.
- March 2026: South partially recovers to £310k. Partner channel revenue falls across South and East (SMB churn beginning).

---

#### Table: `OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE`

| Column | Type | Description |
|---|---|---|
| `PRODUCT_SKU` | VARCHAR | Primary key |
| `PRODUCT_NAME` | VARCHAR | e.g. `AuraSound Pro Headphones` |
| `PRODUCT_CATEGORY` | VARCHAR | Electronics, Accessories, Cables |
| `LAUNCH_DATE` | DATE | When the product was first sold |
| `RRP_GBP` | NUMBER(8,2) | Recommended retail price |
| `CHANNEL_AVAILABILITY` | VARCHAR | All, Online-only, Retail-only |
| `IS_ACTIVE` | BOOLEAN | Whether currently sold |

**Key products to seed:**

| SKU | Name | Category | Launch | RRP |
|---|---|---|---|---|
| `AURA-HP-001` | AuraSound Pro Headphones | Electronics | 2026-01-08 | £149.99 |
| `AURA-HP-002` | AuraSound Lite Headphones | Electronics | 2024-03-01 | £79.99 |
| `AURA-SPK-001` | AuraBoom Portable Speaker | Electronics | 2024-06-15 | £89.99 |
| `AURA-CBL-001` | AuraConnect USB-C Cable 2m | Cables | 2023-01-01 | £12.99 |
| `AURA-ACC-001` | AuraCase Pro Carry Case | Accessories | 2024-09-01 | £34.99 |

Seed 25 more products across the three categories with varied launch dates and price points to make the catalogue realistic.

---

#### Table: `OMNIDATA_DB.RETURNS.RETURN_EVENTS`

| Column | Type | Description |
|---|---|---|
| `RETURN_ID` | VARCHAR | Primary key |
| `RETURN_DATE` | DATE | Date return was processed |
| `SALE_DATE` | DATE | Original sale date |
| `PRODUCT_SKU` | VARCHAR | FK to PRODUCT_CATALOGUE |
| `GEO_TERRITORY` | VARCHAR | North, South, East, West |
| `CHANNEL` | VARCHAR | Online, Retail, Partner |
| `RETURN_REASON` | VARCHAR | Defective, Changed Mind, Wrong Item, Other |
| `REFUND_AMOUNT` | NUMBER(10,2) | Amount refunded in GBP |
| `RETURN_RATE` | NUMBER(4,3) | Calculated rate for that segment |

**Key patterns:**

- Normal return rate: 6–8% across all products and channels October–December 2025.
- January 2026: Online returns of `AURA-HP-001` spike to 18%. `RETURN_REASON = 'Defective'` for ~65% of those returns. This is the AuraSound Pro defect batch.
- February 2026 onwards: Returns normalise after a product patch, falling back to 7%.

---

#### Table: `OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS`

Aggregated monthly customer health metrics by region and segment. One row per month per region per segment.

| Column | Type | Description |
|---|---|---|
| `METRIC_ID` | VARCHAR | Primary key |
| `METRIC_MONTH` | DATE | First day of the month |
| `GEO_TERRITORY` | VARCHAR | North, South, East, West |
| `CUSTOMER_SEGMENT` | VARCHAR | Enterprise, SMB, Consumer |
| `ACTIVE_CUSTOMER_COUNT` | NUMBER | Customers with a purchase that month |
| `NEW_CUSTOMER_COUNT` | NUMBER | First-time buyers |
| `CHURNED_CUSTOMER_COUNT` | NUMBER | Customers who bought previous month but not this one |
| `CHURN_RATE` | NUMBER(4,3) | Churned / total previous month |
| `AVG_ORDER_VALUE` | NUMBER(8,2) | Average transaction value |
| `REPEAT_PURCHASE_RATE` | NUMBER(4,3) | Proportion of customers with 2+ purchases |

**Key patterns:**

- SMB churn rate in South: 4% Oct–Jan, spikes to 11% in February, 14% in March.
- SMB churn rate in East: 3% Oct–Jan, rises to 8% in March (lagging South).
- Enterprise and Consumer segments: flat churn throughout (they are insulated from the price change).
- North Consumer segment: New customer count spikes in January (AuraSound Pro launch driving new buyers).

---

### 3.2 Pinecone — Vector Indexes

**Two serverless indexes:**

#### Index: `omnidata-hybrid` (hybrid search — dense + sparse)
Used for structured data RAG where exact term matching matters alongside semantic similarity. Dense embeddings generated via **Pinecone Inference API** (`multilingual-e5-large`), sparse embeddings via **Pinecone Inference API** (`pinecone-sparse-english-v0`). No local embedding model required.

**Namespace: `schema_store`** — 5 documents (one per Snowflake table)

Each document is an enriched natural language description. Example for `AURA_SALES`:

```
Document ID: schema_AURA_SALES
Text: "Table AURA_SALES tracks daily revenue, money made, total sales,
and income for Aura Retail broken down by geographic region (North,
South, East, West), sales channel (Online, Retail, Partner), and
product. Use this table when the user asks about revenue, earnings,
sales figures, profit, how much money was made, financial performance,
ad spend, discount rates, or units sold by region, product, or channel."
Metadata: { table_name: "AURA_SALES", schema: "SALES",
            schema_hash: "<md5_of_column_list>" }
```

**Namespace: `examples_store`** — 30 documents (verified Q→SQL pairs)

Key examples to include:

```
# Revenue by region
Q: What was total revenue by region last quarter?
SQL: SELECT GEO_TERRITORY, SUM(ACTUAL_SALES) AS TOTAL_REVENUE
     FROM OMNIDATA_DB.SALES.AURA_SALES
     WHERE SALE_DATE >= '2026-01-01' AND SALE_DATE <= '2026-03-31'
     GROUP BY GEO_TERRITORY ORDER BY TOTAL_REVENUE DESC

# Month-on-month comparison
Q: Compare February and March revenue for the South region
SQL: SELECT DATE_TRUNC('month', SALE_DATE) AS MONTH,
     SUM(ACTUAL_SALES) AS REVENUE
     FROM OMNIDATA_DB.SALES.AURA_SALES
     WHERE GEO_TERRITORY = 'South'
     AND SALE_DATE >= '2026-02-01' AND SALE_DATE <= '2026-03-31'
     GROUP BY 1 ORDER BY 1

# Channel breakdown
Q: What is the revenue split by sales channel this year?
SQL: SELECT CHANNEL, SUM(ACTUAL_SALES) AS REVENUE,
     ROUND(SUM(ACTUAL_SALES) * 100.0 / SUM(SUM(ACTUAL_SALES)) OVER(), 1)
     AS PCT_OF_TOTAL
     FROM OMNIDATA_DB.SALES.AURA_SALES
     WHERE SALE_DATE >= '2026-01-01'
     GROUP BY CHANNEL ORDER BY REVENUE DESC

# Top products
Q: Which were the top 5 products by revenue last month?
SQL: SELECT p.PRODUCT_NAME, SUM(s.ACTUAL_SALES) AS REVENUE
     FROM OMNIDATA_DB.SALES.AURA_SALES s
     JOIN OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE p
     ON s.PRODUCT_SKU = p.PRODUCT_SKU
     WHERE s.SALE_DATE >= '2026-03-01' AND s.SALE_DATE <= '2026-03-31'
     GROUP BY p.PRODUCT_NAME ORDER BY REVENUE DESC LIMIT 5

# Return rate
Q: What is the return rate for online electronics this year?
SQL: SELECT PRODUCT_SKU,
     COUNT(*) AS RETURN_COUNT,
     ROUND(AVG(RETURN_RATE) * 100, 1) AS AVG_RETURN_RATE_PCT
     FROM OMNIDATA_DB.RETURNS.RETURN_EVENTS
     WHERE CHANNEL = 'Online' AND RETURN_DATE >= '2026-01-01'
     GROUP BY PRODUCT_SKU ORDER BY RETURN_COUNT DESC

# Churn by segment
Q: What is the churn rate by customer segment in the South?
SQL: SELECT CUSTOMER_SEGMENT, METRIC_MONTH,
     ROUND(CHURN_RATE * 100, 1) AS CHURN_PCT
     FROM OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS
     WHERE GEO_TERRITORY = 'South'
     ORDER BY METRIC_MONTH, CUSTOMER_SEGMENT
```

Seed all 30 examples across the four tables, covering aggregation, filtering, joining, time-series, ranking, and percentage calculations. These are the patterns DeepSeek R1 will learn from.

**Namespace: `salesforce_schema_store`** — 4 documents (one per key Salesforce object)

**Namespace: `salesforce_examples_store`** — 20 documents (verified Q→SOQL pairs)

#### Index: `omnidata-dense` (dense search only, integrated inference)
Used for unstructured text where semantic meaning matters more than exact terms. Created with **integrated inference** (`multilingual-e5-large`) — queries pass raw text directly, Pinecone embeds server-side. No local embedding model required.

**Namespace: `confluence_store`** — ~80 documents (chunked Confluence pages)
**Namespace: `documents_store`** — populated at runtime by user uploads

---

### 3.3 Confluence — Aura Retail Knowledge Base

**Space key:** `AURA`
**Space name:** Aura Retail Internal Knowledge Base

Seed exactly **8 Confluence pages** across two spaces. Every page should reference real numbers, real regions, and real products from your Snowflake data so the hybrid queries feel genuinely connected.

---

**Page 1: Regional Marketing Budget Policy — FY2026**
*Space: Operations*

Content summary to write: Explains the quarterly marketing budget allocation process. Crucially, includes a paragraph stating that in January 2026 the board approved a reallocation of South region's Q1 marketing budget (£180,000) to support the national AuraSound Pro launch campaign. Explicitly states the South region's digital ad spend was paused from 1 February 2026 pending Q2 budget review. This is the smoking gun that explains the South revenue drop. When a user asks "why did South region revenue drop?", this document is retrieved alongside the Snowflake data and the Synthesis Node connects them explicitly.

Key phrases to include: "South region marketing pause", "budget reallocation February 2026", "digital advertising suspended", "Q2 reinstatement pending approval".

---

**Page 2: Customer Refund and Returns Policy — v4.2**
*Space: Customer Operations*

Content summary to write: The official returns policy. States the standard return window is 30 days for consumer purchases, 14 days for Partner channel business purchases. Includes a specific clause that defective products qualify for immediate full refund outside the standard window. Mentions that return rates above 12% for any SKU trigger an automatic product quality review. This document is retrieved when a user asks about the January returns spike — the system can say "per the Returns Policy, the 18% return rate for AuraSound Pro triggered an automatic quality review."

Key phrases to include: "defective product returns", "12% threshold", "automatic quality review", "Partner channel 14-day window", "consumer 30-day window".

---

**Page 3: AuraSound Pro — Product Launch Brief**
*Space: Product*

Content summary to write: The internal launch document for `AURA-HP-001`. States the product launched 8 January 2026 with a £149.99 RRP. Describes the initial quality issue — a firmware defect in batch codes AU-0126-A through AU-0126-F that caused intermittent audio dropout. States engineering deployed an OTA firmware fix on 28 January 2026. Notes that affected units (estimated 2,400 sold) were eligible for replacement or full refund under the defective returns policy. This is the root cause of the January returns spike.

Key phrases to include: "firmware defect", "batch AU-0126", "OTA fix 28 January", "audio dropout", "2,400 affected units", "AuraSound Pro launch".

---

**Page 4: Partner Channel Price Adjustment — February 2026**
*Space: Commercial*

Content summary to write: The memo announcing a 12% price increase on the Partner channel effective 1 February 2026, applied to all Electronics category products. States the rationale as margin recovery following supply chain cost increases in Q4 2025. Acknowledges in the risk section that SMB partners in South and East regions had expressed price sensitivity in Q4 account reviews. This document is the root cause of the SMB churn wave in Salesforce.

Key phrases to include: "Partner channel price increase", "12% uplift February 2026", "SMB price sensitivity", "South and East exposure", "margin recovery".

---

**Page 5: Q1 2026 Commercial Strategy — Board Summary**
*Space: Strategy*

Content summary to write: The board summary for Q1 2026. Highlights AuraSound Pro launch as the strategic priority. Notes the planned South region marketing pause as a deliberate trade-off to fund the launch. Sets a target of 15% revenue growth in North and West regions in Q1 to offset the South reduction. This gives the full strategic context that individual data points don't show — the South drop was intentional at the board level, not a failure.

Key phrases to include: "Q1 2026 priorities", "AuraSound Pro national launch", "South region planned reduction", "North and West growth targets", "strategic trade-off".

---

**Page 6: Customer Success — SMB Retention Playbook**
*Space: Customer Operations*

Content summary to write: The playbook for retaining SMB customers at risk of churn. Defines the trigger conditions (no purchase in 45 days, or a logged price complaint from an account manager). Lists the approved retention offers — a 10% loyalty discount for accounts with 12+ months tenure, a free extended warranty for electronics purchases over £500. States that South and East region SMB accounts should be flagged for proactive outreach in Q1 2026 given the Partner price change. This document becomes actionable when paired with a Salesforce query showing which SMB accounts are at high churn risk.

Key phrases to include: "SMB retention", "45-day inactivity trigger", "10% loyalty discount", "South and East priority outreach", "Partner price change impact".

---

**Page 7: Data Glossary — Aura Retail Metrics Definitions**
*Space: Operations*

Content summary to write: The internal glossary of metric definitions. Defines: Total Sales (sum of ACTUAL_SALES, GBP, before returns), Net Revenue (Total Sales minus Refunds), Active Customer (at least one purchase in the measurement month), Churn Rate (customers who purchased in month N-1 but not in month N, divided by total month N-1 customers), Return Rate (returns divided by units sold for the same SKU and period), Partner Channel (B2B resellers and distributors, not direct retail). This page reinforces the Metric Dictionary and should be synced into `confluence_store` — it validates your semantic layer.

---

**Page 8: Monthly Trading Update — February 2026**
*Space: Operations*

Content summary to write: The internal trading update for February. Acknowledges the South region revenue shortfall (-28% vs plan). Attributes it explicitly to the marketing pause. Notes AuraSound Pro returns are declining following the firmware fix. Flags SMB churn risk as an emerging concern following Partner price increase. Contains a table of actual vs planned revenue by region. This is the richest document for demo purposes — it is a real-world example of the exact kind of internal report that a non-technical user would normally have to read manually, and OmniData can answer questions about it instantly.

---

### 3.4 Salesforce Developer Edition — Aura Retail CRM

**Objects to create/seed:**

#### Standard Object: `Account`

Seed **35 accounts** representing Aura Retail's B2B partners and enterprise customers.

**Custom fields to create in Salesforce Setup before seeding:**

| Field | Type | Values |
|---|---|---|
| `ChurnRisk__c` | Picklist | High, Medium, Low |
| `Region__c` | Text | North, South, East, West |
| `CustomerSegment__c` | Picklist | Enterprise, SMB, Consumer |
| `LastPurchaseDate__c` | Date | Date of most recent order |
| `AnnualContractValue__c` | Currency | Annual value in GBP |
| `PartnerTier__c` | Picklist | Gold, Silver, Bronze |

**Account distribution to seed:**

| Region | Segment | Count | ChurnRisk distribution |
|---|---|---|---|
| North | Enterprise | 4 | All Low |
| North | SMB | 6 | 5 Low, 1 Medium |
| South | Enterprise | 3 | 2 Low, 1 Medium |
| South | SMB | 7 | 2 Low, 2 Medium, 3 High |
| East | Enterprise | 3 | All Low |
| East | SMB | 5 | 2 Low, 1 Medium, 2 High |
| West | Enterprise | 3 | All Low |
| West | SMB | 4 | 3 Low, 1 Medium |

This distribution means that "show me high churn risk accounts" returns 5 accounts — all SMB, all South or East — which perfectly maps to Thread 3 of your narrative.

**Sample high-churn accounts to name specifically** (so they feel real in the demo):

- Brightside Electronics Ltd — South, SMB, High churn, £48,000 ACV, last purchase 12 Feb 2026
- Nexus Office Solutions — South, SMB, High churn, £32,000 ACV, last purchase 8 Feb 2026
- Eastern Trade Supplies — East, SMB, High churn, £27,500 ACV, last purchase 15 Feb 2026

#### Standard Object: `Opportunity`

Seed **20 open opportunities** representing active sales deals.

| Field | Note |
|---|---|
| `Name` | e.g. "Brightside Q2 Renewal" |
| `AccountId` | Link to Account above |
| `Amount` | GBP value |
| `StageName` | Prospecting, Qualification, Proposal, Negotiation |
| `CloseDate` | Future date |
| `Region__c` | Inherited from Account |

Make sure total open pipeline value in North is ~£340,000 and South is ~£95,000 — this contrast tells the pipeline story clearly in one SOQL query.

#### Standard Object: `Case`

Seed **40 support cases** representing customer complaints and returns.

| Field | Note |
|---|---|
| `Subject` | e.g. "AuraSound Pro Audio Dropout Issue" |
| `AccountId` | Link to Account |
| `Status` | Open, In Progress, Closed |
| `Priority` | High, Medium, Low |
| `Origin` | Web, Phone, Email |
| `Description` | Detailed description mentioning the specific issue |
| `CreatedDate` | Concentrate AuraSound Pro defect cases in Jan 2026 |
| `ProductSKU__c` | Custom field — SKU of product related to case |

Seed 18 cases in January 2026 with Subject containing "AuraSound Pro" and Description mentioning "audio dropout" or "firmware". This is what makes the query "what are the main customer complaints this year?" return a clear pattern.

---

## 4. System Architecture & Core Flows

The backend is orchestrated using **LangGraph** with a typed `StateGraph`. Full node execution order:

```
User Query
    ↓
Node 0: Intent Router              — classifies intent, sets branch flags
    ↓
Node 1: Clarification Node         — temporal resolution
    ↓                                metric alias resolution
    ↓                                E2B pre-warm if sql_likely = true
    ↓
┌──────────────────────────────────────────────────────────────┐
│  Branch 1           Branch 2               Branch 3           │
│  Snowflake SQL      ├─ 2A: Confluence RAG  Tavily Web         │
│                     └─ 2B: Salesforce SOQL                    │
└──────────────────────────────────────────────────────────────┘
    ↓
Node 2: Synthesis Node             — merge outputs, draft answer
    ↓                                strip SQL/SOQL jargon (Job 2)
Node 3: Semantic Output Validator  — fires only if rag_present = true
    ↓                                audit RAG jargon, log substitutions
User
```

---

### 4.1 Node 0: The Intent Router

- **Model:** `llama-3.3-8b` via Groq API
- **Output to state:**

```json
{
  "branches": ["sql", "rag_confluence"],
  "rag_sources": ["confluence", "documents"],
  "sql_likely": true,
  "rag_present": true,
  "web_needed": false,
  "original_query": "What does our returns policy say about the spike we're seeing online?"
}
```

---

### 4.2 Node 1: Query Clarification & Normalisation

#### Temporal Resolution

| User phrase | Resolved to |
|---|---|
| "this month" | `date >= '2026-04-01' AND date <= '2026-04-30'` |
| "last quarter" | `date >= '2026-01-01' AND date <= '2026-03-31'` |
| "YTD" | `date >= '2026-01-01' AND date <= today` |
| "recent" | `date >= today - 30 days` |
| "last year" | `date >= '2025-01-01' AND date <= '2025-12-31'` |
| "last month" | First and last day of the previous calendar month |

#### Metric Dictionary Lookup

- Unambiguous match → silent resolution + UI note
- Ambiguous match → single clarifying question, two clickable options
- No match → proceed unchanged

#### Conditional E2B Pre-Warming

Fires only when `sql_likely = true`. Non-SQL queries never touch E2B.

```python
if state["sql_likely"] and not app.state.warm_sandbox:
    asyncio.create_task(prewarm_sandbox(app.state))
```

---

### 4.3 The Metric Dictionary

`backend/src/config/metric_dictionary.yaml` — loaded at startup, used by Nodes 1, 2, and 3. Exposed at `/metrics` for the UI Glossary.

```yaml
metrics:

  revenue:
    display_name: "Total Sales"
    aliases: ["money", "income", "earnings", "sales", "turnover",
              "how much we made", "financials", "revenue"]
    canonical_column: "ACTUAL_SALES"
    table: "OMNIDATA_DB.SALES.AURA_SALES"
    unit: "GBP"
    description: "Total transaction value in GBP before returns."
    ambiguous: false
    jargon_terms: ["ACTUAL_SALES", "actual_sales"]

  net_revenue:
    display_name: "Net Revenue"
    aliases: ["net sales", "revenue after returns", "net income"]
    description: "Total Sales minus total refunds in the same period."
    ambiguous: false
    jargon_terms: []

  performance:
    display_name: null
    aliases: ["results", "numbers", "how we did", "metrics", "kpis",
              "performance"]
    resolves_to: ["revenue", "unit_sales", "churn"]
    ambiguous: true
    clarification_prompt: "Which metric for 'performance'?
      Options: Total Sales (GBP), Units Sold, or Customer Churn Rate."

  churn:
    display_name: "Customer Churn Rate"
    aliases: ["lost customers", "customer loss", "attrition",
              "drop-off", "cancellations", "churn"]
    canonical_column: "CHURN_RATE"
    table: "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS"
    unit: "percentage"
    description: "Percentage of customers from the prior month who
      did not make a purchase in the current month."
    ambiguous: false
    jargon_terms: ["CHURN_RATE", "churn_rate", "CHURNED_CUSTOMER_COUNT",
                   "ChurnRisk__c"]

  active_customers:
    display_name: "Active Customers"
    aliases: ["active customers", "engaged users", "active users",
              "customers this month", "buying customers"]
    canonical_column: "ACTIVE_CUSTOMER_COUNT"
    table: "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS"
    unit: "count"
    description: "Customers who made at least one purchase in the period."
    ambiguous: false
    jargon_terms: ["ACTIVE_CUSTOMER_COUNT", "IS_ACTIVE", "active_customer_count"]

  return_rate:
    display_name: "Return Rate"
    aliases: ["returns", "product returns", "refunds rate",
              "return percentage", "how many came back"]
    canonical_column: "RETURN_RATE"
    table: "OMNIDATA_DB.RETURNS.RETURN_EVENTS"
    unit: "percentage"
    description: "Percentage of units sold that were subsequently returned."
    ambiguous: false
    jargon_terms: ["RETURN_RATE", "return_rate", "RETURN_EVENTS"]

  pipeline_value:
    display_name: "Sales Pipeline Value"
    aliases: ["deals", "opportunities", "sales pipeline",
              "potential revenue", "open deals", "pipeline"]
    canonical_object: "Opportunity"
    salesforce_field: "Amount"
    source: "salesforce"
    unit: "GBP"
    description: "Total value of open Salesforce deals not yet
      marked as won or lost."
    ambiguous: false
    jargon_terms: ["Opportunity", "Amount", "StageName",
                   "Closed Won", "Closed Lost", "OpportunityId"]

  units_sold:
    display_name: "Units Sold"
    aliases: ["units", "volume", "how many sold", "quantity sold",
              "number sold"]
    canonical_column: "UNITS_SOLD"
    table: "OMNIDATA_DB.SALES.AURA_SALES"
    unit: "count"
    description: "Number of individual product units sold in the period."
    ambiguous: false
    jargon_terms: ["UNITS_SOLD", "units_sold"]
```

---

### 4.4 Branch 1: Snowflake SQL

Full pipeline: Schema RAG (Pinecone hybrid, `schema_store` namespace) → Few-Shot RAG (Pinecone hybrid, `examples_store` namespace) → Dynamic Prompt → DeepSeek R1 70B → `sqlglot` validation → Confidence Scoring → E2B Execution → Visualisation.

**Pinecone hybrid query pattern (server-side embeddings via Pinecone Inference API):**

```python
from pinecone import Pinecone

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(os.environ["PINECONE_HYBRID_INDEX"])

# Generate dense + sparse embeddings via Pinecone Inference API
# No local model, no BM25Encoder — all server-side
dense_embedding = pc.inference.embed(
    model="multilingual-e5-large",
    inputs=[user_query],
    parameters={"input_type": "query"}
)[0].values

sparse_embedding = pc.inference.embed(
    model="pinecone-sparse-english-v0",
    inputs=[user_query],
    parameters={"input_type": "query"}
)[0]

results = index.query(
    vector=dense_embedding,
    sparse_vector=sparse_embedding.sparse_values,
    top_k=3,
    namespace="schema_store",
    include_metadata=True
)
```

**Confidence scoring — three signals:**

| Signal | Weight | Low threshold |
|---|---|---|
| Pinecone top-1 score | 40% | < 0.75 |
| Retry count | 40% | 1 retry = half score, 2 = zero |
| Result row sanity | 20% | Zero rows on non-aggregate |

Tiers: Green ≥ 0.8, Amber 0.5–0.79, Red < 0.5.

---

### 4.5 Branch 2: Unstructured Data & CRM

#### Sub-branch 2A: Confluence & Document RAG

**Pinecone dense query pattern (integrated inference — raw text in, results out):**

```python
index = pc.Index(os.environ["PINECONE_DENSE_INDEX"])

# Index has integrated inference (multilingual-e5-large)
# No local embedding needed — pass raw text directly
results = index.search(
    namespace="confluence_store",
    query={"inputs": {"text": user_query}, "top_k": 3}
)
```

Parallel query against `documents_store` namespace. Top 3 from each merged and re-ranked. Top 5 overall to Synthesis Node.

**Confluence MCP Server** — Cloud Run service. Endpoints:
```
GET  /confluence/search?query={text}&space_key={key}
POST /confluence/sync?space_key={key}
```

#### Sub-branch 2B: Salesforce SOQL

**Pinecone hybrid query pattern** — same as Branch 1 but against `salesforce_schema_store` and `salesforce_examples_store` namespaces.

**SOQL Generation:** `deepseek-r1-distill-llama-70b` via Groq, temperature 0.0.

**SOQL Validator constraints:**
- SELECT only — no DML
- `LIMIT` mandatory, max 200
- Aggregate functions require `GROUP BY`
- Object names checked against known schema

**Key SOQL examples to seed:**

```sql
-- High churn risk accounts by region
SELECT Name, Region__c, AnnualContractValue__c,
       ChurnRisk__c, LastPurchaseDate__c
FROM Account
WHERE ChurnRisk__c = 'High'
ORDER BY AnnualContractValue__c DESC
LIMIT 20

-- Open pipeline value by region
SELECT Region__c, SUM(Amount) AS PIPELINE_VALUE,
       COUNT(Id) AS DEAL_COUNT
FROM Opportunity
WHERE StageName NOT IN ('Closed Won', 'Closed Lost')
GROUP BY Region__c
ORDER BY PIPELINE_VALUE DESC

-- Recent support cases by product
SELECT Subject, Account.Name, Priority, Status, CreatedDate
FROM Case
WHERE CreatedDate >= 2026-01-01T00:00:00Z
ORDER BY CreatedDate DESC
LIMIT 50
```

**Salesforce MCP Server** — Cloud Run service. Endpoints:
```
POST /salesforce/query   Body: { "soql": "..." }
GET  /salesforce/schema?object={ObjectName}
```

---

### 4.6 Branch 3: External Market Intelligence

#### Step 1: Query Rewriter

- **Model:** `llama-3.3-8b` via Groq
- Strips internal context, injects resolved dates, produces a public search query

**Example rewrites for Aura Retail:**

| User question | Rewritten query |
|---|---|
| "Why did our South region underperform in February?" | "UK South retail consumer spending decline February 2026 causes" |
| "What macro factors explain our SMB churn spike?" | "UK SMB customer churn increase 2026 price sensitivity" |
| "Is our pricing competitive for consumer electronics?" | "UK consumer electronics pricing benchmark mid-market 2026" |
| "What's happening in the headphones market?" | "UK headphones market trends Q1 2026 consumer demand" |

#### Step 2: Tavily Search

Top 3 results. Source URLs and publication dates captured for citation.

#### Step 3: Summarisation

Handled inside the Synthesis Node — no separate LLM call.

---

### 4.7 Node 2: Synthesis Node

- **Model:** `llama-3.3-70b-versatile` via Groq
- **Two jobs in one prompt:** construct the answer + strip SQL/SOQL jargon
- Output includes `draft_response` and `jargon_audit_clean` boolean

**Jargon substitution list** dynamically generated from Metric Dictionary `jargon_terms` fields at runtime.

---

### 4.8 Node 3: Semantic Output Validator

- **Model:** `llama-3.3-8b` via Groq
- **Fires only when:** `rag_present = true` (any Branch 2 output present)
- **Does not fire for:** pure SQL queries, pure web queries
- **Latency:** 300–600ms on `llama-3.3-8b` — imperceptible against Branch 2 total latency

**Process:** Scan draft response for all `jargon_terms` from Metric Dictionary plus Salesforce API identifiers (`__c` suffix, `Id` suffix, ALL_CAPS object names) and SQL keywords used as nouns. Rewrite using `display_name` values. Output cleaned response + substitution log.

**Substitution log** stored in state, shown in Transparency Dashboard **Language tab**.

---

## 5. Complete Node Execution Summary

| Node | Model | Fires when | Purpose |
|---|---|---|---|
| Node 0: Intent Router | Llama 3.3 8B | Always | Classify, set routing flags |
| Node 1: Clarification | Rule-based + dict | Always | Resolve dates, metrics, pre-warm |
| Branch 1: Snowflake | DeepSeek R1 70B | `sql_likely = true` | Text-to-SQL → execute → visualise |
| Branch 2A: Confluence | Vector search | `rag_confluence` flagged | Retrieve policy/wiki content |
| Branch 2B: Salesforce | DeepSeek R1 70B | `rag_salesforce` flagged | Text-to-SOQL → execute |
| Branch 3: Web | Llama 3.3 8B + Tavily | `web_needed = true` | Rewrite → search → summarise |
| Node 2: Synthesis | Llama 3.3 70B | Always | Merge, draft, strip jargon |
| Node 3: Validator | Llama 3.3 8B | `rag_present = true` | Audit RAG jargon, log subs |

---

## 6. Pinecone Index Architecture

```
Index: omnidata-hybrid  (serverless, us-east-1, hybrid search)
│   Dense model:  multilingual-e5-large      (via Pinecone Inference API)
│   Sparse model: pinecone-sparse-english-v0 (via Pinecone Inference API)
├── namespace: schema_store           (5 docs — Snowflake table descriptions)
├── namespace: examples_store         (30 docs — Q→SQL pairs)
├── namespace: salesforce_schema_store (4 docs — Salesforce object descriptions)
└── namespace: salesforce_examples_store (20 docs — Q→SOQL pairs)

Index: omnidata-dense   (serverless, us-east-1, integrated inference)
│   Model: multilingual-e5-large (integrated — raw text in, vectors auto-generated)
├── namespace: confluence_store        (~80 docs — Confluence page chunks)
└── namespace: documents_store         (populated at runtime by uploads)
```

**Idempotent upsert pattern** — always use deterministic IDs to prevent duplicates on re-seeding:

```python
doc_id = f"{namespace}_{table_name}_chunk_{chunk_index}"
# Re-running the seed script overwrites, never duplicates
```

**Vector count estimate:** schema_store (5) + examples_store (30) + sf_schema (4) + sf_examples (20) + confluence (80) = ~139 vectors before user uploads. Well within the 100k free limit.

---

## 7. Deployment Architecture

| Component | Service | Tier |
|---|---|---|
| Frontend (Next.js) | Vercel | Free |
| Backend / LangGraph (FastAPI) | Google Cloud Run | Free ($300 GCP credit) |
| Confluence MCP server | Google Cloud Run | Free (same credit) |
| Salesforce MCP server | Google Cloud Run | Free (same credit) |
| Snowflake | Snowflake | 30-day trial ($400 credit) |
| Salesforce CRM | Salesforce Developer Edition | Free (permanent) |
| Confluence | Confluence Cloud | Free (up to 10 users) |
| Vector database | Pinecone serverless | Free (Starter, 100k vectors) |
| Code sandbox | E2B Cloud | Free tier |
| LLM inference | Groq API | Free tier |
| Web search | Tavily API | Free (1k/mo) |

**Total cost during hackathon: £0**

### Google Cloud Run Configuration

Each service (backend, Confluence MCP, Salesforce MCP) is a separate Cloud Run service:

```yaml
# cloud-run-backend.yaml
service: omnidata-backend
region: asia-south1         # Mumbai — optimal for India-based judges
min-instances: 1            # Prevents cold start — critical for demo
max-instances: 3
memory: 2Gi
cpu: 1
```

Set `min-instances: 1` on all three services. This keeps containers warm and prevents the 8–12 second cold start that would kill your demo. The free tier allows 1 always-on instance per service.

---

## 8. Demo Script

The demo script is a first-class deliverable. Rehearse these 5 queries until you can run them in under 8 minutes.

### Query 1 — Trust anchor (Branch 1 only)
**"What was total sales by region in Q1 2026?"**
Expected: Bar chart, green confidence, SQL tab visible, date resolution note showing Q1 resolved dates. Establishes the Transparency Dashboard immediately.

### Query 2 — The showstopper (Branch 1 + Branch 2A)
**"Why did the South region underperform in February, and what does our policy say about it?"**
Expected: South region revenue drop from Snowflake + Regional Marketing Budget Policy excerpt from Confluence. Two source chips. System connects the data drop to the marketing pause document explicitly. This is the moment judges remember.

### Query 3 — The Semantic Validator in action (Branch 2B)
**"Which of our customers are most at risk of leaving?"**
Expected: Salesforce SOQL query for high churn accounts. Language tab shows `ChurnRisk__c` rewritten to "Churn Risk Score", `AnnualContractValue__c` rewritten to "Annual Contract Value". Click Language tab to show live. This proves the Clarity pillar visibly.

### Query 4 — Metric Dictionary clarification (Branch 1)
**"How did performance look this quarter?"**
Expected: Clarification buttons appear — "Total Sales (GBP)", "Units Sold", "Customer Churn Rate". User clicks Total Sales. Query proceeds. Shows the semantic layer in action before a single query runs.

### Query 5 — Full system (Branch 1 + Branch 3)
**"What macro factors explain the SMB churn we're seeing in the South?"**
Expected: Snowflake churn data for South SMB segment + Tavily results about UK SMB price sensitivity in 2026. Branch 3 query rewrite visible in the Thinking panel. Demonstrates all three pillars simultaneously.

---

## 9. Tech Stack

| Category | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS, shadcn/ui |
| Backend | Python 3.11, FastAPI, LangGraph |
| LLM Inference | Groq API (Llama 3.3 8B, DeepSeek R1 70B, Llama 3.3 70B) — multiple API keys with rotation |
| Dense embeddings | Pinecone Inference API (`multilingual-e5-large`, server-side — no local model) |
| Sparse embeddings | Pinecone Inference API (`pinecone-sparse-english-v0`, server-side — no BM25Encoder) |
| Vector database | Pinecone serverless (hybrid + dense indexes with integrated inference) |
| Orchestration | LangGraph (typed StateGraph) |
| Structured data | Snowflake (30-day trial) |
| Snowflake connector | `snowflake-connector-python` |
| CRM | Salesforce Developer Edition |
| Salesforce connector | `simple-salesforce` |
| Knowledge base | Confluence Cloud |
| Confluence connector | Confluence REST API (API token) |
| SQL/SOQL validation | `sqlglot` |
| Code sandbox | E2B Cloud (SQL branch only) |
| Web search | Tavily API |
| MCP transport | `mcp` Python SDK (FastAPI microservices) |
| Config | YAML (metric_dictionary, schema_descriptions) |
| Deployment | Google Cloud Run (backend + MCP servers), Vercel (frontend) |

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
│   │       └── LanguageTab.tsx
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
│   │   │   └── branch_web.py
│   │   ├── synthesis/
│   │   │   └── synthesis_node.py
│   │   ├── validation/
│   │   │   ├── semantic_validator.py
│   │   │   ├── sql_validator.py
│   │   │   ├── soql_validator.py
│   │   │   └── confidence_scorer.py
│   │   ├── vector/
│   │   │   ├── pinecone_client.py         # shared Pinecone client
│   │   │   ├── schema_store.py
│   │   │   ├── examples_store.py
│   │   │   ├── confluence_store.py
│   │   │   ├── documents_store.py
│   │   │   ├── salesforce_schema_store.py
│   │   │   ├── salesforce_examples_store.py
│   │   │   └── schema_hasher.py
│   │   ├── sandbox/
│   │   │   ├── e2b_runner.py
│   │   │   └── sandbox_pool.py
│   │   ├── snowflake/
│   │   │   └── connector.py
│   │   └── salesforce/
│   │       └── connector.py
│   ├── seed/
│   │   ├── snowflake_seed.py              # Seeds all 4 Snowflake tables
│   │   ├── pinecone_seed.py               # Seeds all 6 namespaces
│   │   ├── salesforce_seed.py             # Seeds Accounts, Opportunities, Cases
│   │   └── data/
│   │       ├── aura_sales.csv
│   │       ├── product_catalogue.csv
│   │       ├── return_events.csv
│   │       ├── customer_metrics.csv
│   │       ├── schema_descriptions.json
│   │       ├── sql_examples.json
│   │       ├── soql_examples.json
│   │       └── salesforce_accounts.json
│   ├── tests/
│   │   ├── test_sql_validator.py
│   │   ├── test_soql_validator.py
│   │   ├── test_schema_rag.py
│   │   ├── test_clarification_node.py
│   │   ├── test_temporal_resolver.py
│   │   ├── test_confidence_scorer.py
│   │   └── test_semantic_validator.py
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

Note the `seed/` directory as a first-class folder. Seeding is a repeatable, scripted operation — not a manual one-time task. Each seed script is idempotent (safe to run multiple times) and documented in the README under a "Seeding Demo Data" section.

---

## 11. Environment Variables Reference

```bash
# Groq — multiple keys, rotated per-request to avoid rate limits
GROQ_API_KEY_1=
GROQ_API_KEY_2=
GROQ_API_KEY_3=

# Pinecone
PINECONE_API_KEY=
PINECONE_HYBRID_INDEX=         # omnidata-hybrid
PINECONE_DENSE_INDEX=          # omnidata-dense
PINECONE_ENVIRONMENT=          # e.g., us-east-1-aws

# Snowflake
SNOWFLAKE_ACCOUNT=             # e.g., xy12345.eu-west-1
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=           # e.g., COMPUTE_WH
SNOWFLAKE_DATABASE=            # OMNIDATA_DB
SNOWFLAKE_SCHEMA=              # SALES

# Salesforce
SALESFORCE_USERNAME=
SALESFORCE_PASSWORD=
SALESFORCE_SECURITY_TOKEN=
SALESFORCE_CONSUMER_KEY=
SALESFORCE_CONSUMER_SECRET=

# Confluence
CONFLUENCE_BASE_URL=           # https://yourorg.atlassian.net
CONFLUENCE_API_TOKEN=
CONFLUENCE_USER_EMAIL=
CONFLUENCE_DEFAULT_SPACE=      # AURA

# E2B
E2B_API_KEY=

# Tavily
TAVILY_API_KEY=

# Google Cloud
GCP_PROJECT_ID=
GCP_REGION=                    # europe-west2

# MCP server URLs (injected by Cloud Run on deploy)
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
| `README.md` with overview, features, install, tech stack, usage | Written last, after everything is built |
| `requirements.txt` and `package.json` | One per service |
| `.env.example` with all keys, no real values | See Section 11 |
| No hardcoded secrets | All via `os.environ` |
| `git commit -s` DCO sign-off on every commit | Apache License 2.0 |
| Repository private during hackathon | Make public after review |
| Logical folder structure | See Section 10 |
| All listed features working and honest | Label Salesforce/Confluence as seeded demo environments |
| Tests in `tests/` directory | 7 test files covering all critical paths |
| Architecture diagram in `docs/` | Embed inline in README |
| Seed scripts in `seed/` directory | Documented in README under "Seeding Demo Data" |
| No plagiarism, original integration work | Open-source libraries permitted |

---

## 13. Known Limitations & Honest Scope

- **Snowflake data:** Pre-seeded synthetic data for Aura Retail (fictional company). Not real customer data.
- **Salesforce Developer Edition:** Seeded with fictional accounts and cases. Not real CRM data.
- **Confluence:** One space pre-loaded with 8 synthetic policy documents. Not a real knowledge base.
- **No user authentication:** Single-tenant for demo purposes.
- **E2B concurrency:** One pre-warmed sandbox. Concurrent SQL requests cause the second to cold-start.
- **Metric Dictionary:** Manually maintained YAML. No automated sync.
- **Confluence sync:** Manual trigger only.
- **Semantic Validator:** Audits final response text only, not intermediate reasoning tokens.

---

## 14. Future Improvements

- Scheduled Confluence sync (Cloud Scheduler cron)
- Salesforce OAuth 2.0 web flow
- Multi-tenant auth with Pinecone namespace-per-team isolation
- Snowflake + Salesforce metadata auto-ingestion for Metric Dictionary
- SharePoint / OneDrive as third knowledge source
- E2B sandbox pool for concurrent requests
- Redis query result caching
- Fine-tuned embedding model on financial services terminology
- Semantic Validator feedback loop to improve Metric Dictionary over time