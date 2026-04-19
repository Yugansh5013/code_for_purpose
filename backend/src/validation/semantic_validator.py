"""
OmniData — Semantic Output Validator (Node 3)

Three-layer jargon detection and rewriting pipeline:
  Layer 1: Pattern-based detection (regex) — catches __c fields,
           ALL_CAPS columns, fully-qualified table names, SQL fragments
  Layer 2: Known jargon registry — metric dictionary + Snowflake-backed overrides
  Layer 3: LLM rewriting (Llama 3.3 8B) — naturally rewrites flagged terms

Fires ONLY when rag_present = true (any unstructured data source was used).
Pure SQL or pure Web queries skip this node.

The substitution log is returned to the frontend for the "Language Audit"
transparency panel.

Persistence:
  - Primary: Snowflake SYSTEM.JARGON_OVERRIDES table
  - Fallback: local jargon_overrides.yaml (for offline dev / Snowflake outage)
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from src.state import GraphState
from src.clarification.metric_resolver import get_jargon_map

logger = logging.getLogger(__name__)

VALIDATOR_MODEL = "llama-3.1-8b-instant"

# ── Module-level Snowflake connector reference ───────────────
_snowflake_connector = None
_last_sync_time: Optional[datetime] = None


def set_snowflake_connector(connector):
    """Called once at startup from main.py to wire the Snowflake connection."""
    global _snowflake_connector
    _snowflake_connector = connector
    logger.info("Semantic validator: Snowflake connector wired")


# ── Jargon Overrides Loader ──────────────────────────────────

_OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "config" / "jargon_overrides.yaml"
_overrides_cache: dict | None = None


def _load_overrides() -> dict[str, dict]:
    """
    Load jargon overrides — Snowflake-first, YAML fallback.
    Returns a dict: { "TERM": {"replacement": "...", "category": "..."} }
    """
    global _overrides_cache, _last_sync_time
    if _overrides_cache is not None:
        return _overrides_cache

    # Try Snowflake first
    if _snowflake_connector:
        try:
            _overrides_cache = _snowflake_connector.get_jargon_overrides()
            _last_sync_time = datetime.now(timezone.utc)
            logger.info(f"Loaded {len(_overrides_cache)} jargon overrides from Snowflake")
            return _overrides_cache
        except Exception as e:
            logger.warning(f"Snowflake overrides fetch failed, falling back to YAML: {e}")

    # Fallback to YAML
    if not _OVERRIDES_PATH.exists():
        _overrides_cache = {}
        return _overrides_cache

    with open(_OVERRIDES_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    overrides = {}
    for entry in data.get("overrides", []):
        term = entry.get("term", "")
        if term:
            overrides[term] = {
                "replacement": entry.get("replacement", ""),
                "category": entry.get("category", "custom"),
            }

    _overrides_cache = overrides
    _last_sync_time = datetime.now(timezone.utc)
    logger.info(f"Loaded {len(overrides)} jargon overrides from YAML fallback")
    return overrides


def reload_overrides():
    """Force reload of jargon overrides (called after POST /jargon or /sync)."""
    global _overrides_cache
    _overrides_cache = None
    return _load_overrides()


def sync_from_snowflake() -> dict:
    """
    Force a full re-sync of both dictionary + overrides from Snowflake.
    Called by POST /api/sync-semantics and at backend startup.
    Returns sync stats.
    """
    global _overrides_cache, _last_sync_time
    from src.clarification.metric_resolver import reload_metrics

    stats = {"overrides": 0, "dictionary": 0, "source": "unknown", "timestamp": None}

    if not _snowflake_connector:
        stats["source"] = "no_connector"
        logger.warning("Sync requested but no Snowflake connector available")
        return stats

    # Sync overrides
    try:
        _overrides_cache = _snowflake_connector.get_jargon_overrides()
        stats["overrides"] = len(_overrides_cache)
        stats["source"] = "snowflake"
    except Exception as e:
        logger.error(f"Override sync failed: {e}")
        stats["source"] = "error"

    # Sync metric dictionary
    try:
        dict_count = reload_metrics(_snowflake_connector)
        stats["dictionary"] = dict_count
    except Exception as e:
        logger.error(f"Dictionary sync failed: {e}")

    _last_sync_time = datetime.now(timezone.utc)
    stats["timestamp"] = _last_sync_time.isoformat()

    logger.info(
        f"Semantic sync complete: {stats['overrides']} overrides, "
        f"{stats['dictionary']} dictionary entries from {stats['source']}"
    )
    return stats


def get_sync_status() -> dict:
    """Return the current sync status for the frontend status panel."""
    return {
        "last_sync": _last_sync_time.isoformat() if _last_sync_time else None,
        "overrides_count": len(_overrides_cache) if _overrides_cache else 0,
        "source": "snowflake" if _snowflake_connector else "yaml",
        "connector_available": _snowflake_connector is not None,
    }


def get_all_jargon() -> list[dict]:
    """
    Return the complete jargon registry for the GET /jargon endpoint.
    Merges metric dictionary terms + user overrides.
    """
    registry = []

    # From metric dictionary
    metric_map = get_jargon_map()
    for term, display_name in metric_map.items():
        registry.append({
            "term": term,
            "replacement": display_name,
            "source": "metric_dictionary",
            "editable": False,
        })

    # From user overrides
    overrides = _load_overrides()
    for term, info in overrides.items():
        registry.append({
            "term": term,
            "replacement": info["replacement"],
            "source": "user_override",
            "category": info.get("category", "custom"),
            "editable": True,
        })

    return registry


def add_jargon_override(term: str, replacement: str, category: str = "custom"):
    """
    Add a new user-defined jargon term.
    Writes to Snowflake (primary) with YAML fallback.
    """
    overrides = _load_overrides()

    # Add to in-memory cache
    overrides[term] = {"replacement": replacement, "category": category}

    # Persist to Snowflake
    if _snowflake_connector:
        try:
            _snowflake_connector.save_jargon_override(term, replacement, category)
            logger.info(f"Added jargon override to Snowflake: '{term}' → '{replacement}'")
            return
        except Exception as e:
            logger.warning(f"Snowflake write failed, falling back to YAML: {e}")

    # Fallback: persist to YAML
    _save_overrides_yaml(overrides)
    logger.info(f"Added jargon override to YAML: '{term}' → '{replacement}'")


def remove_jargon_override(term: str) -> bool:
    """
    Remove a user-defined jargon term.
    Returns True if removed, False if not found.
    """
    overrides = _load_overrides()

    if term not in overrides:
        return False

    del overrides[term]

    # Delete from Snowflake
    if _snowflake_connector:
        try:
            _snowflake_connector.delete_jargon_override(term)
            logger.info(f"Removed jargon override from Snowflake: '{term}'")
            return True
        except Exception as e:
            logger.warning(f"Snowflake delete failed, falling back to YAML: {e}")

    # Fallback: persist to YAML
    _save_overrides_yaml(overrides)
    logger.info(f"Removed jargon override from YAML: '{term}'")
    return True


def _save_overrides_yaml(overrides: dict):
    """Persist the overrides dict back to YAML (fallback only)."""
    entries = []
    for term, info in overrides.items():
        entries.append({
            "term": term,
            "replacement": info["replacement"],
            "category": info.get("category", "custom"),
        })

    with open(_OVERRIDES_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            {"overrides": entries},
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    reload_overrides()


# ── Pattern-Based Detection (Layer 1) ────────────────────────

# Patterns that indicate leaked technical jargon
JARGON_PATTERNS = [
    # Salesforce custom fields: ChurnRisk__c, Region__c, etc.
    (r'\b\w+__c\b', "salesforce_field"),
    # Fully-qualified Snowflake table: OMNIDATA_DB.SCHEMA.TABLE
    (r'OMNIDATA_DB\.\w+\.\w+', "table_reference"),
    # ALL_CAPS multi-word identifiers: GEO_TERRITORY, ACTUAL_SALES
    (r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b', "column_name"),
    # SQL fragments in prose: "WHERE SALE_DATE >=", "GROUP BY region"
    (r'\b(?:SELECT|FROM|WHERE|JOIN|GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b(?=\s+[A-Z_])',
     "sql_fragment"),
]


def _detect_pattern_jargon(text: str) -> list[dict]:
    """
    Layer 1: Regex-based pattern detection.
    Returns list of {term, type, position} for each match.
    """
    found = []
    seen = set()

    for pattern, jargon_type in JARGON_PATTERNS:
        for match in re.finditer(pattern, text):
            term = match.group()
            if term not in seen:
                seen.add(term)
                found.append({
                    "term": term,
                    "type": jargon_type,
                    "position": match.start(),
                })

    return found


# ── Known Term Detection (Layer 2) ───────────────────────────

def _detect_known_jargon(text: str) -> list[dict]:
    """
    Layer 2: Dictionary-based detection.
    Checks against metric dictionary jargon_terms + user overrides.
    Returns list of {term, replacement, source}.
    """
    found = []
    seen = set()

    # From metric dictionary
    metric_map = get_jargon_map()
    for term, replacement in metric_map.items():
        if term in text and term not in seen:
            seen.add(term)
            found.append({
                "term": term,
                "replacement": replacement,
                "source": "metric_dictionary",
            })

    # From user overrides
    overrides = _load_overrides()
    for term, info in overrides.items():
        if term in text and term not in seen:
            seen.add(term)
            found.append({
                "term": term,
                "replacement": info["replacement"],
                "source": "user_override",
            })

    return found


# ── LLM Rewriting (Layer 3) ──────────────────────────────────

VALIDATOR_PROMPT = """You are a language quality auditor for a business intelligence system.
Your job is to rewrite a response to remove ALL technical database jargon while preserving meaning.

## Flagged Terms Found:
{flagged_terms}

## Known Replacements:
{replacement_map}

## Rules:
1. Replace every flagged term with its human-friendly equivalent.
2. For terms without a known replacement, infer a natural business-friendly name:
   - ALL_CAPS_NAME → lowercase with spaces (e.g., "GEO_TERRITORY" → "region")
   - __c fields → remove the __c suffix and add spaces (e.g., "ChurnRisk__c" → "Churn Risk")
   - Table references → use "the [purpose] data" (e.g., "OMNIDATA_DB.SALES.AURA_SALES" → "the sales data")
3. Do NOT change any numbers, dates, currency values, or percentages.
4. Do NOT add new information. Only rewrite the existing text.
5. Preserve the paragraph structure and tone of the original.

## Original Response:
{original_response}

## Instructions:
Return ONLY a JSON object with exactly these fields:
{{
  "cleaned_response": "the full rewritten response text",
  "substitutions": [
    {{"original": "TERM_FOUND", "replacement": "human friendly version", "category": "column_name|salesforce_field|table_reference|sql_fragment"}}
  ]
}}"""


async def semantic_validator_node(state: GraphState, groq_pool: Any) -> dict:
    """
    Node 3: Semantic Output Validator.

    Scans the draft response for leaked technical jargon and rewrites
    it naturally. Returns the cleaned response + substitution log.

    Fires only when rag_present = true.
    """
    draft = state.get("draft_response", "")

    if not draft:
        return {}

    # ── Layer 1: Pattern detection ────────────────────────
    pattern_hits = _detect_pattern_jargon(draft)

    # ── Layer 2: Known term detection ─────────────────────
    known_hits = _detect_known_jargon(draft)

    # Merge all detected terms
    all_flagged = set()
    replacement_map = {}

    for hit in pattern_hits:
        all_flagged.add(hit["term"])

    for hit in known_hits:
        all_flagged.add(hit["term"])
        replacement_map[hit["term"]] = hit["replacement"]

    # ── Short circuit: no jargon found ────────────────────
    if not all_flagged:
        logger.info("Semantic Validator: no jargon detected — pass-through")
        return {
            "final_response": draft,
            "jargon_substitutions": [],
        }

    logger.info(f"Semantic Validator: {len(all_flagged)} terms flagged → LLM rewrite")

    # ── Layer 3: LLM rewriting ────────────────────────────
    flagged_str = "\n".join(f"- {t}" for t in sorted(all_flagged))
    replacement_str = "\n".join(
        f"- \"{k}\" → \"{v}\"" for k, v in replacement_map.items()
    ) or "No pre-defined replacements available. Infer natural names."

    prompt = VALIDATOR_PROMPT.format(
        flagged_terms=flagged_str,
        replacement_map=replacement_str,
        original_response=draft,
    )

    try:
        response = groq_pool.complete_with_retry(
            model=VALIDATOR_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Rewrite the response and return the JSON."},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        raw = response.choices[0].message.content.strip()

        # Parse JSON from LLM response
        parsed = _parse_validator_json(raw)

        if parsed:
            cleaned = parsed.get("cleaned_response", draft)
            subs = parsed.get("substitutions", [])

            logger.info(
                f"Semantic Validator: {len(subs)} substitutions applied "
                f"({len(cleaned)} chars)"
            )

            return {
                "final_response": cleaned,
                "jargon_substitutions": subs,
            }
        else:
            # Failed to parse — use draft as-is but log what we found
            logger.warning("Semantic Validator: LLM output not parseable, using draft")
            return {
                "final_response": draft,
                "jargon_substitutions": [
                    {"original": t, "replacement": replacement_map.get(t, "?"), "category": "detected"}
                    for t in all_flagged
                    if t in replacement_map
                ],
            }

    except Exception as e:
        logger.error(f"Semantic Validator LLM call failed: {e}")
        # Graceful fallback: return draft response unchanged
        return {
            "final_response": draft,
            "jargon_substitutions": [],
        }


def _parse_validator_json(raw: str) -> dict | None:
    """
    Extract JSON from LLM response. Handles markdown code blocks.
    """
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ```
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    return None
