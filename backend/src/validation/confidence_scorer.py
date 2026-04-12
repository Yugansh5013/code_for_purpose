"""
OmniData — Confidence Scorer

Three-signal weighted scoring system for SQL query confidence.
Signals: Pinecone RAG relevance, retry count, result sanity.
"""

import logging

logger = logging.getLogger(__name__)

# Weight configuration from PRD §4.4
WEIGHTS = {
    "pinecone_score": 0.40,
    "retry_count": 0.40,
    "result_sanity": 0.20,
}

# Thresholds
PINECONE_LOW_THRESHOLD = 0.75
TIER_GREEN = 0.80
TIER_AMBER = 0.50


def calculate_confidence(
    pinecone_top_score: float,
    retry_count: int,
    row_count: int,
    is_aggregate: bool = False,
) -> dict:
    """
    Calculate confidence score from three signals.
    
    Args:
        pinecone_top_score: Relevance score of the top RAG match (0-1)
        retry_count: Number of SQL generation retries (0 = first attempt worked)
        row_count: Number of rows returned by the query
        is_aggregate: Whether the query uses aggregate functions
    
    Returns:
        Dict with score (float), tier (str), and signal breakdown
    """
    # ── Signal 1: Pinecone relevance (40%) ───────────────
    if pinecone_top_score >= PINECONE_LOW_THRESHOLD:
        signal_pinecone = min(pinecone_top_score, 1.0)
    else:
        signal_pinecone = pinecone_top_score * 0.6  # Penalty for low relevance
    
    # ── Signal 2: Retry count (40%) ──────────────────────
    if retry_count == 0:
        signal_retry = 1.0
    elif retry_count == 1:
        signal_retry = 0.5
    else:
        signal_retry = 0.0
    
    # ── Signal 3: Result sanity (20%) ────────────────────
    if row_count > 0:
        signal_sanity = 1.0
    elif is_aggregate:
        # Zero rows on aggregate = suspicious but possible (no data in range)
        signal_sanity = 0.5
    else:
        # Zero rows on non-aggregate = likely wrong query
        signal_sanity = 0.2
    
    # ── Weighted score ───────────────────────────────────
    score = (
        signal_pinecone * WEIGHTS["pinecone_score"]
        + signal_retry * WEIGHTS["retry_count"]
        + signal_sanity * WEIGHTS["result_sanity"]
    )
    
    # Clamp to [0, 1]
    score = max(0.0, min(1.0, round(score, 3)))
    
    # ── Tier assignment ──────────────────────────────────
    if score >= TIER_GREEN:
        tier = "green"
    elif score >= TIER_AMBER:
        tier = "amber"
    else:
        tier = "red"
    
    result = {
        "score": score,
        "tier": tier,
        "signals": {
            "pinecone_relevance": round(signal_pinecone, 3),
            "retry_penalty": round(signal_retry, 3),
            "result_sanity": round(signal_sanity, 3),
        },
    }
    
    logger.info(f"Confidence: {score:.3f} ({tier}) — pinecone={signal_pinecone:.2f}, retry={signal_retry:.2f}, sanity={signal_sanity:.2f}")
    
    return result
