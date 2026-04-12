"""
OmniData — Clarification Node (Node 1)

Orchestrates temporal resolution and metric resolution.
Determines if the user needs to clarify before proceeding.
"""

import logging
from typing import Any

from src.state import GraphState
from src.clarification.temporal_resolver import resolve_temporal_references
from src.clarification.metric_resolver import resolve_metrics

logger = logging.getLogger(__name__)


async def clarification_node(state: GraphState) -> dict:
    """
    Node 1: Resolve temporal references and metrics.
    
    Returns state updates with resolved dates, metrics, and
    clarification flags if the query is ambiguous.
    """
    query = state.get("original_query", "")
    
    # ── Step 1: Temporal resolution ──────────────────────
    temporal = resolve_temporal_references(query)
    
    # ── Step 2: Metric resolution ────────────────────────
    metric_result = resolve_metrics(query)
    
    # ── Step 3: Check if clarification needed ────────────
    if metric_result["ambiguous"]:
        logger.info(f"Clarification needed: {metric_result['clarification_prompt']}")
        return {
            "resolved_query": query,
            "resolved_dates": temporal.get("resolved_dates"),
            "temporal_note": temporal.get("temporal_note", ""),
            "resolved_metrics": metric_result["resolved_info"],
            "clarification_needed": True,
            "clarification_options": metric_result["clarification_options"],
        }
    
    # ── Step 4: Build enriched query context ─────────────
    # Add resolved date info to the query context for SQL generation
    enriched_parts = [query]
    
    if temporal["temporal_note"]:
        enriched_parts.append(f"[Date context: {temporal['temporal_note']}]")
    
    if temporal["date_clause"]:
        # Inject as explicit SQL directive — not just a hint
        enriched_parts.append(
            f"[IMPORTANT: MUST USE this SQL WHERE clause for date filtering: {temporal['date_clause']}. "
            f"Apply to SALE_DATE, RETURN_DATE, or METRIC_MONTH as appropriate for the table being queried.]"
        )
    
    for info in metric_result["resolved_info"]:
        if info.get("canonical_column"):
            enriched_parts.append(
                f"[Metric '{info['display_name']}' maps to column {info['canonical_column']} "
                f"in table {info.get('table', 'unknown')}]"
            )
    
    resolved_query = " ".join(enriched_parts)
    
    logger.info(f"Clarification complete: dates={'yes' if temporal['resolved_dates'] else 'no'}, "
                f"metrics={len(metric_result['matched_metrics'])}")
    
    return {
        "resolved_query": resolved_query,
        "resolved_dates": temporal.get("resolved_dates"),
        "temporal_note": temporal.get("temporal_note", ""),
        "resolved_metrics": metric_result["resolved_info"],
        "clarification_needed": False,
        "clarification_options": [],
    }
