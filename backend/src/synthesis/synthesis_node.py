"""
OmniData — Synthesis Node (Node 2)

Synthesizes all branch outputs into a clean, jargon-free business narrative
using Llama 3.3 70B.

Designed to handle N branch outputs generically — adding a new branch
requires no changes to this node.
"""

import json
import logging
from typing import Any

from src.state import GraphState
from src.clarification.metric_resolver import get_jargon_map

logger = logging.getLogger(__name__)

# ── Model ──────────────────────────────────────────────────────
SYNTHESIS_MODEL = "llama-3.3-70b-versatile"


# ── Synthesis prompt ───────────────────────────────────────────
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
9. When citing information from the Internal Knowledge Base, mention the document title naturally in your response.
10. You MUST return your answer as a valid JSON object with EXACTLY two keys:
    - "response": Your synthesized business narrative.
    - "suggested_followups": An array of exactly 3 relevant follow-up questions the user might want to ask next based on this data.

## Jargon Substitution Rules:
Replace these technical terms if they appear in your response:
{jargon_rules}

## Data Sources:
{sources_section}

## Conversation Context (if follow-up):
{conversation_context}

## User Question:
{user_question}
"""


async def synthesis_node(state: GraphState, groq_pool: Any) -> dict:
    """
    Node 2: Synthesize all branch outputs into a final response using Llama 3.3 70B.
    """
    query = state.get("original_query", "")

    # ── Collect all branch outputs ───────────────────────
    sources = []
    sources_section_parts = []

    branch_outputs = [
        ("sql_output",        "Snowflake Data Warehouse"),
        ("rag_output",        "Internal Knowledge Base"),
        ("salesforce_output", "Salesforce CRM"),
        ("web_output",        "External Market Intelligence"),
    ]

    for output_key, label in branch_outputs:
        output = state.get(output_key)
        if output is None:
            continue

        source_info = {
            "source":     output.get("source", output_key),
            "label":      output.get("source_label", label),
            "confidence": output.get("confidence_score", None),
        }
        sources.append(source_info)

        if output.get("error"):
            sources_section_parts.append(
                f"### {label}\n**Error:** {output['error']}"
            )
        elif output_key == "sql_output":
            charts = output.get("charts", [])
            if len(charts) > 1:
                for idx, chart in enumerate(charts):
                    chart_title = chart.get("title", f"Analysis {idx + 1}")
                    chart_sql   = chart.get("sql", "")
                    chart_rows  = chart.get("data", [])[:20]
                    chart_conf  = chart.get("confidence_tier", "unknown")
                    rows_text   = json.dumps(chart_rows, indent=2, default=str)
                    sources_section_parts.append(
                        f"### {label} — Sub-analysis {idx + 1}: {chart_title} (confidence: {chart_conf})\n"
                        f"**SQL Query:** {chart_sql}\n\n"
                        f"**Results ({len(chart_rows)} rows):**\n```json\n{rows_text}\n```"
                    )
            else:
                sql          = output.get("sql", "")
                rows         = output.get("rows", [])
                confidence   = output.get("confidence_tier", "unknown")
                display_rows = rows[:30]
                rows_text    = json.dumps(display_rows, indent=2, default=str)
                sources_section_parts.append(
                    f"### {label} (confidence: {confidence})\n"
                    f"**SQL Query:** {sql}\n\n"
                    f"**Results ({len(rows)} rows):**\n```json\n{rows_text}\n```"
                )
        else:
            data = output.get("data", "")
            data_text = (
                json.dumps(data[:10], indent=2, default=str)
                if isinstance(data, list)
                else str(data)[:2000]
            )
            sources_section_parts.append(f"### {label}\n{data_text}")

    if not sources:
        return {
            "final_response": "I wasn't able to retrieve any data for your question. Could you try rephrasing it?",
            "draft_response": "",
            "sources_used":   [],
        }

    sources_section = "\n\n".join(sources_section_parts)

    # ── Build jargon rules ───────────────────────────────
    jargon_map   = get_jargon_map()
    jargon_rules = "\n".join([
        f"- Replace '{term}' with '{display}'"
        for term, display in jargon_map.items()
    ])

    # ── Build conversation context ────────────────────────
    history = state.get("conversation_history", []) or []
    conversation_context = "No prior conversation."
    if history:
        context_lines = []
        for turn in history[-4:]:
            role    = "User" if turn.get("role") == "user" else "Assistant"
            content = turn.get("content", "")[:200]
            context_lines.append(f"{role}: {content}")
        conversation_context = "\n".join(context_lines)

    # ════════════════════════════════════════════════════
    # Llama 3.3 70B — single-step synthesis
    # ════════════════════════════════════════════════════
    synthesis_prompt = SYNTHESIS_PROMPT.format(
        jargon_rules=jargon_rules or "No specific substitutions required.",
        sources_section=sources_section,
        conversation_context=conversation_context,
        user_question=query,
    )

    # Inject RBAC scoping directive for restricted users
    user_context = state.get("user_context") or {}
    if user_context.get("region_filter"):
        region = user_context["region_filter"]
        other_regions = [r for r in ["North", "South", "East", "West"] if r != region]
        synthesis_prompt += f"""

## Data Scope & Access Control
The current user is: {user_context.get('label', region + ' Manager')}.
They ONLY have access to {region} region data. The data above has been filtered accordingly.

IMPORTANT RULES:
1. If the user's question asks about {', '.join(other_regions)}, or "all regions", or any region other than {region}:
   → Start your response with: "As a {user_context.get('label', region + ' Manager')}, you only have access to {region} region data. I'm unable to show information for other regions."
   → Then offer to show the equivalent data for the {region} region instead.
   → Do NOT try to answer the question with {region} data pretending it answers a question about another region.

2. If the user's question is about the {region} region or is region-agnostic:
   → Naturally scope your language to the {region} region (e.g., "In the {region} region, revenue was...")
   → Do NOT mention access restrictions — just present the data naturally."""

    def _try_synthesize(model: str) -> tuple[str, list]:
        response = groq_pool.complete_with_retry(
            model=model,
            messages=[
                {"role": "system", "content": synthesis_prompt},
                {"role": "user", "content": "Please synthesize the data into a clear answer in JSON format as instructed."},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed.get("response", "Error generating response."), parsed.get("suggested_followups", [])

    try:
        final_response, suggested_followups = _try_synthesize(SYNTHESIS_MODEL)
        logger.info(f"Synthesis complete: {len(final_response)} chars, {len(suggested_followups)} followups")

        result: dict = {
            "draft_response": final_response,
            "final_response": final_response,
            "suggested_followups": suggested_followups,
            "sources_used": sources,
        }

        # Derive confidence for non-SQL queries
        sql_output = state.get("sql_output")
        rag_output = state.get("rag_output")
        web_output = state.get("web_output")

        if not sql_output:
            top_score = 0.0
            if rag_output and not rag_output.get("error"):
                top_score = max(top_score, rag_output.get("metadata", {}).get("top_score", 0.0))
            if web_output and not web_output.get("error"):
                top_score = max(top_score, web_output.get("metadata", {}).get("top_score", 0.0))

            if top_score > 0:
                tier = "green" if top_score >= 0.8 else ("amber" if top_score >= 0.6 else "red")
                result["confidence_score"] = round(top_score, 3)
                result["confidence_tier"] = tier

        return result

    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        fallback = _build_fallback_response(state, sources)
        return {
            "draft_response": fallback,
            "final_response": fallback,
            "sources_used":   sources,
        }


def _build_fallback_response(state: GraphState, sources: list[dict]) -> str:
    """Build a clean readable response when all synthesis models fail."""
    from decimal import Decimal

    def _fmt_val(v) -> str:
        if isinstance(v, Decimal):
            f = float(v)
            if f >= 1000:
                return f"£{f:,.2f}" if "SALES" in str(v) or "REVENUE" in str(v) else f"{f:,.0f}"
            return f"{f:.2f}"
        if isinstance(v, float):
            return f"{v:,.2f}"
        if isinstance(v, int):
            return f"{v:,}"
        return str(v)

    parts = ["Here's a summary of the data retrieved:\n"]
    sql_output = state.get("sql_output")
    if sql_output and not sql_output.get("error"):
        charts = sql_output.get("charts", [])
        rows_source = charts[0].get("data", []) if charts else sql_output.get("rows", [])
        if rows_source:
            parts.append(f"**{len(rows_source)} records returned from Snowflake:**\n")
            for row in rows_source[:8]:
                line = "  ".join(f"**{k.replace('_', ' ').title()}:** {_fmt_val(v)}" for k, v in row.items())
                parts.append(f"- {line}")
    rag_output = state.get("rag_output")
    if rag_output and not rag_output.get("error"):
        docs = rag_output.get("data", [])
        if docs:
            parts.append(f"\n**Knowledge Base:** Found {len(docs)} relevant document(s).")
    return "\n".join(parts)
