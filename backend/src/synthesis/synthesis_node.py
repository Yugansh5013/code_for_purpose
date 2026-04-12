"""
OmniData — Synthesis Node (Node 2)

Merges outputs from all active branches into a coherent, jargon-free response.
Uses Llama 3.3 70B via Groq.

Designed to handle N branch outputs generically — adding a new branch
requires no changes to this node.
"""

import json
import logging
from typing import Any

from src.state import GraphState
from src.clarification.metric_resolver import get_jargon_map

logger = logging.getLogger(__name__)

SYNTHESIS_MODEL = "llama-3.3-70b-versatile"

SYNTHESIS_PROMPT = """You are a business intelligence assistant for Aura Retail, a UK consumer electronics retailer.
Synthesize the data below into a clear, concise, jargon-free answer for a non-technical business user.

## Rules:
1. Lead with the key insight — don't bury the answer.
2. Use plain English. Never use SQL column names, API field names, or technical identifiers.
3. Format numbers with commas and appropriate currency symbols (£ for GBP).
4. Round percentages to one decimal place.
5. If multiple data sources provided answers, connect them into a narrative.
6. If data shows an anomaly, explain the likely cause if context is available.
7. Keep responses concise — 2-4 paragraphs maximum.
8. If there was an error retrieving data, acknowledge it honestly.
9. When citing information from the Internal Knowledge Base, mention the document title naturally in your response (e.g. "According to the Regional Marketing Budget Policy...", "The Monthly Trading Update confirms..."). This builds trust by showing where the insight came from.

## Jargon Substitution Rules:
Replace these technical terms if they appear in your response:
{jargon_rules}

## Data Sources:
{sources_section}

## User Question:
{user_question}
"""


async def synthesis_node(state: GraphState, groq_pool: Any) -> dict:
    """
    Node 2: Synthesize all branch outputs into a final response.
    
    Iterates over ALL non-None branch outputs in state.
    Phase 1: Only sql_output is populated.
    Phase 2+: Handles multiple outputs naturally.
    """
    query = state.get("original_query", "")
    
    # ── Collect all branch outputs ───────────────────────
    sources = []
    sources_section_parts = []
    
    branch_outputs = [
        ("sql_output", "Snowflake Data Warehouse"),
        ("rag_output", "Internal Knowledge Base"),
        ("salesforce_output", "Salesforce CRM"),
        ("web_output", "External Market Intelligence"),
    ]
    
    for output_key, label in branch_outputs:
        output = state.get(output_key)
        if output is None:
            continue
        
        source_info = {
            "source": output.get("source", output_key),
            "label": output.get("source_label", label),
            "confidence": output.get("confidence_score", None),
        }
        sources.append(source_info)
        
        # Format for the LLM prompt
        if output.get("error"):
            sources_section_parts.append(
                f"### {label}\n**Error:** {output['error']}"
            )
        elif output_key == "sql_output":
            # Check for multi-chart data from complexity decomposition
            charts = output.get("charts", [])
            
            if len(charts) > 1:
                # Multiple sub-queries — include ALL results for full narrative
                for idx, chart in enumerate(charts):
                    chart_title = chart.get("title", f"Analysis {idx + 1}")
                    chart_sql = chart.get("sql", "")
                    chart_rows = chart.get("data", [])[:20]
                    chart_conf = chart.get("confidence_tier", "unknown")
                    rows_text = json.dumps(chart_rows, indent=2, default=str)
                    
                    sources_section_parts.append(
                        f"### {label} — Sub-analysis {idx + 1}: {chart_title} (confidence: {chart_conf})\n"
                        f"**SQL Query:** {chart_sql}\n\n"
                        f"**Results ({len(chart_rows)} rows):**\n```json\n{rows_text}\n```"
                    )
            else:
                # Single query — standard format
                sql = output.get("sql", "")
                rows = output.get("rows", [])
                confidence = output.get("confidence_tier", "unknown")
                
                display_rows = rows[:30]
                rows_text = json.dumps(display_rows, indent=2, default=str)
                
                sources_section_parts.append(
                    f"### {label} (confidence: {confidence})\n"
                    f"**SQL Query:** {sql}\n\n"
                    f"**Results ({len(rows)} rows):**\n```json\n{rows_text}\n```"
                )
        else:
            # Generic format for other branches
            data = output.get("data", "")
            if isinstance(data, list):
                data_text = json.dumps(data[:10], indent=2, default=str)
            else:
                data_text = str(data)[:2000]
            
            sources_section_parts.append(
                f"### {label}\n{data_text}"
            )
    
    if not sources:
        return {
            "final_response": "I wasn't able to retrieve any data for your question. Could you try rephrasing it?",
            "draft_response": "",
            "sources_used": [],
        }
    
    # ── Build jargon rules ───────────────────────────────
    jargon_map = get_jargon_map()
    jargon_rules = "\n".join([
        f"- Replace '{term}' with '{display}'"
        for term, display in jargon_map.items()
    ])
    
    # ── Generate synthesis ───────────────────────────────
    prompt = SYNTHESIS_PROMPT.format(
        jargon_rules=jargon_rules or "No specific substitutions required.",
        sources_section="\n\n".join(sources_section_parts),
        user_question=query,
    )
    
    try:
        client = groq_pool.get_client()
        response = client.chat.completions.create(
            model=SYNTHESIS_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Please synthesize the data into a clear answer."},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        
        final_response = response.choices[0].message.content.strip()
        
        logger.info(f"Synthesis complete: {len(final_response)} chars, {len(sources)} sources")
        
        # ── Compute confidence when SQL branch is absent ─────
        # SQL branch sets confidence_score/tier at the graph level.
        # For RAG-only queries, derive confidence from top document score.
        result = {
            "draft_response": final_response,
            "final_response": final_response,
            "sources_used": sources,
        }
        
        sql_output = state.get("sql_output")
        rag_output = state.get("rag_output")
        web_output = state.get("web_output")
        
        if not sql_output:
            # No SQL branch ran — derive confidence from RAG or Web
            top_score = 0.0
            
            if rag_output and not rag_output.get("error"):
                rag_meta = rag_output.get("metadata", {})
                rag_score = rag_meta.get("top_score", 0.0)
                top_score = max(top_score, rag_score)
            
            if web_output and not web_output.get("error"):
                web_meta = web_output.get("metadata", {})
                web_score = web_meta.get("top_score", 0.0)
                top_score = max(top_score, web_score)
            
            if top_score > 0:
                if top_score >= 0.8:
                    tier = "green"
                elif top_score >= 0.6:
                    tier = "amber"
                else:
                    tier = "red"
                
                result["confidence_score"] = round(top_score, 3)
                result["confidence_tier"] = tier
        
        return result
        
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        # Fallback: return raw data summary
        fallback = _build_fallback_response(state, sources)
        return {
            "draft_response": fallback,
            "final_response": fallback,
            "sources_used": sources,
        }


def _build_fallback_response(state: GraphState, sources: list[dict]) -> str:
    """Build a basic response when synthesis LLM fails."""
    parts = ["Here's what I found:\n"]
    
    sql_output = state.get("sql_output")
    if sql_output and not sql_output.get("error"):
        rows = sql_output.get("rows", [])
        if rows:
            parts.append(f"**Data:** {len(rows)} rows returned from the warehouse.\n")
            # Show first few rows
            for row in rows[:5]:
                parts.append(f"- {row}")
    
    return "\n".join(parts)
