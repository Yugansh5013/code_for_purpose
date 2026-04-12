"""
OmniData — Branch 1: Snowflake SQL Pipeline

Unified pipeline that auto-detects query complexity:
- Simple queries → 1 SQL, 1 chart
- Complex queries → decomposes into N focused sub-queries, N charts

No separate "analyze" mode. The pipeline decides what the question needs.
"""

import json
import logging
from typing import Any

from src.state import GraphState, SQLBranchOutput
from src.vector.schema_store import SchemaStore, ExamplesStore
from src.validation.sql_validator import validate_sql
from src.validation.confidence_scorer import calculate_confidence

logger = logging.getLogger(__name__)

SQL_GENERATION_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2

SQL_SYSTEM_PROMPT = """You are an expert Snowflake SQL query generator for Aura Retail's data warehouse.

## Database: OMNIDATA_DB
## Available Tables and Schemas:
{schema_context}

## Rules:
1. Generate ONLY a valid Snowflake SQL SELECT query — no explanations, no markdown.
2. Use fully qualified table names: OMNIDATA_DB.SCHEMA.TABLE
3. Always include appropriate WHERE clauses for date filtering when dates are mentioned.
4. Use DATE_TRUNC('month', date_col) for monthly aggregations.
5. Always add ORDER BY for sorted results.
6. Use ROUND() for decimal values.
7. For percentage calculations, multiply by 100.
8. JOIN PRODUCT_CATALOGUE on PRODUCT_SKU when product names are needed.
9. CHURN_RATE is stored as a decimal (0.05 = 5%), multiply by 100 for display.
10. RETURN_RATE is stored as a decimal, multiply by 100 for display.
11. Output ONLY the SQL query, nothing else. No ```sql``` markers.

## Relevant Examples:
{examples_context}

## Date Context:
{date_context}
"""

COMPLEXITY_PROMPT = """Analyze this business question for Aura Retail's data warehouse.

Available tables:
- AURA_SALES (sales data: date, region, channel, product, revenue, units)
- PRODUCT_CATALOGUE (product info: SKU, name, category, price)
- RETURN_EVENTS (returns: date, product, region, reason, rate)
- CUSTOMER_METRICS (monthly: region, segment, churn, repeat purchase)

Question: "{query}"

Is this question SIMPLE (answerable by a single SQL query on one or two dimensions) 
or COMPLEX (needs multiple queries across different dimensions/tables to fully answer)?

If COMPLEX, break it into 2-3 focused sub-questions. Each must be answerable by ONE SQL SELECT.
Don't force sub-questions if they aren't needed — only decompose if the question genuinely
spans multiple unrelated dimensions.

Respond in JSON:
{{
  "complexity": "simple" | "complex",
  "reasoning": "one line explaining why",
  "sub_queries": [
    {{"question": "...", "chart_hint": "bar|line|number"}}
  ]
}}

For SIMPLE questions, sub_queries should have exactly 1 item (the original question).
For COMPLEX questions, sub_queries should have 2-3 items (never more than 3).
Output ONLY valid JSON."""


async def branch_sql_node(
    state: GraphState,
    groq_pool: Any,
    schema_store: SchemaStore,
    examples_store: ExamplesStore,
    snowflake_connector: Any,
) -> dict:
    """
    Branch 1: Unified SQL pipeline with automatic complexity detection.
    
    Simple query → 1 SQL → 1 chart
    Complex query → 2-3 SQL → multiple charts
    """
    query = state.get("resolved_query", state["original_query"])
    date_context = ""
    
    if state.get("resolved_dates"):
        dates = state["resolved_dates"]
        date_context = f"Date range: {dates['start']} to {dates['end']}"
    if state.get("temporal_note"):
        date_context += f"\n{state['temporal_note']}"
    
    try:
        # ── Step 1: Schema RAG ───────────────────────────
        schemas = schema_store.get_relevant_schemas(query, top_k=4)
        schema_context = "\n\n".join([
            f"### {s['table_name']} ({s['schema']})\n{s['description']}"
            for s in schemas
        ])
        pinecone_top_score = schemas[0]["relevance_score"] if schemas else 0.0
        
        # ── Step 2: Few-Shot RAG ─────────────────────────
        examples = examples_store.get_relevant_examples(query, top_k=3)
        examples_context = "\n\n".join([
            f"Example:\n{e['example_text']}" for e in examples
        ])
        
        # ── Step 3: Detect complexity ────────────────────
        sub_queries = await _detect_complexity(groq_pool, query)
        logger.info(f"Complexity: {len(sub_queries)} sub-queries for '{query[:50]}...'")
        
        # ── Step 4: Generate + Execute each sub-query ────
        results = []
        
        for sq in sub_queries:
            result = await _run_single_query(
                groq_pool=groq_pool,
                question=sq["question"],
                chart_hint=sq.get("chart_hint", "bar"),
                schema_context=schema_context,
                examples_context=examples_context,
                date_context=date_context,
                pinecone_top_score=pinecone_top_score,
                snowflake_connector=snowflake_connector,
            )
            results.append(result)
        
        # ── Fallback: if ALL sub-queries failed, retry original as simple ──
        all_failed = all(r.get("error") for r in results)
        if all_failed and len(sub_queries) > 1:
            logger.warning("All sub-queries failed — retrying original query as simple")
            fallback = await _run_single_query(
                groq_pool=groq_pool,
                question=query,
                chart_hint="bar",
                schema_context=schema_context,
                examples_context=examples_context,
                date_context=date_context,
                pinecone_top_score=pinecone_top_score,
                snowflake_connector=snowflake_connector,
            )
            results = [fallback]
        
        # ── Build output ─────────────────────────────────
        # Primary result = first successful result
        primary = next((r for r in results if not r.get("error")), results[0])
        
        # Collect all charts (for multi-chart rendering)
        charts = []
        for r in results:
            if r.get("rows") and not r.get("error"):
                charts.append({
                    "title": r.get("title", ""),
                    "chart_type": r["chart_type"],
                    "data": r["rows"][:100],
                    "columns": r["columns"],
                    "sql": r["sql"],
                    "row_count": r["row_count"],
                    "confidence_score": r["confidence_score"],
                    "confidence_tier": r["confidence_tier"],
                })
        
        # Average confidence across all results
        valid_scores = [r["confidence_score"] for r in results if r["confidence_score"] > 0]
        avg_confidence = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        avg_tier = "green" if avg_confidence >= 0.8 else "amber" if avg_confidence >= 0.5 else "red"
        
        output: SQLBranchOutput = {
            "data": primary.get("rows", []),
            "raw_query": primary.get("sql", ""),
            "source": "snowflake",
            "source_label": "Snowflake Data Warehouse",
            "sql": primary.get("sql", ""),
            "columns": primary.get("columns", []),
            "rows": primary.get("rows", []),
            "row_count": primary.get("row_count", 0),
            "chart_type": primary.get("chart_type"),
            "confidence_score": avg_confidence,
            "confidence_tier": avg_tier,
            "retry_count": 0,
            "pinecone_top_score": pinecone_top_score,
            "charts": charts,  # Multiple charts for complex queries
            "error": primary.get("error"),
            "metadata": {
                "schemas_used": [s["table_name"] for s in schemas],
                "examples_matched": len(examples),
                "sub_query_count": len(sub_queries),
                "charts_rendered": len(charts),
            },
        }
        
        logger.info(f"SQL Branch: {len(charts)} chart(s), avg confidence={avg_tier}")
        
        return {
            "sql_output": output,
            "confidence_score": avg_confidence,
            "confidence_tier": avg_tier,
        }
        
    except Exception as e:
        logger.error(f"SQL branch error: {e}", exc_info=True)
        return _error_output(str(e))


async def _detect_complexity(groq_pool: Any, query: str) -> list[dict]:
    """
    Detect if a query is simple or complex.
    Simple → return [original query]
    Complex → return 2-3 focused sub-queries
    """
    try:
        client = groq_pool.get_client()
        response = client.chat.completions.create(
            model=SQL_GENERATION_MODEL,
            messages=[
                {"role": "system", "content": COMPLEXITY_PROMPT.format(query=query)},
                {"role": "user", "content": "Analyze the complexity."},
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        
        sub_queries = parsed.get("sub_queries", [])
        complexity = parsed.get("complexity", "simple")
        
        if not sub_queries:
            return [{"question": query, "chart_hint": "bar"}]
        
        # Cap at 3
        sub_queries = sub_queries[:3]
        
        logger.info(f"Complexity={complexity}: {parsed.get('reasoning', '')}")
        return sub_queries
        
    except Exception as e:
        logger.warning(f"Complexity detection failed, treating as simple: {e}")
        return [{"question": query, "chart_hint": "bar"}]


async def _run_single_query(
    groq_pool: Any,
    question: str,
    chart_hint: str,
    schema_context: str,
    examples_context: str,
    date_context: str,
    pinecone_top_score: float,
    snowflake_connector: Any,
) -> dict:
    """Run a single SQL generation + execution cycle."""
    result = {
        "title": question,
        "sql": "",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "chart_type": chart_hint,
        "confidence_score": 0.0,
        "confidence_tier": "red",
        "error": None,
    }
    
    try:
        # Generate SQL with retry
        sql = None
        retry_count = 0
        validation_errors = []
        
        for attempt in range(MAX_RETRIES + 1):
            generated_sql = await _generate_sql(
                groq_pool, question, schema_context, examples_context, date_context,
                previous_errors=validation_errors if attempt > 0 else None,
            )
            
            is_valid, cleaned_sql, errors = validate_sql(generated_sql)
            
            if is_valid:
                sql = cleaned_sql
                retry_count = attempt
                break
            else:
                validation_errors = errors
                logger.warning(f"SQL validation failed (attempt {attempt + 1}): {errors}")
                retry_count = attempt + 1
        
        if sql is None:
            result["error"] = f"SQL validation failed: {validation_errors}"
            return result
        
        result["sql"] = sql
        
        # Execute
        try:
            rows = snowflake_connector.execute_query(sql)
        except Exception as e:
            result["error"] = f"SQL execution failed: {str(e)[:200]}"
            return result
        
        result["columns"] = list(rows[0].keys()) if rows else []
        result["rows"] = rows
        result["row_count"] = len(rows)
        
        # Chart type
        result["chart_type"] = _detect_chart_type(result["columns"], rows, sql, chart_hint)
        
        # Confidence
        is_aggregate = any(kw in sql.upper() for kw in ["SUM(", "COUNT(", "AVG(", "GROUP BY"])
        confidence = calculate_confidence(
            pinecone_top_score=pinecone_top_score,
            retry_count=retry_count,
            row_count=len(rows),
            is_aggregate=is_aggregate,
        )
        result["confidence_score"] = confidence["score"]
        result["confidence_tier"] = confidence["tier"]
        
    except Exception as e:
        result["error"] = str(e)[:200]
    
    return result


async def _generate_sql(
    groq_pool: Any,
    query: str,
    schema_context: str,
    examples_context: str,
    date_context: str,
    previous_errors: list[str] | None = None,
) -> str:
    """Generate SQL via Groq."""
    system = SQL_SYSTEM_PROMPT.format(
        schema_context=schema_context,
        examples_context=examples_context,
        date_context=date_context or "No specific date range mentioned.",
    )
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]
    
    if previous_errors:
        messages.append({
            "role": "user",
            "content": f"The previous SQL had these errors: {previous_errors}. Please fix and regenerate."
        })
    
    client = groq_pool.get_client()
    response = client.chat.completions.create(
        model=SQL_GENERATION_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=1000,
    )
    
    sql = response.choices[0].message.content.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    if "<think>" in sql:
        parts = sql.split("</think>")
        sql = parts[-1].strip() if len(parts) > 1 else sql
    
    logger.info(f"Generated SQL: {sql[:100]}...")
    return sql


def _detect_chart_type(columns: list[str], rows: list[dict], sql: str, hint: str = "bar") -> str:
    """Detect the best visualization type based on result shape and column semantics."""
    if not rows:
        return "table"
    
    row_count = len(rows)
    col_count = len(columns)
    cols_upper = [c.upper() for c in columns]
    sql_upper = sql.upper()
    
    # ── Single value → number card ──
    if row_count == 1 and col_count == 1:
        return "number"
    if row_count == 1 and col_count <= 3:
        return "number"
    
    # ── Time-series detection (column name heuristics + SQL) ──
    time_col_keywords = ["MONTH", "DATE", "PERIOD", "QUARTER", "YEAR", "WEEK", "DAY"]
    has_time_col = any(
        any(kw in col for kw in time_col_keywords)
        for col in cols_upper
    )
    has_time_sql = any(kw in sql_upper for kw in ["DATE_TRUNC", "METRIC_MONTH", "ORDER BY"])
    
    # Also detect date-like string values in first column
    first_val = str(rows[0].get(columns[0], ""))
    looks_like_date = bool(
        len(first_val) >= 7 and first_val[:4].isdigit() and first_val[4] == '-'
    ) if first_val else False
    
    if (has_time_col or looks_like_date) and row_count > 2:
        return "line"
    if has_time_sql and row_count > 2:
        return "line"
    
    # ── Percentage/rate columns → line chart (trends) ──
    rate_keywords = ["RATE", "PERCENT", "PCT", "RATIO"]
    has_rate_col = any(
        any(kw in col for kw in rate_keywords)
        for col in cols_upper
    )
    if has_rate_col and row_count > 3:
        return "line"
    
    # ── Small categorical set → doughnut if hint says so or ≤5 items ──
    has_numeric = any(isinstance(rows[0].get(col), (int, float)) for col in columns)
    if has_numeric and row_count <= 5 and hint == "doughnut":
        return "doughnut"
    
    # ── Categorical with numeric → bar chart ──
    if has_numeric and row_count <= 30:
        return hint if hint in ("bar", "line", "doughnut") else "bar"
    
    return "table"


def _error_output(error_msg: str) -> dict:
    """Build error output for the SQL branch."""
    return {
        "sql_output": {
            "data": [],
            "raw_query": "",
            "source": "snowflake",
            "source_label": "Snowflake Data Warehouse",
            "error": error_msg,
            "sql": "",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "chart_type": None,
            "charts": [],
            "confidence_score": 0.0,
            "confidence_tier": "red",
            "retry_count": 0,
            "pinecone_top_score": 0.0,
            "metadata": {},
        },
        "confidence_score": 0.0,
        "confidence_tier": "red",
    }
