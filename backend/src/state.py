"""
OmniData — Graph State Definition

Defines the typed state that flows through the LangGraph pipeline.
ALL branch outputs are defined here from Day 1, even if only Branch 1
(Snowflake SQL) is active in Phase 1. This ensures seamless integration
of Branches 2 and 3 later.
"""

from typing import TypedDict, Optional, List, Any


class BranchOutput(TypedDict, total=False):
    """Standard output format for any branch."""
    data: Any                    # Query results (rows, documents, etc.)
    raw_query: str               # The generated SQL/SOQL/search query
    source: str                  # "snowflake", "confluence", "salesforce", "tavily"
    source_label: str            # Human-readable: "Snowflake Data Warehouse"
    error: Optional[str]         # Error message if branch failed
    metadata: dict               # Branch-specific metadata


class SQLBranchOutput(BranchOutput, total=False):
    """Extended output for SQL branch with visualization metadata."""
    sql: str                     # Generated SQL query
    columns: List[str]           # Column names from result
    rows: List[dict]             # Result rows as dicts
    row_count: int               # Number of rows returned
    chart_type: Optional[str]    # "bar", "line", "table", "number", None
    confidence_score: float      # 0.0 to 1.0
    confidence_tier: str         # "green", "amber", "red"
    retry_count: int             # Number of SQL generation retries
    pinecone_top_score: float    # Top-1 RAG relevance score
    # E2B Sandbox visualization outputs
    e2b_plotly_json: Optional[str]   # Plotly fig.to_json() string (interactive chart)
    e2b_chart_image: Optional[str]   # Base64 PNG fallback image
    e2b_code: Optional[str]          # Generated Python code (for transparency)


class GraphState(TypedDict, total=False):
    """
    Full state flowing through the LangGraph pipeline.
    
    Fields are grouped by the node that produces them.
    Optional fields default to None when not set.
    """

    # ── Input ──────────────────────────────────────────────
    original_query: str
    conversation_history: List[dict]

    # ── Security Context (RBAC) ───────────────────────────
    user_context: Optional[dict]  # {"role": "north_manager", "region_filter": "North", "label": "North Region Manager"}

    # ── Node 0: Intent Router ─────────────────────────────
    branches: List[str]           # ["sql"], ["sql", "rag_confluence"], etc.
    sql_likely: bool
    rag_present: bool
    rag_sources: List[str]        # ["confluence", "documents"]
    web_needed: bool
    salesforce_needed: bool

    # ── Node 1: Clarification ─────────────────────────────
    resolved_query: str
    resolved_dates: dict          # {"start": "2026-01-01", "end": "2026-03-31"}
    resolved_metrics: List[dict]
    clarification_needed: bool
    clarification_options: List[dict]  # [{"label": "Total Sales", "value": "revenue"}]
    temporal_note: str            # "Q1 2026 resolved to Jan 1 – Mar 31, 2026"

    # ── Branch Outputs ────────────────────────────────────
    # Phase 1: Only sql_output is populated
    sql_output: Optional[SQLBranchOutput]

    # Phase 2: These will be populated when branches are added
    rag_output: Optional[BranchOutput]
    salesforce_output: Optional[BranchOutput]

    # Phase 3
    web_output: Optional[BranchOutput]

    # ── Node 2: Synthesis ─────────────────────────────────
    draft_response: str
    suggested_followups: List[str]
    sources_used: List[dict]      # [{"source": "snowflake", "label": "...", "confidence": 0.9}]
    reasoning_trace: Optional[str]  # DeepSeek-R1 <think> block — raw model reasoning

    # ── Node 3: Semantic Validator (Phase 2+) ─────────────
    final_response: str
    jargon_substitutions: List[dict]  # [{"original": "CHURN_RATE", "replaced": "Churn Rate"}]

    # ── Aggregate ─────────────────────────────────────────
    confidence_score: float       # Overall confidence (0.0 to 1.0)
    confidence_tier: str          # "green" (≥0.8), "amber" (0.5–0.79), "red" (<0.5)
    error: Optional[str]          # Top-level error if pipeline fails
