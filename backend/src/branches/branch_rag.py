"""
OmniData — Branch RAG (Confluence & Document RAG)

Searches the Confluence knowledge base and user-uploaded documents
in Pinecone, returning relevant document excerpts with source metadata.

This branch is activated when the intent router detects questions about:
- Company policies, procedures, internal decisions
- "Why did X happen?" queries needing context beyond raw data
- Product launch details, strategic memos, operational playbooks
"""

import logging
from typing import Any

from src.state import GraphState
from src.vector.confluence_store import search_confluence

logger = logging.getLogger(__name__)

# Minimum relevance score to include a document
MIN_RELEVANCE_SCORE = 0.5


async def branch_rag_node(
    state: GraphState,
    pinecone_client: Any,
    dense_index: str = "omnidata-dense",
) -> dict:
    """
    Branch 2A: Confluence & Document RAG.
    
    1. Search confluence_store namespace for relevant documents
    2. Optionally search documents_store for user uploads (future)
    3. Merge, deduplicate, and return top results
    
    Args:
        state: Current graph state with resolved_query
        pinecone_client: PineconeClient instance
        dense_index: Name of the Pinecone dense index
        
    Returns:
        Dict with rag_output populated
    """
    query = state.get("resolved_query", state.get("original_query", ""))
    
    logger.info(f"Branch RAG: searching for '{query[:80]}...'")
    
    try:
        # ── Step 1: Search Confluence ─────────────────────
        confluence_results = search_confluence(
            client=pinecone_client,
            query=query,
            index_name=dense_index,
            top_k=5,
        )
        
        # Filter by minimum relevance
        relevant_docs = [
            doc for doc in confluence_results
            if doc["score"] >= MIN_RELEVANCE_SCORE
        ]
        
        if not relevant_docs:
            logger.warning("Branch RAG: no relevant documents found")
            return {
                "rag_output": {
                    "data": [],
                    "source": "confluence",
                    "source_label": "Internal Knowledge Base (Confluence)",
                    "error": "No relevant documents found in the knowledge base.",
                    "metadata": {"doc_count": 0, "query": query},
                }
            }
        
        # ── Step 2: Format results ────────────────────────
        # Build structured data for synthesis
        formatted_docs = []
        for doc in relevant_docs:
            formatted_docs.append({
                "title": doc["title"],
                "space": doc["space"],
                "relevance": round(doc["score"], 3),
                "excerpt": doc["text"],
                "doc_id": doc["doc_id"],
                "source": "confluence",
            })
        
        # Determine top score for confidence
        top_score = max(d["relevance"] for d in formatted_docs)
        
        # Build the text blob that goes to synthesis
        data_for_synthesis = []
        for d in formatted_docs:
            data_for_synthesis.append(
                f"**{d['title']}** (Space: {d['space']}, Relevance: {d['relevance']})\n"
                f"{d['excerpt']}"
            )
        
        logger.info(
            f"Branch RAG: found {len(formatted_docs)} relevant documents "
            f"(top score: {top_score:.3f})"
        )
        
        return {
            "rag_output": {
                "data": data_for_synthesis,
                "raw_query": f"Vector search: '{query[:100]}'",
                "source": "confluence",
                "source_label": "Internal Knowledge Base (Confluence)",
                "error": None,
                "metadata": {
                    "doc_count": len(formatted_docs),
                    "top_score": top_score,
                    "documents": formatted_docs,
                    "query": query,
                },
            }
        }
        
    except Exception as e:
        logger.error(f"Branch RAG failed: {e}")
        return {
            "rag_output": {
                "data": [],
                "source": "confluence",
                "source_label": "Internal Knowledge Base (Confluence)",
                "error": f"Knowledge base search failed: {str(e)}",
                "metadata": {"query": query},
            }
        }
