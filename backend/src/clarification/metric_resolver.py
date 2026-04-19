"""
OmniData — Metric Resolver

Resolves ambiguous business terms using the Metric Dictionary.
Handles alias matching, ambiguity detection, and clarification prompts.

Dictionary source:
  - Primary: Snowflake column COMMENTs (JSON metadata)
  - Fallback: local metric_dictionary.yaml
"""

import logging
import re
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Load metric dictionary at module level
_METRIC_DICT_PATH = Path(__file__).resolve().parent.parent / "config" / "metric_dictionary.yaml"
_METRICS: dict = {}


def _load_metrics() -> dict:
    """Load and cache the metric dictionary (YAML fallback)."""
    global _METRICS
    if not _METRICS:
        with open(_METRIC_DICT_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        _METRICS = data.get("metrics", {})
        logger.info(f"Loaded {len(_METRICS)} metrics from YAML dictionary")
    return _METRICS


def reload_metrics(connector=None) -> int:
    """
    Force reload of metrics — Snowflake first, then YAML fallback.
    Called by sync_from_snowflake() and optionally at startup.
    Returns the number of metrics loaded.
    """
    global _METRICS

    if connector:
        try:
            sf_dict = connector.fetch_metric_dictionary()
            if sf_dict:
                # Convert Snowflake column metadata into the same format as YAML metrics
                merged = {}

                # First, load the YAML as a base (it has ambiguous entries, aliases, etc.)
                with open(_METRIC_DICT_PATH, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                yaml_metrics = yaml_data.get("metrics", {})

                # Keep all YAML entries as baseline
                merged.update(yaml_metrics)

                # Overlay Snowflake column metadata — enrich existing entries
                for col_name, meta in sf_dict.items():
                    display = meta.get("display_name")
                    if not display:
                        continue

                    # Find matching YAML entry by canonical_column
                    matched_key = None
                    for key, m in yaml_metrics.items():
                        if m.get("canonical_column") == col_name:
                            matched_key = key
                            break

                    if matched_key:
                        # Enrich existing entry with Snowflake metadata
                        if meta.get("aliases"):
                            existing_aliases = set(merged[matched_key].get("aliases", []))
                            existing_aliases.update(meta["aliases"])
                            merged[matched_key]["aliases"] = list(existing_aliases)
                        if meta.get("description"):
                            merged[matched_key]["description"] = meta["description"]
                    else:
                        # New column not in YAML — create a metric entry
                        key = col_name.lower()
                        jargon_terms = [col_name, col_name.lower()]
                        merged[key] = {
                            "display_name": display,
                            "aliases": meta.get("aliases", []),
                            "canonical_column": col_name,
                            "table": meta.get("table"),
                            "unit": meta.get("unit"),
                            "description": meta.get("description", ""),
                            "ambiguous": False,
                            "jargon_terms": jargon_terms,
                        }

                _METRICS = merged
                logger.info(f"Loaded {len(_METRICS)} metrics (Snowflake + YAML merged)")
                return len(_METRICS)

        except Exception as e:
            logger.warning(f"Snowflake metric dictionary fetch failed: {e}")

    # Fallback to YAML
    _METRICS = {}
    _load_metrics()
    return len(_METRICS)


def resolve_metrics(query: str) -> dict:
    """
    Match user query against metric dictionary aliases.
    
    Returns:
        Dict with:
            - matched_metrics: list of matched metric keys
            - ambiguous: whether clarification is needed
            - clarification_options: list of options if ambiguous
            - jargon_terms: all jargon terms from matched metrics (for stripping)
            - resolved_info: enriched context for SQL generation
    """
    metrics = _load_metrics()
    
    # Check if a clarification answer was injected
    is_clarification_response = False
    specific_match = re.search(r'\(specifically:\s*(.*?)\)', query, re.IGNORECASE)
    if specific_match:
        is_clarification_response = True
        answer = specific_match.group(1).strip().lower()
        for key, metric in metrics.items():
            if metric.get("ambiguous"): continue
            
            display = metric.get("display_name", "").lower()
            unit = metric.get("unit", "")
            label = f"{display}"
            if unit:
                label += f" ({unit.lower()})"
                
            if answer == display or answer == label or answer == key.lower():
                logger.info(f"Clarification intercepted: bound directly to {key}")
                return {
                    "matched_metrics": [key],
                    "ambiguous": False,
                    "clarification_options": [],
                    "clarification_prompt": None,
                    "jargon_terms": metric.get("jargon_terms", []),
                    "resolved_info": [{
                        "metric_key": key,
                        "display_name": metric.get("display_name", key),
                        "canonical_column": metric.get("canonical_column"),
                        "table": metric.get("table"),
                        "unit": metric.get("unit"),
                        "description": metric.get("description", ""),
                    }],
                }
        
        # Clarification was given but no exact match — still do NOT re-trigger ambiguity
        logger.info(f"Clarification present but unmatched for '{answer}', proceeding without ambiguity lock")

    query_lower = query.lower()
    
    matched = []
    ambiguous_matches = []
    all_jargon = []
    resolved_info = []
    
    for key, metric in metrics.items():
        aliases = metric.get("aliases", [])
        
        # Check if any alias appears in the query
        for alias in aliases:
            if alias.lower() in query_lower:
                matched.append(key)
                
                # Collect jargon terms for this metric
                jargon = metric.get("jargon_terms", [])
                all_jargon.extend(jargon)
                
                # Check if this metric is ambiguous
                if metric.get("ambiguous", False):
                    ambiguous_matches.append({
                        "metric_key": key,
                        "clarification_prompt": metric.get("clarification_prompt", ""),
                        "resolves_to": metric.get("resolves_to", []),
                        "options": _build_options(metric, metrics),
                    })
                else:
                    resolved_info.append({
                        "metric_key": key,
                        "display_name": metric.get("display_name", key),
                        "canonical_column": metric.get("canonical_column"),
                        "table": metric.get("table"),
                        "unit": metric.get("unit"),
                        "description": metric.get("description", ""),
                    })
                
                break  # Only match first alias per metric
    
    # Deduplicate
    matched = list(dict.fromkeys(matched))
    
    # IMPORTANT: If user already provided a clarification answer, NEVER re-trigger
    # ambiguity even if the original query still contains an ambiguous term like "performance"
    is_ambiguous = len(ambiguous_matches) > 0 and not is_clarification_response
    
    result = {
        "matched_metrics": matched,
        "ambiguous": is_ambiguous,
        "clarification_options": ambiguous_matches[0]["options"] if (ambiguous_matches and not is_clarification_response) else [],
        "clarification_prompt": ambiguous_matches[0]["clarification_prompt"] if (ambiguous_matches and not is_clarification_response) else None,
        "jargon_terms": list(set(all_jargon)),
        "resolved_info": resolved_info,
    }
    
    if is_ambiguous:
        logger.info(f"Metric resolution: AMBIGUOUS — {ambiguous_matches[0]['metric_key']}")
    elif matched:
        logger.info(f"Metric resolution: matched {matched}")
    
    return result


def _build_options(ambiguous_metric: dict, all_metrics: dict) -> list[dict]:
    """Build clarification options from an ambiguous metric's resolves_to list."""
    resolves_to = ambiguous_metric.get("resolves_to", [])
    options = []
    
    for target_key in resolves_to:
        target = all_metrics.get(target_key, {})
        display = target.get("display_name", target_key)
        unit = target.get("unit", "")
        
        label = f"{display}"
        if unit:
            label += f" ({unit})"
        
        options.append({
            "label": label,
            "value": target_key,
            "description": target.get("description", ""),
        })
    
    return options


def get_jargon_map() -> dict[str, str]:
    """
    Build a jargon → display_name mapping for the Semantic Validator.
    Used to replace technical terms in final responses.
    """
    metrics = _load_metrics()
    jargon_map = {}
    
    for key, metric in metrics.items():
        display = metric.get("display_name")
        if not display:
            continue
        for term in metric.get("jargon_terms", []):
            jargon_map[term] = display
    
    return jargon_map


def get_all_metrics_for_glossary() -> list[dict]:
    """
    Return all metrics formatted for the frontend Glossary component.
    Exposed via GET /metrics endpoint.
    """
    metrics = _load_metrics()
    glossary = []
    
    for key, metric in metrics.items():
        if metric.get("display_name") is None:
            continue  # Skip ambiguous meta-metrics
        glossary.append({
            "key": key,
            "display_name": metric["display_name"],
            "description": metric.get("description", ""),
            "unit": metric.get("unit", ""),
            "aliases": metric.get("aliases", []),
            "source": metric.get("source", "snowflake"),
        })
    
    return glossary
