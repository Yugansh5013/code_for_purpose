"""
OmniData — SQL Validator

Validates generated SQL queries using sqlglot.
Enforces read-only access, LIMIT requirements, and table name verification.
"""

import logging
from typing import Optional

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

# Known tables in OMNIDATA_DB
VALID_TABLES = {
    "AURA_SALES", "PRODUCT_CATALOGUE", "RETURN_EVENTS", "CUSTOMER_METRICS",
    # Also allow fully qualified names
    "OMNIDATA_DB.SALES.AURA_SALES",
    "OMNIDATA_DB.PRODUCTS.PRODUCT_CATALOGUE",
    "OMNIDATA_DB.RETURNS.RETURN_EVENTS",
    "OMNIDATA_DB.CUSTOMERS.CUSTOMER_METRICS",
}

# Dangerous SQL keywords/operations
FORBIDDEN_OPERATIONS = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "MERGE", "GRANT", "REVOKE"}

MAX_LIMIT = 500
DEFAULT_LIMIT = 100


def validate_sql(sql: str) -> tuple[bool, str, list[str]]:
    """
    Validate a generated SQL query.
    
    Args:
        sql: The SQL string to validate
    
    Returns:
        Tuple of (is_valid, cleaned_sql, errors)
        - is_valid: Whether the SQL passes all checks
        - cleaned_sql: The SQL with auto-fixes applied (e.g., LIMIT added)
        - errors: List of validation error messages
    """
    errors = []
    cleaned_sql = sql.strip().rstrip(";")
    
    # ── Check 1: Not empty ───────────────────────────────
    if not cleaned_sql:
        return False, "", ["Empty SQL query"]
    
    # ── Check 2: No forbidden DML/DDL operations ─────────
    sql_upper = cleaned_sql.upper()
    for op in FORBIDDEN_OPERATIONS:
        # Check if the operation appears as a standalone keyword
        if f" {op} " in f" {sql_upper} " or sql_upper.startswith(f"{op} "):
            errors.append(f"Forbidden operation: {op} — only SELECT queries are allowed")
            return False, cleaned_sql, errors
    
    # ── Check 3: Must be a SELECT statement ──────────────
    if not sql_upper.lstrip().startswith("SELECT"):
        errors.append("Query must be a SELECT statement")
        return False, cleaned_sql, errors
    
    # ── Check 4: Parse with sqlglot ──────────────────────
    try:
        parsed = sqlglot.parse(cleaned_sql, dialect="snowflake")
        if not parsed:
            errors.append("Failed to parse SQL")
            return False, cleaned_sql, errors
        
        tree = parsed[0]
    except sqlglot.errors.ParseError as e:
        errors.append(f"SQL parse error: {str(e)[:200]}")
        return False, cleaned_sql, errors
    
    # ── Check 5: Verify table names ──────────────────────
    tables_used = set()
    for table in tree.find_all(exp.Table):
        table_name = table.name.upper()
        full_name = str(table).upper().replace('"', '')
        tables_used.add(table_name)
        tables_used.add(full_name)
    
    # Check if at least one known table is referenced
    if tables_used and not any(t in VALID_TABLES for t in tables_used):
        errors.append(f"Unknown table(s): {tables_used}. Known tables: {', '.join(sorted(VALID_TABLES))}")
    
    # ── Check 6: LIMIT enforcement ───────────────────────
    has_limit = tree.find(exp.Limit) is not None
    has_aggregate = _has_aggregate(tree)
    
    if not has_limit and not has_aggregate:
        # Auto-add LIMIT for non-aggregate queries
        cleaned_sql = f"{cleaned_sql} LIMIT {DEFAULT_LIMIT}"
        logger.info(f"Auto-added LIMIT {DEFAULT_LIMIT} to non-aggregate query")
    elif has_limit:
        # Verify LIMIT isn't too high
        limit_node = tree.find(exp.Limit)
        if limit_node and limit_node.expression:
            try:
                limit_val = int(str(limit_node.expression))
                if limit_val > MAX_LIMIT:
                    cleaned_sql = cleaned_sql.replace(str(limit_val), str(MAX_LIMIT))
                    logger.info(f"Reduced LIMIT from {limit_val} to {MAX_LIMIT}")
            except (ValueError, TypeError):
                pass
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("SQL validation passed")
    else:
        logger.warning(f"SQL validation failed: {errors}")
    
    return is_valid, cleaned_sql, errors


def _has_aggregate(tree) -> bool:
    """Check if the query contains aggregate functions (SUM, COUNT, AVG, etc.)."""
    aggregate_funcs = {"SUM", "COUNT", "AVG", "MIN", "MAX"}
    for func in tree.find_all(exp.Func):
        if func.key.upper() in aggregate_funcs or (hasattr(func, 'name') and func.name and func.name.upper() in aggregate_funcs):
            return True
    # Also check for GROUP BY as a signal
    if tree.find(exp.Group):
        return True
    return False


# ── Row-Level Security (RLS) Validator ────────────────────

# Tables that contain a GEO_TERRITORY column and require RLS filtering
RLS_TABLES = {"AURA_SALES", "RETURN_EVENTS", "CUSTOMER_METRICS"}


def validate_rls(sql: str, user_context: dict) -> tuple[bool, list[str]]:
    """
    Validate that a SQL query respects Row-Level Security constraints.
    
    For restricted users, checks that every query against RLS_TABLES
    includes a WHERE GEO_TERRITORY = '{region}' filter.
    
    Args:
        sql: The SQL string to validate
        user_context: The RBAC context dict with 'region_filter' key
    
    Returns:
        Tuple of (is_valid, errors)
    """
    region_filter = user_context.get("region_filter")
    if not region_filter:
        return True, []  # CEO / unrestricted — no RLS needed
    
    errors = []
    sql_upper = sql.upper()
    
    # Quick check: does the SQL reference any RLS table?
    tables_referenced = [t for t in RLS_TABLES if t in sql_upper]
    
    if not tables_referenced:
        return True, []  # Query doesn't touch restricted tables
    
    # Check for the presence of the GEO_TERRITORY filter
    # Accept variations: GEO_TERRITORY = 'North', "GEO_TERRITORY" = 'North', etc.
    region_upper = region_filter.upper()
    has_filter = (
        f"GEO_TERRITORY = '{region_filter}'" in sql
        or f"GEO_TERRITORY = '{region_upper}'" in sql_upper
        or f'"GEO_TERRITORY" = \'{region_filter}\'' in sql
        or f"GEO_TERRITORY='{region_filter}'" in sql
    )
    
    if not has_filter:
        errors.append(
            f"RLS VIOLATION: Query accesses {', '.join(tables_referenced)} "
            f"but is missing mandatory filter: WHERE GEO_TERRITORY = '{region_filter}'. "
            f"The current user ({user_context.get('label', 'restricted')}) can only access "
            f"{region_filter} region data. You MUST add GEO_TERRITORY = '{region_filter}' "
            f"to the WHERE clause."
        )
        logger.warning(f"RLS enforcement triggered: missing GEO_TERRITORY filter for {region_filter}")
        return False, errors
    
    logger.info(f"RLS validation passed: GEO_TERRITORY = '{region_filter}' present")
    return True, []

