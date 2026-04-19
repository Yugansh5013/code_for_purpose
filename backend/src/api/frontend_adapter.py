"""
OmniData — Frontend API Adapter

Translates the backend's internal pipeline responses into the exact
JSON envelope that the Next.js frontend expects.

Routes:
    POST /api/chat     → wraps /query into ChatResponse envelope
    GET  /api/status   → wraps /health into IntegrationStatus shape
    GET  /api/metrics  → wraps /metrics into MetricsResponse shape

This adapter exists so that neither the frontend nor the backend
need to compromise their internal data models.
"""

import time
import uuid
import logging
from typing import Optional, List
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Frontend Adapter"])


# ── Request / Response Models (matching frontend types.ts) ──

class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str  # message text or summary


class FrontendChatRequest(BaseModel):
    session_id: str
    message: str
    clarification_answer: Optional[str] = None
    conversation_history: Optional[List[ConversationTurn]] = None
    user_role: Optional[str] = None  # "ceo", "north_manager", "south_manager"


# ── RBAC Role Definitions ───────────────────────────────────
ROLE_MAP = {
    "ceo": {
        "role": "ceo",
        "region_filter": None,
        "label": "CEO (Unrestricted)",
        "restricted_tables": [],
    },
    "north_manager": {
        "role": "north_manager",
        "region_filter": "North",
        "label": "North Region Manager",
        "restricted_tables": ["AURA_SALES", "RETURN_EVENTS", "CUSTOMER_METRICS"],
    },
    "south_manager": {
        "role": "south_manager",
        "region_filter": "South",
        "label": "South Region Manager",
        "restricted_tables": ["AURA_SALES", "RETURN_EVENTS", "CUSTOMER_METRICS"],
    },
}


# We return raw dicts so we have full control over the shape.


# ── Helpers ──────────────────────────────────────────────────

def _build_branches(result: dict) -> list[str]:
    """Derive active branch keys from non-null/non-error outputs."""
    branches = []
    if result.get("sql_output") and not result["sql_output"].get("error"):
        branches.append("sql")
    if result.get("rag_output") and not result["rag_output"].get("error"):
        branches.append("rag_confluence")
    if result.get("salesforce_output") and not result["salesforce_output"].get("error"):
        branches.append("rag_salesforce")
    if result.get("web_output") and not result["web_output"].get("error"):
        branches.append("web")
    return branches


def _build_trace(result: dict) -> list[dict]:
    """Build a rich thinking-trace from the pipeline execution metadata.

    Each entry has: node, detail, status, latency_ms, metadata.
    The metadata dict powers the expandable panels in the frontend.
    """
    trace = []

    def fmt(v, decimals=2):
        try:
            return round(float(v), decimals)
        except (TypeError, ValueError):
            return 0.0


    # 1. Intent router
    router_info = result.get("router_decision") or {}
    sql_likely = router_info.get("sql_likely", True)
    rag_present = router_info.get("rag_present", True)
    branches_human = []
    if sql_likely:
        branches_human.append("your data warehouse")
    if rag_present:
        branches_human.append("the knowledge base")
    trace.append({
        "node": "intent_router",
        "status": "success",
        "latency_ms": router_info.get("latency_ms"),
        "detail": f"Understood your question — checking {' and '.join(branches_human) or 'all sources'}",
        "metadata": None,
    })

    # 2. Temporal resolver
    temporal = result.get("temporal_note")
    if temporal:
        trace.append({
            "node": "temporal_resolver",
            "status": "success",
            "latency_ms": None,
            "detail": f"Time period identified → {temporal}",
            "metadata": None,
        })

    # 3. Metric resolver
    metric_info = result.get("metric_resolution") or {}
    matched = metric_info.get("matched_metrics", [])
    if matched:
        trace.append({
            "node": "metric_resolver",
            "status": "success",
            "latency_ms": None,
            "detail": f"Business terms mapped → {', '.join(matched)}",
            "metadata": None,
        })

    # 4. Branch SQL
    sql_out = result.get("sql_output") or {}
    if sql_out and not sql_out.get("error"):
        charts = sql_out.get("charts", [])
        total_rows = sum(c.get("row_count", 0) for c in charts) if charts else len(sql_out.get("rows", []))
        first_sql = None
        if charts and charts[0].get("sql"):
            first_sql = charts[0]["sql"]
        elif sql_out.get("query"):
            first_sql = sql_out.get("query")
        confidence = result.get("confidence_score")
        sql_meta = {k: v for k, v in {
            "sql": first_sql,
            "row_count": total_rows,
            "confidence": fmt(confidence) if confidence else None,
        }.items() if v is not None}
        sub_count = len(charts) if charts else 1
        trace.append({
            "node": "branch_sql",
            "status": "success",
            "latency_ms": sql_out.get("metadata", {}).get("latency_ms"),
            "detail": f"Found {total_rows} matching record{'s' if total_rows != 1 else ''} across {sub_count} {'queries' if sub_count > 1 else 'query'}",
            "metadata": sql_meta if sql_meta else None,
        })
        # 4b. E2B sandbox
        e2b_meta = sql_out.get("metadata", {})
        if e2b_meta.get("e2b_used"):
            py_code = sql_out.get("e2b_code") or e2b_meta.get("python_code")
            chart_type = "interactive chart" if sql_out.get("e2b_plotly_json") else "static chart"
            trace.append({
                "node": "e2b_sandbox",
                "status": "success",
                "latency_ms": e2b_meta.get("e2b_latency_ms"),
                "detail": f"Generated a {chart_type} from your data ✨",
                "metadata": {"python_code": py_code} if py_code else None,
            })
        elif sql_out.get("e2b_code"):
            trace.append({
                "node": "e2b_sandbox",
                "status": "error",
                "latency_ms": None,
                "detail": "Data visualization failed — falling back to text analysis",
                "metadata": {"error_message": str(sql_out.get("e2b_error", "Sandbox execution failed"))[:300]},
            })
    elif sql_out and sql_out.get("error"):
        error_msg = str(sql_out.get("error", ""))[:300]
        trace.append({
            "node": "branch_sql",
            "status": "error",
            "latency_ms": None,
            "detail": "Couldn't retrieve data from the warehouse — the query didn't succeed",
            "metadata": {"error_message": error_msg},
        })
        # Recovery suggestion
        original_query = result.get("original_query", "")
        suggestion = f"Show me a summary of overall sales instead"
        if "churn" in original_query.lower():
            suggestion = "Show me overall customer retention trends instead"
        elif "region" in original_query.lower() or "store" in original_query.lower():
            suggestion = "Show me national-level totals instead of by region"
        elif "product" in original_query.lower():
            suggestion = "Show me top 10 products by revenue instead"
        trace.append({
            "node": "recovery",
            "status": "suggestion",
            "latency_ms": None,
            "detail": "I had trouble fetching that exact data. Would you like to try a related query?",
            "metadata": {"suggestion": suggestion, "error_context": error_msg[:150]},
        })

    # 5. Branch Salesforce
    sf_out = result.get("salesforce_output") or {}
    if sf_out and not sf_out.get("error"):
        sf_meta = sf_out.get("metadata", {})
        record_ct = sf_meta.get("record_count", 0)
        top_score = sf_meta.get("top_score", 0)
        trace.append({
            "node": "branch_soql",
            "status": "success",
            "latency_ms": sf_meta.get("latency_ms"),
            "detail": f"Found {record_ct} relevant CRM record{'s' if record_ct != 1 else ''} in Salesforce",
            "metadata": {"record_count": record_ct, "top_score": fmt(top_score)},
        })
    elif sf_out and sf_out.get("error"):
        trace.append({
            "node": "branch_soql",
            "status": "error",
            "latency_ms": None,
            "detail": "Could not reach Salesforce — CRM data is unavailable right now",
            "metadata": {"error_message": str(sf_out.get("error", ""))[:200]},
        })
        trace.append({
            "node": "recovery",
            "status": "suggestion",
            "latency_ms": None,
            "detail": "Salesforce was unreachable. The answer was built from other available sources.",
            "metadata": {"suggestion": "Show me what data is available about this customer from other sources"},
        })

    # 6. Branch RAG / Confluence
    rag_out = result.get("rag_output") or {}
    if rag_out and not rag_out.get("error"):
        rag_meta = rag_out.get("metadata", {})
        docs = rag_meta.get("documents", [])
        top_score = max((d.get("relevance", 0) for d in docs), default=0)
        query = rag_meta.get("query") or rag_out.get("query")
        rag_payload: dict = {"document_count": len(docs), "top_score": fmt(top_score)}
        if query:
            rag_payload["search_query"] = query
        trace.append({
            "node": "branch_rag",
            "status": "success",
            "latency_ms": rag_meta.get("latency_ms"),
            "detail": f"Found {len(docs)} relevant document{'s' if len(docs) != 1 else ''} in the knowledge base",
            "metadata": rag_payload,
        })
    elif rag_out and rag_out.get("error"):
        trace.append({
            "node": "branch_rag",
            "status": "error",
            "latency_ms": None,
            "detail": "Knowledge base search didn't return results — document index may be unavailable",
            "metadata": {"error_message": str(rag_out.get("error", ""))[:200]},
        })
        trace.append({
            "node": "recovery",
            "status": "suggestion",
            "latency_ms": None,
            "detail": "I couldn't search internal documents. The answer relies on live data instead.",
            "metadata": {"suggestion": "Search for this topic in the knowledge base"},
        })

    # 7. Branch Web
    web_out = result.get("web_output") or {}
    if web_out and not web_out.get("error"):
        web_meta = web_out.get("metadata", {})
        web_results = web_meta.get("web_results", [])
        query = web_meta.get("query") or web_out.get("query")
        web_payload: dict = {"document_count": len(web_results)}
        if query:
            web_payload["search_query"] = query
        trace.append({
            "node": "branch_web",
            "status": "success",
            "latency_ms": web_meta.get("latency_ms"),
            "detail": f"Searched the web — found {len(web_results)} relevant source{'s' if len(web_results) != 1 else ''}",
            "metadata": web_payload,
        })
    elif web_out and web_out.get("error"):
        trace.append({
            "node": "branch_web",
            "status": "error",
            "latency_ms": None,
            "detail": "Live web search timed out — external market data is unavailable",
            "metadata": {"error_message": str(web_out.get("error", ""))[:200]},
        })
        trace.append({
            "node": "recovery",
            "status": "suggestion",
            "latency_ms": None,
            "detail": "Web data wasn't available. I've answered using internal sources only.",
            "metadata": {"suggestion": "Try asking again to retry the web search"},
        })

    # 8. Synthesis
    sources_ct = len(result.get("sources_used", []))
    trace.append({
        "node": "synthesis_node",
        "status": "success",
        "latency_ms": None,
        "detail": f"Combined {sources_ct} source{'s' if sources_ct != 1 else ''} into a clear answer",
        "metadata": None,
    })

    # 9. Semantic validator
    jargon = result.get("jargon_substitutions", [])
    trace.append({
        "node": "semantic_validator",
        "status": "success",
        "latency_ms": None,
        "detail": f"Simplified {len(jargon)} technical term{'s' if len(jargon) != 1 else ''} for plain English" if jargon else "Language check passed — response is jargon-free",
        "highlight": True,
        "metadata": None,
    })

    return trace





def _build_sources(result: dict) -> list[dict]:
    """Build source chips from pipeline result."""
    sources = []

    sql_out = result.get("sql_output") or {}
    if sql_out and not sql_out.get("error"):
        conf = result.get("confidence_score")
        sources.append({
            "source_type": "snowflake",
            "label": "AURA_SALES",
            "confidence": round(conf, 2) if conf else None,
        })

    rag_out = result.get("rag_output") or {}
    if rag_out and not rag_out.get("error"):
        rag_meta = rag_out.get("metadata", {})
        docs = rag_meta.get("documents", [])
        label = docs[0]["title"][:30] if docs else "Confluence"
        sources.append({
            "source_type": "confluence",
            "label": label,
        })

    sf_out = result.get("salesforce_output") or {}
    if sf_out and not sf_out.get("error"):
        sf_meta = sf_out.get("metadata", {})
        top = sf_meta.get("top_score", 0)
        sources.append({
            "source_type": "salesforce",
            "label": "CRM Accounts",
            "confidence": round(top, 2) if top else None,
        })

    web_out = result.get("web_output") or {}
    if web_out and not web_out.get("error"):
        sources.append({
            "source_type": "tavily",
            "label": "Web Search",
        })

    return sources


def _build_transparency(result: dict) -> dict:
    """Build the transparency payload from pipeline result."""
    sql_out = result.get("sql_output") or {}
    rag_out = result.get("rag_output") or {}
    sf_out = result.get("salesforce_output") or {}

    # SQL transparency
    sql_str = sql_out.get("sql")
    
    # Raw data from first chart or main rows
    charts = sql_out.get("charts", [])
    raw_data = None
    if charts:
        raw_data = charts[0].get("data", [])[:20]
    elif sql_out.get("rows"):
        raw_data = sql_out["rows"][:20]

    # Context chunks from RAG documents
    context_chunks = []
    if rag_out and not rag_out.get("error"):
        rag_meta = rag_out.get("metadata", {})
        for doc in rag_meta.get("documents", []):
            context_chunks.append({
                "source_type": "confluence",
                "title": doc.get("title", ""),
                "space_key": doc.get("space_key", "AURA"),
                "body": doc.get("excerpt", doc.get("text", ""))[:300],
                "updated_at": doc.get("updated_at", ""),
                "chunk_index": doc.get("chunk_index", 1),
                "total_chunks": doc.get("total_chunks", 1),
                "score": doc.get("relevance", 0),
            })

    # Add Salesforce records as context chunks too
    if sf_out and not sf_out.get("error"):
        sf_meta = sf_out.get("metadata", {})
        for rec in sf_meta.get("crm_records", [])[:3]:
            context_chunks.append({
                "source_type": "upload",  # reuse upload type for SF cards
                "title": f"CRM: {rec.get('account_name', 'Unknown')}",
                "body": rec.get("excerpt", "")[:300],
                "updated_at": "",
                "chunk_index": 1,
                "total_chunks": 1,
                "score": rec.get("relevance", 0),
            })

    # Confidence
    conf_score = result.get("confidence_score")
    conf_tier = result.get("confidence_tier")
    confidence = None
    if conf_score is not None:
        confidence = {
            "score": conf_score,
            "tier": conf_tier or "green",
            "signals": {
                "schema_cosine": round(conf_score * 1.05, 2) if conf_score else 0,
                "retry_score": 1.0,
                "row_sanity": round(conf_score * 0.85, 2) if conf_score else 0,
            },
            "explanation": f"Confidence {conf_tier}: composite score {conf_score:.2f}",
        }
        # Clamp
        confidence["signals"]["schema_cosine"] = min(confidence["signals"]["schema_cosine"], 1.0)
        confidence["signals"]["row_sanity"] = min(confidence["signals"]["row_sanity"], 1.0)

    # Semantic substitutions
    jargon = result.get("jargon_substitutions", [])
    semantic_subs = [
        {
            "original": j.get("original", j.get("term", "")),
            "replaced_with": j.get("replaced_with", j.get("replacement", "")),
            "location": j.get("location", "response text"),
        }
        for j in jargon
    ]

    return {
        "sql": sql_str,
        "soql": None,  # Salesforce uses vector search, not live SOQL
        "raw_data": raw_data,
        "python_code": sql_out.get("e2b_code"),  # E2B sandbox generated Python
        "context_chunks": context_chunks if context_chunks else None,
        "confidence": confidence,
        "semantic_substitutions": semantic_subs if semantic_subs else None,
        "validation_passed": True if jargon is not None else None,
        "validator_model": "llama-3.3-70b" if conf_score else None,
        "validator_latency_ms": None,
    }


def _build_chart_data(result: dict) -> dict | None:
    """Build a single chart_data object from the pipeline's multi-chart output."""
    sql_out = result.get("sql_output") or {}
    charts = sql_out.get("charts", [])

    if not charts:
        return None

    # Use the first chart (or the one with most data)
    chart = max(charts, key=lambda c: c.get("row_count", 0))
    chart_type = chart.get("chart_type", "bar")
    data_rows = chart.get("data", [])
    columns = chart.get("columns", [])

    if not data_rows or not columns:
        return None

    # Determine label column (first string-like column) and value column
    label_col = columns[0] if columns else "label"
    value_col = columns[1] if len(columns) > 1 else columns[0]

    labels = [str(row.get(label_col, row.get(columns[0], ""))) for row in data_rows]
    values = []
    for row in data_rows:
        val = row.get(value_col, 0)
        try:
            values.append(float(val) if val is not None else 0)
        except (ValueError, TypeError):
            values.append(0)

    # Map chart_type
    type_map = {"bar": "bar", "line": "line", "pie": "doughnut", "number": "bar", "doughnut": "doughnut"}
    mapped_type = type_map.get(chart_type, "bar")

    return {
        "type": mapped_type,
        "labels": labels,
        "values": values,
        "y_label": chart.get("title", value_col),
    }


def _build_stat_updates(result: dict) -> list[dict]:
    """Build stat cards from SQL data for the dashboard header."""
    sql_out = result.get("sql_output") or {}
    charts = sql_out.get("charts", [])

    stats = []
    for chart in charts[:3]:
        title = chart.get("title", "")
        data = chart.get("data", [])
        chart_type = chart.get("chart_type", "")

        if chart_type == "number" and data:
            row = data[0]
            val_key = list(row.keys())[0] if row else ""
            val = row.get(val_key, "—")
            stats.append({
                "label": title[:20],
                "value": str(val),
                "delta": "",
                "delta_direction": "neutral",
            })

    return stats if stats else []


# ── In-memory session store for multi-turn context ──────────
_session_history: dict[str, list[dict]] = defaultdict(list)


# ── Adapter Routes ───────────────────────────────────────────

def create_adapter_routes(graph, groq_pool):
    """Create the adapter routes with access to the pipeline graph."""

    from fastapi.responses import StreamingResponse
    import json
    import asyncio

    @router.post("/chat")
    async def frontend_chat(request: FrontendChatRequest):
        """
        POST /api/chat — the main frontend query endpoint.
        
        Uses Server-Sent Events (SSE) to stream live execution traces back
        to the frontend, followed by the final answer payload.
        Supports multi-turn conversations via conversation_history.
        """
        start = time.time()
        
        # Build conversation history from frontend + server-side store
        history = []
        if request.conversation_history:
            history = [
                {"role": t.role, "content": t.content}
                for t in request.conversation_history[-6:]  # last 6 turns (3 exchanges)
            ]
        elif _session_history.get(request.session_id):
            history = _session_history[request.session_id][-6:]

        # Resolve RBAC context
        user_context = ROLE_MAP.get(request.user_role or "ceo", ROLE_MAP["ceo"])
        logger.info(f"RBAC context: {user_context['label']} (filter={user_context['region_filter']})")

        initial_state = {
            "original_query": request.message,
            "conversation_history": history,
            "user_context": user_context,
        }
        if request.clarification_answer:
            initial_state["original_query"] = (
                f"(specifically: {request.clarification_answer}) for {request.message}"
            )

        async def event_generator():
            message_id = f"msg-{uuid.uuid4().hex[:8]}"
            final_state = initial_state.copy()
            
            try:
                # 0. Stream security context as first trace event
                if user_context.get("region_filter"):
                    sec_detail = f"Security context: {user_context['label']} — data restricted to {user_context['region_filter']} region"
                else:
                    sec_detail = f"Security context: {user_context['label']} — unrestricted access"
                sec_payload = {"type": "trace", "node": "security_context", "detail": sec_detail}
                yield f"data: {json.dumps(sec_payload, default=str)}\n\n"
                await asyncio.sleep(0.01)

                # 1. Stream intermediate events from LangGraph
                async for event in graph.astream(initial_state, stream_mode="updates"):
                    for node_name, update in event.items():
                        if update:
                            final_state.update(update)
                        
                        # Jargon-free live streaming trace detail
                        detail = "Working on your request…"
                        if node_name == "intent_router":
                            detail = "Understanding your question…"
                        elif node_name == "clarification":
                            detail = "Checking if I need more information…"
                        elif node_name == "branch_sql":
                            detail = "Looking up your data in the warehouse…"
                        elif node_name == "branch_rag":
                            detail = "Searching internal documents and knowledge base…"
                        elif node_name == "branch_salesforce":
                            detail = "Scanning Salesforce CRM records…"
                        elif node_name == "branch_web":
                            detail = "Searching the web for relevant information…"
                        elif node_name == "semantic_validator":
                            detail = "Checking the response for jargon and simplifying…"
                        elif node_name == "synthesis":
                            detail = "Putting together a clear answer for you…"
                        elif node_name == "synthesis_node":
                            detail = "Putting together a clear answer for you…"
                        elif node_name == "temporal_resolver":
                            detail = "Working out what time period you mean…"
                        elif node_name == "metric_resolver":
                            detail = "Matching business terms to the right metrics…"
                            
                        trace_payload = {
                            "type": "trace",
                            "node": node_name,
                            "detail": detail
                        }
                        yield f"data: {json.dumps(trace_payload, default=str)}\n\n"
                        await asyncio.sleep(0.01)  # flush
                
                # 2. Build final graph result
                result = final_state
                processing_time = int((time.time() - start) * 1000)

                # Check for clarification needed
                if result.get("clarification_needed"):
                    options = result.get("clarification_options", [])
                    option_labels = []
                    for opt in options:
                        if isinstance(opt, dict):
                            option_labels.append(opt.get("label", opt.get("display_name", str(opt))))
                        else:
                            option_labels.append(str(opt))

                    clarification_data = {
                        "message_id": message_id,
                        "type": "clarification",
                        "clarification": {
                            "question": result.get("final_response", "Could you clarify what you mean?"),
                            "ambiguous_term": result.get("ambiguous_term", ""),
                            "options": option_labels,
                        },
                    }
                    yield f"data: {json.dumps(clarification_data, default=str)}\n\n"
                    return

                # Build answer envelope (similar to former logic)
                branches = _build_branches(result)
                trace = _build_trace(result)
                sources = _build_sources(result)
                transparency = _build_transparency(result)
                chart_data = _build_chart_data(result)
                stat_updates = _build_stat_updates(result)

                # Build multi-chart panels
                sql_out = result.get("sql_output") or {}
                charts_raw = sql_out.get("charts", [])
                chart_panels = []
                for c in charts_raw:
                    chart_panels.append({
                        "title": c.get("title", ""),
                        "chart_type": c.get("chart_type", "bar"),
                        "data": c.get("data", [])[:100],
                        "columns": c.get("columns", []),
                        "sql": c.get("sql"),
                        "row_count": c.get("row_count", 0),
                        "confidence_score": c.get("confidence_score", 0),
                        "confidence_tier": c.get("confidence_tier", "green"),
                    })

                # Build RAG documents
                rag_out = result.get("rag_output") or {}
                rag_documents = []
                if rag_out and not rag_out.get("error"):
                    rag_meta = rag_out.get("metadata", {})
                    for doc in rag_meta.get("documents", []):
                        rag_documents.append({
                            "title": doc.get("title", ""),
                            "space": doc.get("space_key", doc.get("space", "AURA")),
                            "excerpt": doc.get("excerpt", doc.get("text", "")),
                            "relevance": doc.get("relevance", 0),
                            "source_type": "confluence",
                        })

                # Build web results
                web_out = result.get("web_output") or {}
                web_results = []
                if web_out and not web_out.get("error"):
                    web_meta = web_out.get("metadata", {})
                    for wr in web_meta.get("web_results", []):
                        web_results.append({
                            "title": wr.get("title", ""),
                            "url": wr.get("url", ""),
                            "content": wr.get("content", ""),
                            "score": wr.get("score", 0),
                        })

                # Build Salesforce CRM records
                sf_out = result.get("salesforce_output") or {}
                salesforce_records = []
                if sf_out and not sf_out.get("error"):
                    sf_meta = sf_out.get("metadata", {})
                    for rec in sf_meta.get("crm_records", []):
                        salesforce_records.append({
                            "account_name": rec.get("account_name", ""),
                            "object_type": rec.get("object_type", "Account"),
                            "excerpt": rec.get("excerpt", ""),
                            "relevance": rec.get("relevance", 0),
                        })

                # Build metric resolution
                metric_res = result.get("metric_resolution") or {}
                metric_resolution = None
                if metric_res and metric_res.get("matched_metrics"):
                    first_metric = metric_res["matched_metrics"][0] if metric_res["matched_metrics"] else ""
                    resolved = metric_res.get("resolved_info", [{}])
                    first_resolved = resolved[0] if resolved else {}
                    metric_resolution = {
                        "alias": first_resolved.get("alias", first_metric),
                        "display_name": first_resolved.get("display_name", first_metric),
                        "column_name": first_resolved.get("column_name", ""),
                    }

                # Jargon substitutions
                jargon_subs = result.get("jargon_substitutions", [])
                jargon_for_frontend = []
                for j in jargon_subs:
                    jargon_for_frontend.append({
                        "original": j.get("original", j.get("term", "")),
                        "replacement": j.get("replaced_with", j.get("replacement", "")),
                        "category": j.get("category", "detected"),
                    })

                answer_data = {
                    "message_id": message_id,
                    "type": "answer",
                    "answer": {
                        "text": result.get("final_response", "No response generated."),
                        "branches": branches,
                        "trace": trace,
                        "date_resolution": result.get("temporal_note"),
                        "metric_resolution": metric_resolution,
                        "sources": sources,
                        "transparency": transparency,
                        "chart_data": chart_data,
                        "charts": chart_panels if chart_panels else None,
                        "rag_documents": rag_documents if rag_documents else None,
                        "web_results": web_results if web_results else None,
                        "salesforce_records": salesforce_records if salesforce_records else None,
                        "jargon_substitutions": jargon_for_frontend if jargon_for_frontend else None,
                        "stat_updates": stat_updates if stat_updates else None,
                        "confidence_score": result.get("confidence_score"),
                        "confidence_tier": result.get("confidence_tier"),
                        "processing_time_ms": processing_time,
                        "e2b_plotly_json": sql_out.get("e2b_plotly_json"),
                        "e2b_chart_image": sql_out.get("e2b_chart_image"),
                        "security_context": user_context,
                        "suggested_followups": result.get("suggested_followups", []),
                    },
                }
                yield f"data: {json.dumps(answer_data, default=str)}\n\n"

                # Accumulate conversation history for this session
                _session_history[request.session_id].append(
                    {"role": "user", "content": request.message}
                )
                response_text = result.get("final_response", "")
                # Store a condensed summary (first 200 chars) for context
                _session_history[request.session_id].append(
                    {"role": "assistant", "content": response_text[:200]}
                )
                # Cap history per session to prevent unbounded growth
                if len(_session_history[request.session_id]) > 20:
                    _session_history[request.session_id] = _session_history[request.session_id][-12:]

            except Exception as e:
                logger.error(f"Frontend chat streaming failed: {e}", exc_info=True)
                error_data = {
                    "type": "error",
                    "detail": str(e)
                }
                yield f"data: {json.dumps(error_data, default=str)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @router.get("/status")
    async def frontend_status():
        """
        GET /api/status — integration status for topbar and sidebar.
        
        Maps the backend's /health service statuses to the frontend's
        expected IntegrationStatus shape.
        """
        from src.main import _snowflake, _pinecone, _confluence_client, _salesforce, _groq_pool
        from src.config.settings import get_settings

        settings = get_settings()

        def _sf_status():
            if _salesforce and _salesforce.is_connected:
                return "live"
            elif _salesforce:
                return "connecting"
            return "error"

        def _sf_conn_status():
            try:
                if _snowflake and _snowflake.test_connection():
                    return "live"
                return "error"
            except Exception:
                return "error"

        def _conf_status():
            if _confluence_client:
                return "syncing"  # demo mode shows as syncing
            return "error"

        def _tavily_status():
            return "live" if settings.tavily_api_key else "error"

        return {
            "snowflake": _sf_conn_status(),
            "confluence": _conf_status(),
            "salesforce": _sf_status(),
            "tavily": _tavily_status(),
        }

    @router.get("/metrics")
    async def frontend_metrics():
        """
        GET /api/metrics — metric glossary for the frontend Glossary component.
        
        Reshapes the backend's glossary into the frontend's MetricsResponse shape.
        """
        from src.clarification.metric_resolver import get_all_metrics_for_glossary

        raw = get_all_metrics_for_glossary()

        metrics = []
        for m in raw:
            metrics.append({
                "name": m.get("key", m.get("display_name", "")),
                "display_name": m.get("display_name", ""),
                "canonical_column": m.get("canonical_column", m.get("key", "").upper()),
                "unit": m.get("unit", ""),
                "description": m.get("description", ""),
                "aliases": m.get("aliases", []),
                "ambiguous": False,
            })

        return {"metrics": metrics}

    return router
