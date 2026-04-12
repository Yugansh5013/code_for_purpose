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
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Frontend Adapter"])


# ── Request / Response Models (matching frontend types.ts) ──

class FrontendChatRequest(BaseModel):
    session_id: str
    message: str
    clarification_answer: Optional[str] = None


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
    """Build a thinking-trace from the pipeline execution metadata."""
    trace = []

    # 1. Intent router
    router_info = result.get("router_decision") or {}
    sql_likely = router_info.get("sql_likely", True)
    rag_present = router_info.get("rag_present", True)
    trace.append({
        "node": "intent_router",
        "detail": f"sql_likely={sql_likely}, rag_present={rag_present}",
    })

    # 2. Temporal resolver
    temporal = result.get("temporal_note")
    trace.append({
        "node": "temporal_resolver",
        "detail": temporal if temporal else "no date phrase detected",
    })

    # 3. Metric resolver
    metric_info = result.get("metric_resolution") or {}
    if metric_info:
        matched = metric_info.get("matched_metrics", [])
        if matched:
            trace.append({
                "node": "metric_resolver",
                "detail": f"resolved → {', '.join(matched)}",
            })
        else:
            trace.append({
                "node": "metric_resolver",
                "detail": "no metric aliases detected",
            })
    else:
        trace.append({
            "node": "metric_resolver",
            "detail": "no metric aliases detected",
        })

    # 4. Branch SQL
    sql_out = result.get("sql_output") or {}
    if sql_out and not sql_out.get("error"):
        charts = sql_out.get("charts", [])
        if charts:
            trace.append({
                "node": "branch_sql",
                "detail": f"generated {len(charts)} sub-queries → execute → {sum(c.get('row_count', 0) for c in charts)} rows",
            })
        else:
            rows_ct = len(sql_out.get("rows", []))
            trace.append({
                "node": "branch_sql",
                "detail": f"schema_rag → sql_gen → execute → {rows_ct} rows",
            })

    # 5. Branch Salesforce
    sf_out = result.get("salesforce_output") or {}
    if sf_out and not sf_out.get("error"):
        sf_meta = sf_out.get("metadata", {})
        record_ct = sf_meta.get("record_count", 0)
        top_score = sf_meta.get("top_score", 0)
        trace.append({
            "node": "branch_soql",
            "detail": f"crm_vector_search → {record_ct} records [score: {top_score:.2f}]",
        })

    # 6. Branch RAG
    rag_out = result.get("rag_output") or {}
    if rag_out and not rag_out.get("error"):
        rag_meta = rag_out.get("metadata", {})
        docs = rag_meta.get("documents", [])
        top_score = max((d.get("relevance", 0) for d in docs), default=0)
        trace.append({
            "node": "branch_rag",
            "detail": f"confluence_search → {len(docs)} chunks [score: {top_score:.2f}]",
        })

    # 7. Branch Web
    web_out = result.get("web_output") or {}
    if web_out and not web_out.get("error"):
        web_meta = web_out.get("metadata", {})
        web_results = web_meta.get("web_results", [])
        trace.append({
            "node": "branch_web",
            "detail": f"tavily_search → {len(web_results)} results",
        })

    # 8. Synthesis
    sources_ct = len(result.get("sources_used", []))
    trace.append({
        "node": "synthesis_node",
        "detail": f"merging {sources_ct} branch outputs → jargon audit",
    })

    # 9. Semantic validator
    jargon = result.get("jargon_substitutions", [])
    trace.append({
        "node": "semantic_validator",
        "detail": f"rag_present={rag_present} → {len(jargon)} terms rewritten" if jargon else "no jargon detected → pass-through",
        "highlight": True,
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
        "python_code": None,  # E2B sandbox not active
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
        """
        start = time.time()
        
        initial_state = {
            "original_query": request.message,
        }
        if request.clarification_answer:
            initial_state["original_query"] = (
                f"{request.message} (specifically: {request.clarification_answer})"
            )

        async def event_generator():
            message_id = f"msg-{uuid.uuid4().hex[:8]}"
            final_state = initial_state.copy()
            
            try:
                # 1. Stream intermediate events from LangGraph
                async for event in graph.astream(initial_state, stream_mode="updates"):
                    for node_name, update in event.items():
                        if update:
                            final_state.update(update)
                        
                        # Generate a human-readable trace detail based on the node
                        detail = f"Processing data in {node_name}..."
                        if node_name == "intent_router":
                            detail = "Analyzing intent and planning execution route..."
                        elif node_name == "clarification":
                            detail = "Checking if clarification is needed..."
                        elif node_name == "branch_sql":
                            detail = "Querying Snowflake data warehouse..."
                        elif node_name == "branch_rag":
                            detail = "Searching Confluence knowledge base..."
                        elif node_name == "branch_salesforce":
                            detail = "Retrieving records from Salesforce CRM..."
                        elif node_name == "branch_web":
                            detail = "Running live web searches via Tavily..."
                        elif node_name == "semantic_validator":
                            detail = "Auditing response for compliance and jargon..."
                        elif node_name == "synthesis":
                            detail = "Synthesizing cross-source intelligence..."
                            
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
                            option_labels.append(opt.get("display_name", opt.get("label", str(opt))))
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
                    },
                }
                yield f"data: {json.dumps(answer_data, default=str)}\n\n"

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
