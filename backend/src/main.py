"""
OmniData — FastAPI Backend

Main entry point for the OmniData API.
Provides query execution, health checks, and metric glossary endpoints.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config.settings import get_settings
from src.config.groq_keys import GroqKeyPool
from src.vector.pinecone_client import PineconeClient
from src.vector.schema_store import SchemaStore, ExamplesStore
from src.warehouse.connector import SnowflakeConnector
from src.connectors.confluence_client import ConfluenceClient
from src.connectors.salesforce_connector import SalesforceConnector
from src.clarification.metric_resolver import get_all_metrics_for_glossary
from src.graph import build_graph

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Global state ─────────────────────────────────────────
_graph = None
_groq_pool = None
_snowflake = None
_pinecone = None
_confluence_client = None
_salesforce = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all clients at startup, clean up at shutdown."""
    global _graph, _groq_pool, _snowflake, _pinecone, _confluence_client, _salesforce
    
    settings = get_settings()
    logger.info("Starting OmniData backend...")
    
    # Initialize clients
    _groq_pool = GroqKeyPool(settings.groq_keys)
    logger.info(f"Groq pool: {_groq_pool.key_count} keys")
    
    _pinecone = PineconeClient(settings.pinecone_api_key)
    
    _snowflake = SnowflakeConnector(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
    )
    
    # Build vector stores
    schema_store = SchemaStore(_pinecone, settings.pinecone_hybrid_index)
    examples_store = ExamplesStore(_pinecone, settings.pinecone_hybrid_index)
    
    # Initialize Confluence client (live or demo mode)
    _confluence_client = ConfluenceClient(
        base_url=settings.confluence_base_url,
        email=settings.confluence_user_email,
        api_token=settings.confluence_api_token,
        default_space=settings.confluence_default_space,
    )
    
    # Initialize Salesforce connector (live CRM connection)
    _salesforce = SalesforceConnector(
        username=settings.salesforce_username,
        password=settings.salesforce_password,
        security_token=settings.salesforce_security_token,
        instance_url=settings.salesforce_instance_url,
    )
    try:
        sf_connected = _salesforce.connect()
        logger.info(f"Salesforce: {'connected' if sf_connected else 'offline (vector fallback)'}")
    except Exception as e:
        logger.warning(f"Salesforce connection failed: {e} — using vector fallback")
    
    # Build LangGraph pipeline
    _graph = build_graph(
        groq_pool=_groq_pool,
        schema_store=schema_store,
        examples_store=examples_store,
        snowflake_connector=_snowflake,
        pinecone_client=_pinecone,
        dense_index=settings.pinecone_dense_index,
        tavily_api_key=settings.tavily_api_key,
        salesforce_connector=_salesforce,
    )
    
    logger.info("OmniData backend ready!")
    
    yield
    
    # Cleanup
    if _snowflake:
        _snowflake.close()
    logger.info("OmniData backend shutdown complete")


# ── FastAPI App ──────────────────────────────────────────
app = FastAPI(
    title="OmniData API",
    description="Multi-agent AI system for enterprise data access",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──────────────────────────────

class QueryRequest(BaseModel):
    query: str
    clarification_response: Optional[str] = None


class ChartPanel(BaseModel):
    """A single chart panel — used when the pipeline produces multiple charts."""
    title: str = ""
    chart_type: Optional[str] = None
    data: list = []
    columns: list = []
    sql: Optional[str] = None
    row_count: int = 0
    confidence_score: float = 0.0
    confidence_tier: str = "red"


class QueryResponse(BaseModel):
    response: str
    sources: list[dict] = []
    sql: Optional[str] = None
    chart_type: Optional[str] = None
    chart_data: Optional[list] = None
    charts: list[ChartPanel] = []       # Multiple charts for complex queries
    rag_documents: list[dict] = []      # Documents from Confluence/RAG branch
    salesforce_records: list[dict] = [] # CRM records from Salesforce branch
    web_results: list[dict] = []        # External web search results from Tavily
    jargon_substitutions: list[dict] = []  # Language audit: what jargon was rewritten
    confidence_score: Optional[float] = None
    confidence_tier: Optional[str] = None
    temporal_note: Optional[str] = None
    clarification_needed: bool = False
    clarification_options: list[dict] = []
    processing_time_ms: int = 0


class HealthResponse(BaseModel):
    status: str
    services: dict


# ── Endpoints ────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Main query endpoint — runs the full LangGraph pipeline."""
    start = time.time()
    
    try:
        # Build initial state
        initial_state = {
            "original_query": request.query,
        }
        
        # If this is a clarification response, modify the query
        if request.clarification_response:
            initial_state["original_query"] = (
                f"{request.query} (specifically: {request.clarification_response})"
            )
        
        # Run the graph
        result = await _graph.ainvoke(initial_state)
        
        processing_time = int((time.time() - start) * 1000)
        
        # Check for clarification needed
        if result.get("clarification_needed"):
            return QueryResponse(
                response="I need a bit more context to answer that precisely.",
                clarification_needed=True,
                clarification_options=result.get("clarification_options", []),
                processing_time_ms=processing_time,
            )
        
        # Build response
        sql_output = result.get("sql_output") or {}
        rag_output = result.get("rag_output") or {}
        sf_output = result.get("salesforce_output") or {}
        
        # Build chart panels from multi-chart output
        charts_raw = sql_output.get("charts", [])
        chart_panels = [
            ChartPanel(
                title=c.get("title", ""),
                chart_type=c.get("chart_type"),
                data=c.get("data", [])[:100],
                columns=c.get("columns", []),
                sql=c.get("sql"),
                row_count=c.get("row_count", 0),
                confidence_score=c.get("confidence_score", 0),
                confidence_tier=c.get("confidence_tier", "red"),
            )
            for c in charts_raw
        ]
        
        # Extract RAG documents for frontend display
        rag_docs = []
        if rag_output and not rag_output.get("error"):
            rag_meta = rag_output.get("metadata", {})
            rag_docs = rag_meta.get("documents", [])
        
        # Extract Salesforce CRM records for frontend display
        sf_records = []
        if sf_output and not sf_output.get("error"):
            sf_meta = sf_output.get("metadata", {})
            sf_records = sf_meta.get("crm_records", [])
        
        # Extract web results for frontend display
        web_output = result.get("web_output") or {}
        web_results = []
        if web_output and not web_output.get("error"):
            web_meta = web_output.get("metadata", {})
            web_results = web_meta.get("web_results", [])
        
        return QueryResponse(
            response=result.get("final_response", "No response generated."),
            sources=result.get("sources_used", []),
            sql=sql_output.get("sql"),
            chart_type=sql_output.get("chart_type"),
            chart_data=sql_output.get("rows", [])[:100],
            charts=chart_panels,
            rag_documents=rag_docs,
            salesforce_records=sf_records,
            web_results=web_results,
            jargon_substitutions=result.get("jargon_substitutions", []),
            confidence_score=result.get("confidence_score"),
            confidence_tier=result.get("confidence_tier"),
            temporal_note=result.get("temporal_note"),
            clarification_needed=False,
            clarification_options=[],
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        processing_time = int((time.time() - start) * 1000)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "processing_time_ms": processing_time,
            }
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check connectivity to all external services."""
    services = {}
    
    try:
        services["snowflake"] = "ok" if _snowflake and _snowflake.test_connection() else "disconnected"
    except Exception:
        services["snowflake"] = "error"
    
    try:
        settings = get_settings()
        services["pinecone_hybrid"] = "ok" if _pinecone and _pinecone.test_connection(settings.pinecone_hybrid_index) else "disconnected"
    except Exception:
        services["pinecone_hybrid"] = "error"
    
    try:
        settings = get_settings()
        services["pinecone_dense"] = "ok" if _pinecone and _pinecone.test_connection(settings.pinecone_dense_index) else "disconnected"
    except Exception:
        services["pinecone_dense"] = "error"
    
    try:
        if _groq_pool:
            client = _groq_pool.get_client()
            client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            services["groq"] = "ok"
        else:
            services["groq"] = "disconnected"
    except Exception:
        services["groq"] = "error"
    
    try:
        settings = get_settings()
        services["tavily"] = "ok" if settings.tavily_api_key else "not_configured"
    except Exception:
        services["tavily"] = "error"
    
    try:
        if _confluence_client:
            conn_ok = await _confluence_client.test_connection()
            services["confluence"] = f"ok ({_confluence_client.mode_label})" if conn_ok else "error"
        else:
            services["confluence"] = "not_initialized"
    except Exception:
        services["confluence"] = "error"
    
    try:
        if _salesforce and _salesforce.is_connected:
            services["salesforce"] = "ok"
        elif _salesforce:
            services["salesforce"] = "offline (vector fallback)"
        else:
            services["salesforce"] = "not_initialized"
    except Exception:
        services["salesforce"] = "error"
    
    all_ok = all(v.startswith("ok") for v in services.values())
    
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        services=services,
    )


@app.get("/metrics")
async def metrics_glossary():
    """Return the metric dictionary for the frontend Glossary component."""
    return get_all_metrics_for_glossary()


@app.get("/")
async def root():
    """Root endpoint — basic info."""
    return {
        "name": "OmniData API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.post("/confluence/sync")
async def confluence_sync():
    """
    Sync Confluence pages into the Pinecone vector store.
    
    Fetches pages from the Confluence instance (live or demo mode),
    chunks them, and upserts the embeddings into Pinecone for RAG retrieval.
    
    This endpoint enables real-time knowledge base updates without
    restarting the backend.
    """
    import time as _time
    from pinecone import Pinecone
    from seed.confluence_seed import chunk_document
    
    if not _confluence_client:
        raise HTTPException(status_code=503, detail="Confluence client not initialized")
    
    settings = get_settings()
    
    try:
        # Step 1: Fetch pages from Confluence
        pages = await _confluence_client.get_space_pages()
        if not pages:
            raise HTTPException(status_code=404, detail="No pages found in Confluence")
        
        # Step 2: Chunk all pages
        all_chunks = []
        for page in pages:
            chunks = chunk_document(page)
            all_chunks.extend(chunks)
        
        # Step 3: Upsert into Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_dense_index)
        
        BATCH_SIZE = 10
        for i in range(0, len(all_chunks), BATCH_SIZE):
            batch = all_chunks[i:i + BATCH_SIZE]
            index.upsert_records(namespace="confluence_store", records=batch)
            _time.sleep(0.5)  # Rate limit
        
        logger.info(f"Confluence sync complete: {len(pages)} pages, {len(all_chunks)} chunks")
        
        return {
            "status": "success",
            "pages_synced": len(pages),
            "chunks_created": len(all_chunks),
            "mode": _confluence_client.mode_label,
            "index": settings.pinecone_dense_index,
            "namespace": "confluence_store",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Confluence sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.get("/confluence/status")
async def confluence_status():
    """
    Return the current Confluence integration status.
    
    Shows whether the client is in live or demo mode,
    and what space is configured.
    """
    if not _confluence_client:
        return {"status": "not_initialized"}
    
    connected = await _confluence_client.test_connection()
    
    return {
        "status": "connected" if connected else "disconnected",
        "mode": _confluence_client.mode_label,
        "space": _confluence_client.default_space,
        "base_url": _confluence_client.base_url or "(demo — local data)",
    }


# ── Jargon Management Endpoints ──────────────────────────────

@app.get("/jargon")
async def list_jargon():
    """
    Return the complete jargon registry.
    
    Merges auto-generated terms from the Metric Dictionary with
    user-defined overrides. Each entry is marked as editable or not.
    """
    from src.validation.semantic_validator import get_all_jargon
    return {"terms": get_all_jargon()}


class JargonEntry(BaseModel):
    term: str
    replacement: str
    category: str = "custom"


@app.post("/jargon")
async def add_jargon(entry: JargonEntry):
    """
    Add a user-defined jargon term.
    
    The term will be detected and rewritten in all future responses
    that pass through the Semantic Validator.
    """
    from src.validation.semantic_validator import add_jargon_override
    add_jargon_override(entry.term, entry.replacement, entry.category)
    return {
        "status": "added",
        "term": entry.term,
        "replacement": entry.replacement,
    }


@app.delete("/jargon/{term}")
async def delete_jargon(term: str):
    """
    Remove a user-defined jargon term.
    
    Only user-defined overrides can be removed. Metric Dictionary
    terms are read-only.
    """
    from src.validation.semantic_validator import remove_jargon_override
    removed = remove_jargon_override(term)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found in overrides")
    return {"status": "removed", "term": term}
