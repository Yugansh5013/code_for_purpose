# 01 — System Overview

## High-Level Architecture

OmniData is a multi-agent AI platform that translates plain-English business questions into verified, jargon-free insights pulled from five enterprise data sources simultaneously.

```mermaid
graph TB
    subgraph Client["Frontend — Next.js 14"]
        UI["Chat Interface"]
        TP["Transparency Panel"]
        CH["Plotly Charts"]
        GL["Metric Glossary"]
    end

    subgraph Server["Backend — FastAPI"]
        SSE["/api/chat — SSE Stream"]

        subgraph Pipeline["LangGraph StateGraph"]
            IR["Intent Router<br/><i>Llama 3.3 70B</i>"]
            CL["Clarification Node"]

            subgraph Branches["Data Branches"]
                B1["SQL Branch"]
                B2["Salesforce Branch"]
                B3["RAG Branch"]
                B4["Web Branch"]
            end

            MG["Merge Node"]
            SY["Synthesis Node<br/><i>Llama 3.3 70B</i>"]
            SV["Semantic Validator<br/><i>Llama 3.1 8B</i>"]
        end
    end

    subgraph External["External Services"]
        SF["Snowflake<br/>Data Warehouse"]
        PC["Pinecone<br/>Vector DB"]
        GQ["Groq<br/>LLM Inference"]
        E2["E2B<br/>Code Sandbox"]
        TV["Tavily<br/>Web Search"]
        SC["Salesforce<br/>CRM"]
    end

    UI -->|"SSE"| SSE
    SSE --> IR
    IR --> CL
    CL --> B1 & B2 & B3 & B4
    B1 & B2 & B3 & B4 --> MG
    MG --> SY
    SY --> SV
    SV -->|"Stream"| UI

    B1 --> SF & PC & E2
    B2 --> PC & SC
    B3 --> PC
    B4 --> TV
    IR & SY & SV --> GQ

    SSE --> TP & CH
```

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Frontend | Next.js 14, React 18, TypeScript | SSE streaming chat UI |
| Styling | Tailwind CSS 3, Material Symbols | Ethereal design system |
| Charts | Plotly.js (via E2B) | AI-generated visualizations |
| State | Zustand | Global state management |
| Backend | FastAPI, Uvicorn, Python 3.11 | REST + SSE server |
| Orchestration | LangGraph | Multi-agent pipeline |
| LLM | Groq (Llama 3.3 70B + 3.1 8B) | Intent, SQL, synthesis, validation |
| Vector DB | Pinecone Serverless (2 indexes) | Schema RAG, document retrieval, CRM |
| Warehouse | Snowflake (4 schemas, 4 tables) | Structured business data |
| Web Search | Tavily API | Live market intelligence |
| Sandbox | E2B | Secure Python code execution |
| Deploy | Google Cloud Run, Docker | Serverless containers |

## Data Flow Summary

1. **User** types a question in the chat UI
2. **SSE** connection opens to `/api/chat`
3. **Intent Router** classifies the question and selects branch(es)
4. **Clarification Node** resolves dates, metrics, and ambiguity
5. **Branches** execute sequentially: SQL → Salesforce → RAG → Web
6. **Merge Node** collects all branch outputs
7. **Synthesis Node** generates a unified natural-language narrative
8. **Semantic Validator** strips jargon from the response
9. **Frontend** renders the narrative, charts, data, and transparency tabs

## Pinecone Vector Architecture

```mermaid
graph LR
    subgraph Hybrid["Index: omnidata-hybrid"]
        SS["ns: schema_store<br/>5 table descriptions"]
        ES["ns: examples_store<br/>30 Q → SQL pairs"]
    end

    subgraph Dense["Index: omnidata-dense"]
        CF["ns: confluence<br/>Policy docs, memos"]
        SFR["ns: salesforce<br/>Pre-indexed CRM records"]
    end

    B1["SQL Branch"] -->|"Schema RAG"| SS
    B1 -->|"Few-shot"| ES
    B3["RAG Branch"] -->|"Doc search"| CF
    B2["CRM Branch"] -->|"Vector fallback"| SFR
```

## Snowflake Database Schema

```
OMNIDATA_DB
├── SALES
│   └── AURA_SALES          — 2,160 rows (Oct 2025 – Mar 2026)
├── PRODUCTS
│   └── PRODUCT_CATALOGUE   — 30 products
├── RETURNS
│   └── RETURN_EVENTS       — 450 return records
└── CUSTOMERS
    └── CUSTOMER_METRICS     — 72 monthly segment records
```
