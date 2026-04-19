# 03 — SQL Branch & Snowflake

## Overview

The SQL Branch is OmniData's primary data engine. It translates natural-language questions into validated SQL, executes them against a live Snowflake warehouse, and generates AI-powered Plotly visualizations in an E2B sandbox.

## End-to-End Flow

```mermaid
flowchart TD
    Q["User Question"] --> CR["Complexity Router<br/><i>Simple vs Complex</i>"]

    CR -->|"Simple"| SQ["Single Sub-Query"]
    CR -->|"Complex"| DQ["Decompose into 2–3<br/>focused sub-queries"]

    SQ --> GEN
    DQ --> GEN

    GEN["SQL Generation<br/><i>Llama 3.3 70B</i>"] --> EX["Execute on Snowflake"]

    EX -->|"Success"| VIZ["E2B Visualization"]
    EX -->|"Error"| RET{"Retry count < 2?"}

    RET -->|"Yes"| FIX["Feed error to LLM<br/>for correction"]
    FIX --> EX
    RET -->|"No"| FAIL["Return error message"]

    VIZ --> CONF["Confidence Scoring"]
    CONF --> OUT["Return SQL output<br/>+ charts + data"]
```

## Query Decomposition

Complex multi-dimensional questions are broken down before SQL generation:

```mermaid
flowchart LR
    Q["Why did revenue drop<br/>and how is churn trending?"] --> LLM["Complexity LLM"]

    LLM --> SQ1["Sub-Q1: Revenue by region<br/>for date range<br/><i>chart_hint: bar</i>"]
    LLM --> SQ2["Sub-Q2: Churn rate trend<br/>over last 6 months<br/><i>chart_hint: line</i>"]

    SQ1 --> SQL1["SELECT REGION, SUM(ACTUAL_SALES)..."]
    SQ2 --> SQL2["SELECT MONTH, AVG(CHURN_RATE)..."]
```

The LLM responds with a JSON payload:

```json
{
  "complexity": "complex",
  "reasoning": "Spans revenue and churn — two unrelated dimensions",
  "sub_queries": [
    {"question": "Revenue breakdown by region for Q1 2026", "chart_hint": "bar"},
    {"question": "Monthly churn rate trend Oct 2025 to Mar 2026", "chart_hint": "line"}
  ]
}
```

## Schema-Aware SQL Generation

Every SQL query is generated with full schema context retrieved from Pinecone:

```mermaid
sequenceDiagram
    participant SQL as SQL Branch
    participant PC as Pinecone (omnidata-hybrid)
    participant LLM as Groq (Llama 3.3 70B)
    participant SF as Snowflake

    SQL->>PC: Search schema_store (question)
    PC-->>SQL: Top 3 table descriptions with columns
    SQL->>PC: Search examples_store (question)
    PC-->>SQL: Top 3 verified Q→SQL pairs
    SQL->>LLM: Generate SQL with schema + examples + date context
    LLM-->>SQL: SQL query
    SQL->>SF: Execute SQL
    SF-->>SQL: Result rows
```

## E2B Visualization Pipeline

After SQL returns data, an AI-generated Python script runs in an isolated E2B sandbox:

```mermaid
sequenceDiagram
    participant SQL as SQL Branch
    participant LLM as Groq (Llama 3.3 70B)
    participant E2B as E2B Sandbox

    SQL->>LLM: Generate Plotly code for this data + chart_hint
    LLM-->>SQL: Python script (Plotly figure → JSON)
    SQL->>E2B: Execute Python in sandbox
    E2B-->>SQL: Plotly JSON figure
    SQL->>SQL: Embed chart JSON in response
```

The generated visualizations use OmniData's branded color palette and are returned as Plotly JSON objects that the frontend renders interactively.

## Available Tables

| Table | Schema | Rows | Key Columns |
|-------|--------|------|-------------|
| `AURA_SALES` | `SALES` | 2,160 | `SALE_DATE`, `REGION`, `CHANNEL`, `PRODUCT_NAME`, `ACTUAL_SALES`, `UNITS_SOLD` |
| `PRODUCT_CATALOGUE` | `PRODUCTS` | 30 | `SKU`, `PRODUCT_NAME`, `CATEGORY`, `LIST_PRICE` |
| `RETURN_EVENTS` | `RETURNS` | 450 | `RETURN_DATE`, `PRODUCT_NAME`, `REGION`, `RETURN_REASON`, `RETURN_RATE` |
| `CUSTOMER_METRICS` | `CUSTOMERS` | 72 | `MONTH`, `REGION`, `SEGMENT`, `CHURN_RATE`, `REPEAT_PURCHASE_RATE` |

## Error Recovery

The SQL branch implements a retry loop with LLM-powered error correction:

1. **Attempt 1:** Execute generated SQL
2. **On failure:** Feed the Snowflake error message back to the LLM with the failed query
3. **Attempt 2:** LLM generates a corrected SQL query
4. **On failure:** Return a graceful error response with the error details
5. **Confidence impact:** Retry count feeds into the confidence score (1.0 → 0.5 → 0.0)
