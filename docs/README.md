# OmniData — Architecture Documentation

Comprehensive technical documentation covering every architectural subsystem in OmniData.

## Contents

| Document | Description |
|----------|-------------|
| [System Overview](./01-system-overview.md) | High-level architecture, tech stack, and data flow |
| [LangGraph Pipeline](./02-langgraph-pipeline.md) | Multi-agent orchestration, routing logic, and branch chaining |
| [SQL Branch & Snowflake](./03-sql-branch.md) | SQL generation, query decomposition, retry, and E2B visualization |
| [RAG & Knowledge Base](./04-rag-branch.md) | Confluence document retrieval via Pinecone dense vectors |
| [Salesforce CRM Branch](./05-salesforce-branch.md) | CRM data retrieval with vector-first, SOQL-fallback architecture |
| [Web Intelligence Branch](./06-web-branch.md) | Real-time market data via Tavily with query rewriting |
| [Metric Dictionary & Clarification](./07-metric-dictionary.md) | Alias resolution, ambiguity detection, and clarification flow |
| [Semantic Validator & Jargon Auditor](./08-semantic-validator.md) | Three-layer jargon detection and response rewriting |
| [Confidence Scoring](./09-confidence-scoring.md) | Three-signal weighted confidence system |
| [Self-Healing SQL](./10-self-healing-sql.md) | Human-in-the-loop SQL correction and vector embedding |
| [Groq Key Pool & Resilience](./11-groq-resilience.md) | API key rotation and automatic 429 retry logic |
