"""
OmniData — Branch Salesforce (CRM Data Retrieval)

Searches the Salesforce CRM data in Pinecone (and optionally the live org)
to return customer account, opportunity, and case information.

This branch is activated when the intent router detects questions about:
- Customer accounts, churn risk, partner relationships
- Sales pipeline, deals, opportunities
- Support cases, complaints, product issues at account level
- "Which customers are at risk?" or "What's our pipeline?"

Architecture:
    Pinecone (salesforce_crm namespace) → primary retrieval
    SalesforceConnector (live SOQL) → fallback if vector search is empty
"""

import logging
from typing import Any, Optional

from src.state import GraphState
from src.vector.salesforce_store import search_salesforce_crm

logger = logging.getLogger(__name__)

# Minimum relevance score to include a CRM record
MIN_RELEVANCE_SCORE = 0.4


async def branch_salesforce_node(
    state: GraphState,
    pinecone_client: Any,
    dense_index: str = "omnidata-dense",
    salesforce_connector: Any = None,
) -> dict:
    """
    Branch 2B: Salesforce CRM Data Retrieval.
    
    1. Search salesforce_crm namespace for relevant CRM records
    2. Optionally fall back to live SOQL via SalesforceConnector
    3. Format results for synthesis
    
    Args:
        state: Current graph state with resolved_query
        pinecone_client: PineconeClient instance
        dense_index: Name of the Pinecone dense index
        salesforce_connector: Optional SalesforceConnector for live fallback
        
    Returns:
        Dict with salesforce_output populated
    """
    query = state.get("resolved_query", state.get("original_query", ""))
    user_context = state.get("user_context") or {}
    
    logger.info(f"Branch Salesforce: searching CRM for '{query[:80]}...'")
    
    try:
        # Build Pinecone metadata filter for restricted roles
        pinecone_filter = None
        if user_context.get("region_filter"):
            pinecone_filter = {"region": {"$eq": user_context["region_filter"]}}
            logger.info(f"Salesforce RLS: filtering to region={user_context['region_filter']}")
        
        # ── Step 1: Search CRM data ──────────────────────
        crm_results = search_salesforce_crm(
            client=pinecone_client,
            query=query,
            index_name=dense_index,
            top_k=5,
            salesforce_connector=salesforce_connector,
            filter=pinecone_filter,
        )
        
        # Filter by minimum relevance
        relevant_records = [
            rec for rec in crm_results
            if rec["score"] >= MIN_RELEVANCE_SCORE
        ]
        
        if not relevant_records:
            logger.warning("Branch Salesforce: no relevant CRM records found")
            return {
                "salesforce_output": {
                    "data": [],
                    "source": "salesforce",
                    "source_label": "Salesforce CRM",
                    "error": "No relevant CRM records found.",
                    "metadata": {"record_count": 0, "query": query},
                }
            }
        
        # ── Step 2: Format results ───────────────────────
        formatted_records = []
        for rec in relevant_records:
            display_name = rec["account_name"] or rec["object_type"]
            formatted_records.append({
                "account_name": display_name,
                "object_type": rec["object_type"],
                "region": rec["region"],
                "segment": rec["segment"],
                "churn_risk": rec["churn_risk"],
                "acv": rec["acv"],
                "partner_tier": rec["partner_tier"],
                "relevance": round(rec["score"], 3),
                "excerpt": rec["text"],
                "source": "salesforce",
            })
        
        # Determine top score for confidence
        top_score = max(r["relevance"] for r in formatted_records)
        
        # Build the text blob for synthesis
        data_for_synthesis = []
        for r in formatted_records:
            data_for_synthesis.append(
                f"**{r['account_name'] or r['object_type']}** "
                f"(Region: {r['region']}, Relevance: {r['relevance']})\n"
                f"{r['excerpt']}"
            )
        
        logger.info(
            f"Branch Salesforce: found {len(formatted_records)} relevant CRM records "
            f"(top score: {top_score:.3f})"
        )
        
        return {
            "salesforce_output": {
                "data": data_for_synthesis,
                "raw_query": f"CRM search: '{query[:100]}'",
                "source": "salesforce",
                "source_label": "Salesforce CRM",
                "error": None,
                "metadata": {
                    "record_count": len(formatted_records),
                    "top_score": top_score,
                    "crm_records": formatted_records,
                    "query": query,
                },
            }
        }
        
    except Exception as e:
        logger.error(f"Branch Salesforce failed: {e}")
        return {
            "salesforce_output": {
                "data": [],
                "source": "salesforce",
                "source_label": "Salesforce CRM",
                "error": f"CRM search failed: {str(e)}",
                "metadata": {"query": query},
            }
        }
