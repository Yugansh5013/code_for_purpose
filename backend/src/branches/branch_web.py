"""
OmniData — Branch Web (Tavily Live Search)

Searches the web using Tavily API for real-time external context:
market trends, competitor intelligence, industry benchmarks.

This branch is activated when the intent router detects questions about:
- Competitors, market trends, industry performance
- External factors affecting business metrics
- "What's happening in the market?" queries
- Anything requiring context beyond internal data

The branch rewrites company-specific queries into industry-generic
searches since Aura Retail is a proprietary/fictional brand.
"""

import logging
from typing import Any, Optional

from src.state import GraphState

logger = logging.getLogger(__name__)

# Maximum results to return from Tavily
MAX_RESULTS = 5

# Query rewriting: strip internal jargon, make industry-generic
COMPANY_TERMS = {
    "aura retail": "UK consumer electronics retailer",
    "aura sound pro": "wireless headphones",
    "aurasound pro": "wireless headphones",
    "aura beats": "wireless earbuds",
    "aurabeats": "wireless earbuds",
    "aura base": "bluetooth speaker",
    "aurabase": "bluetooth speaker",
    "aura link": "smart home hub",
    "auralink": "smart home hub",
    "aura charge": "wireless charging dock",
    "auracharge": "wireless charging dock",
    "our company": "UK consumer electronics retail",
    "our product": "consumer electronics product",
    "our": "UK retail",
}

# Context keywords to append for better search relevance
CONTEXT_SUFFIX = "UK retail market 2025 2026"


def _rewrite_query_for_web(query: str) -> str:
    """
    Rewrite an internal-facing query into an industry-generic web search query.
    
    Strips company-specific product names and replaces them with
    industry-generic terms so Tavily returns relevant market data.
    """
    rewritten = query.lower()
    
    for internal, external in COMPANY_TERMS.items():
        rewritten = rewritten.replace(internal, external)
    
    # Remove filler phrases
    for filler in ["can you tell me", "please", "i want to know", "help me understand"]:
        rewritten = rewritten.replace(filler, "")
    
    # Clean up and add context
    rewritten = " ".join(rewritten.split())  # collapse whitespace
    
    # Only append context suffix if the query doesn't already have
    # enough context words
    context_words = ["market", "industry", "competitor", "trend", "uk", "retail"]
    has_context = any(w in rewritten.lower() for w in context_words)
    
    if not has_context:
        rewritten = f"{rewritten} {CONTEXT_SUFFIX}"
    
    return rewritten


async def branch_web_node(
    state: GraphState,
    tavily_api_key: str = "",
) -> dict:
    """
    Branch 3: Tavily Web Search.
    
    1. Rewrites the user query to be industry-generic
    2. Searches the web via Tavily
    3. Formats results for synthesis
    
    Args:
        state: Current graph state with resolved_query
        tavily_api_key: Tavily API key
        
    Returns:
        Dict with web_output populated
    """
    query = state.get("resolved_query", state.get("original_query", ""))
    
    if not tavily_api_key:
        logger.error("Branch Web: no Tavily API key configured")
        return {
            "web_output": {
                "data": [],
                "source": "tavily",
                "source_label": "External Market Intelligence (Web)",
                "error": "Web search not configured — missing API key.",
                "metadata": {"query": query},
            }
        }
    
    # Rewrite query for external search
    web_query = _rewrite_query_for_web(query)
    logger.info(f"Branch Web: '{query[:60]}...' → search: '{web_query[:80]}'")
    
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=tavily_api_key)
        
        # Search with Tavily
        response = client.search(
            query=web_query,
            search_depth="basic",      # "basic" is faster, "advanced" is deeper
            max_results=MAX_RESULTS,
            include_answer=True,        # Get a synthesized answer from Tavily
            include_raw_content=False,  # Don't need full page content
        )
        
        # Extract results
        results = response.get("results", [])
        tavily_answer = response.get("answer", "")
        
        if not results:
            logger.warning("Branch Web: no results from Tavily")
            return {
                "web_output": {
                    "data": [],
                    "source": "tavily",
                    "source_label": "External Market Intelligence (Web)",
                    "error": "No relevant external sources found.",
                    "metadata": {"query": query, "web_query": web_query},
                }
            }
        
        # Format results for synthesis and frontend
        formatted_results = []
        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": round(r.get("score", 0.0), 3),
                "source": "web",
            })
        
        # Build text blob for synthesis prompt
        data_for_synthesis = []
        if tavily_answer:
            data_for_synthesis.append(f"**Web Summary:** {tavily_answer}")
        
        for r in formatted_results:
            data_for_synthesis.append(
                f"**{r['title']}** (Source: {r['url']})\n"
                f"{r['content']}"
            )
        
        top_score = max(r["score"] for r in formatted_results) if formatted_results else 0
        
        logger.info(
            f"Branch Web: found {len(formatted_results)} results "
            f"(top score: {top_score:.3f})"
        )
        
        return {
            "web_output": {
                "data": data_for_synthesis,
                "raw_query": f"Web search: '{web_query}'",
                "source": "tavily",
                "source_label": "External Market Intelligence (Web)",
                "error": None,
                "metadata": {
                    "result_count": len(formatted_results),
                    "top_score": top_score,
                    "web_results": formatted_results,
                    "tavily_answer": tavily_answer,
                    "original_query": query,
                    "web_query": web_query,
                },
            }
        }
        
    except Exception as e:
        logger.error(f"Branch Web failed: {e}")
        return {
            "web_output": {
                "data": [],
                "source": "tavily",
                "source_label": "External Market Intelligence (Web)",
                "error": f"Web search failed: {str(e)}",
                "metadata": {"query": query, "web_query": web_query},
            }
        }
