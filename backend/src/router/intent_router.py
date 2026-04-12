"""
OmniData — Intent Router (Node 0)

Classifies user query intent and sets routing flags for the LangGraph pipeline.
Uses Llama 3.1 8B via Groq for fast, lightweight classification.

Phase 1: Primary focus on SQL detection.
Phase 2+: Adds RAG, Salesforce, and web branch detection.
"""

import json
import logging
from typing import Any

from src.state import GraphState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an intent classifier for a business intelligence chatbot called OmniData.
The system has access to the following data sources:
1. **Snowflake Data Warehouse** — structured sales, product, customer, and returns data for Aura Retail (a UK consumer electronics retailer). Use when the user asks about revenue, sales, units, churn, returns, products, regions, channels, ad spend, or any quantitative business metric.
2. **Confluence Knowledge Base** — internal policy documents, product launch briefs, strategy memos. Use when the user asks about company policies, procedures, internal decisions, or "what does our policy say about X".
3. **Salesforce CRM** — customer accounts, opportunities, support cases. Use when the user asks about specific customers, accounts, deals, pipeline, support tickets, or churn risk at the account level.
4. **Web Search** — external market intelligence via Tavily. Use when the user asks about market trends, competitors, macro factors, industry benchmarks, or anything that requires external context.

Classify the user's query and output a JSON object with these fields:
{
  "branches": ["sql", "rag_confluence", "rag_salesforce", "web"],  // which branches to activate (list)
  "sql_likely": true/false,     // does this need a SQL query against Snowflake?
  "rag_present": true/false,    // does this need document/knowledge retrieval?
  "rag_sources": ["confluence", "documents"],  // which RAG sources if rag_present
  "salesforce_needed": true/false,  // does this need Salesforce CRM data?
  "web_needed": true/false,     // does this need external web search?
  "reasoning": "brief explanation of your classification"
}

Rules:
- A query can activate MULTIPLE branches simultaneously
- "Why did X happen?" usually needs both sql + rag_confluence
- "What does our policy say?" needs rag_confluence
- "Which customers are at risk?" needs rag_salesforce  
- "What's happening in the market?" needs web
- Pure data questions (revenue, units, trends) need only sql
- Output ONLY valid JSON, no other text
"""


async def intent_router_node(state: GraphState, groq_pool: Any) -> dict:
    """
    Node 0: Classify user intent and set routing flags.
    
    Args:
        state: Current graph state with original_query
        groq_pool: GroqKeyPool instance for API key rotation
    
    Returns:
        Dict of state updates with routing flags
    """
    query = state["original_query"]
    
    try:
        client = groq_pool.get_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        
        result = json.loads(response.choices[0].message.content)
        
        logger.info(f"Intent Router: branches={result.get('branches', [])} | reasoning={result.get('reasoning', '')}")
        
        return {
            "branches": result.get("branches", ["sql"]),
            "sql_likely": result.get("sql_likely", True),
            "rag_present": result.get("rag_present", False),
            "rag_sources": result.get("rag_sources", []),
            "salesforce_needed": result.get("salesforce_needed", False),
            "web_needed": result.get("web_needed", False),
        }
        
    except Exception as e:
        logger.error(f"Intent Router failed: {e}")
        # Default to SQL branch on failure — safe fallback
        return {
            "branches": ["sql"],
            "sql_likely": True,
            "rag_present": False,
            "rag_sources": [],
            "salesforce_needed": False,
            "web_needed": False,
        }
