# 11 — Groq Key Pool & Resilience

## Overview

OmniData uses **Groq** for all LLM inference (Llama 3.3 70B for intent routing, SQL generation, and synthesis; Llama 3.1 8B for semantic validation). To handle rate limits under concurrent usage, the system implements a **rotating key pool with automatic 429 retry logic**.

## Key Pool Architecture

```mermaid
flowchart TD
    REQ["LLM Request"] --> POOL["GroqKeyPool<br/>(3 API keys)"]

    POOL --> K1["Key 1"]
    POOL --> K2["Key 2"]
    POOL --> K3["Key 3"]

    K1 -->|"429 Rate Limit"| ROTATE["Rotate to next key"]
    K2 -->|"429 Rate Limit"| ROTATE
    K3 -->|"429 Rate Limit"| ROTATE

    K1 -->|"200 OK"| RES["Return response"]
    K2 -->|"200 OK"| RES
    K3 -->|"200 OK"| RES

    ROTATE --> POOL
```

## Rotation Logic

```mermaid
sequenceDiagram
    participant Node as Pipeline Node
    participant Pool as GroqKeyPool
    participant API as Groq API

    Node->>Pool: request(prompt, model)
    Pool->>Pool: Select key at current index
    Pool->>API: POST /chat/completions (Key 1)

    alt 200 OK
        API-->>Pool: Response
        Pool-->>Node: Return result
    else 429 Rate Limited
        API-->>Pool: 429 Too Many Requests
        Pool->>Pool: Increment index → Key 2
        Pool->>API: POST /chat/completions (Key 2)
        API-->>Pool: Response
        Pool-->>Node: Return result
    end
```

## Key Distribution

The pipeline makes multiple LLM calls per query. The key pool distributes load:

| Node | Model | Calls per Query |
|------|-------|----------------|
| Intent Router | Llama 3.3 70B | 1 |
| Complexity Router | Llama 3.3 70B | 1 |
| SQL Generation | Llama 3.3 70B | 1–3 (retries) |
| Chart Generation | Llama 3.3 70B | 1 per sub-query |
| Synthesis | Llama 3.3 70B | 1 |
| Semantic Validator | Llama 3.1 8B | 0–1 (conditional) |

**Total per complex query:** 5–8 LLM calls, distributed across 3 API keys.

## Configuration

Keys are loaded from environment variables:

```env
GROQ_API_KEY_1=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_2=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY_3=gsk_xxxxxxxxxxxxxxxxxxxx
```

The pool initializes at startup:

```python
pool = GroqKeyPool([
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
])
```

## Resilience Features

| Feature | Implementation |
|---------|---------------|
| **Round-robin rotation** | Keys cycle sequentially on each call |
| **429 auto-retry** | Automatically switches to the next key on rate limit |
| **Graceful degradation** | If all keys are exhausted, returns an error message instead of crashing |
| **Startup validation** | Logs the number of valid keys on boot: `Groq pool: 3 keys` |
