# 10 — Self-Healing SQL

## Overview

Self-Healing SQL is OmniData's **human-in-the-loop learning system**. When a domain expert spots an incorrect or suboptimal SQL query in the Transparency Panel, they can edit it and save the correction to Pinecone's `examples_store`. Future similar questions automatically retrieve the corrected pattern, making the system smarter with every human correction.

## Architecture

```mermaid
sequenceDiagram
    participant U as Domain Expert
    participant FE as Frontend
    participant BE as Backend API
    participant PC as Pinecone (examples_store)

    Note over U,FE: User sees SQL in Transparency Panel

    U->>FE: Click "Edit & Teach AI"
    FE->>FE: Open SQL editor modal
    U->>FE: Correct the SQL query
    U->>FE: Click "Save to Knowledge Base"
    FE->>BE: POST /api/save-knowledge<br/>{question, corrected_sql}
    BE->>PC: Upsert to omnidata-hybrid<br/>namespace: examples_store
    PC-->>BE: Upsert confirmed
    BE-->>FE: 200 OK
    FE->>U: Toast: "Query embedded and saved<br/>to Pinecone examples_store"
```

## Learning Loop

```mermaid
flowchart TD
    subgraph Before["Before Correction"]
        Q1["'Show me South revenue'"] --> GEN1["LLM generates SQL"]
        GEN1 --> BAD["SELECT * FROM AURA_SALES<br/>WHERE REGION = 'south'<br/><i>(wrong casing)</i>"]
    end

    subgraph Correction["Human Correction"]
        BAD --> EDIT["Expert edits SQL"]
        EDIT --> GOOD["SELECT REGION, SUM(ACTUAL_SALES)<br/>FROM SALES.AURA_SALES<br/>WHERE REGION = 'South'<br/>GROUP BY REGION"]
        GOOD --> SAVE["Save to examples_store"]
    end

    subgraph After["After Correction"]
        Q2["'What is South region revenue?'"] --> RAG["Retrieve from examples_store"]
        RAG --> MATCH["Finds corrected example<br/>(high cosine similarity)"]
        MATCH --> GEN2["LLM uses corrected pattern<br/>as few-shot example"]
        GEN2 --> CORRECT["Generates correct SQL<br/>on first attempt"]
    end
```

## How It Integrates with SQL Generation

The SQL Branch retrieves examples from Pinecone's `examples_store` namespace before generating SQL:

```mermaid
flowchart LR
    Q["User question"] --> PC["Search examples_store<br/>top-3 similar Q→SQL pairs"]
    PC --> FEW["Include as few-shot examples<br/>in the SQL generation prompt"]
    FEW --> LLM["Llama 3.3 70B<br/>generates SQL with examples"]
```

When a human-corrected example is saved, it becomes part of this retrieval pool. Because Pinecone ranks by semantic similarity, the corrected example naturally surfaces for similar future queries.

## Record Schema

Each Q→SQL pair in `examples_store`:

```json
{
  "id": "example-custom-001",
  "text": "Show me South region revenue breakdown",
  "metadata": {
    "sql": "SELECT REGION, SUM(ACTUAL_SALES) as TOTAL_REVENUE FROM SALES.AURA_SALES WHERE REGION = 'South' GROUP BY REGION",
    "source": "human_correction",
    "created_at": "2026-04-19T10:30:00Z",
    "tables": ["AURA_SALES"]
  }
}
```

## Frontend UI

The self-healing workflow is accessible directly from the SQL tab:

1. **"Edit & Teach AI" button** — Opens a modal with the SQL in an editable textarea
2. **SQL Editor** — User corrects the query
3. **"Save to Knowledge Base" button** — Sends the correction to the API
4. **Success toast** — Confirms the correction was embedded and saved

This creates a continuous improvement loop where the system gets better with use — without requiring any code changes or redeployment.
