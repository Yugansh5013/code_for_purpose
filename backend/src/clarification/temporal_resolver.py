"""
OmniData — Temporal Resolver

Resolves natural language date/time references to concrete date ranges.
Handles phrases like "last quarter", "this month", "YTD", "recent", etc.

Also includes a guardrail for out-of-range queries — Aura Retail data
covers October 2025 to March 2026.
"""

import re
import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Aura Retail data boundaries
DATA_START = date(2025, 10, 1)
DATA_END = date(2026, 3, 31)


def resolve_temporal_references(query: str, reference_date: Optional[date] = None) -> dict:
    """
    Resolve temporal phrases in a user query to concrete date ranges.
    
    Args:
        query: The user's natural language query
        reference_date: The "today" date for resolution (defaults to DATA_END
                       since our data is historical)
    
    Returns:
        Dict with:
            - resolved_dates: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} or None
            - temporal_note: Human-readable note about what was resolved
            - date_clause: SQL WHERE clause fragment
            - out_of_range: Whether the resolved dates fall outside our data
            - modified_query: Query with temporal phrases replaced
    """
    if reference_date is None:
        reference_date = DATA_END  # Use end of data range as reference
    
    query_lower = query.lower()
    result = {
        "resolved_dates": None,
        "temporal_note": None,
        "date_clause": None,
        "out_of_range": False,
        "modified_query": query,
    }
    
    # ── Pattern matching (order matters — most specific first) ──
    
    # "Q1 2026", "Q2 2025", etc.
    quarter_match = re.search(r'q([1-4])\s*(\d{4})', query_lower)
    if quarter_match:
        q = int(quarter_match.group(1))
        year = int(quarter_match.group(2))
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        start = date(year, start_month, 1)
        end = _last_day_of_month(year, end_month)
        return _build_result(start, end, f"Q{q} {year} resolved to {start} – {end}", query)
    
    # "last quarter"
    if "last quarter" in query_lower:
        current_q = (reference_date.month - 1) // 3 + 1
        if current_q == 1:
            start = date(reference_date.year - 1, 10, 1)
            end = date(reference_date.year - 1, 12, 31)
        else:
            start_month = (current_q - 2) * 3 + 1
            end_month = start_month + 2
            start = date(reference_date.year, start_month, 1)
            end = _last_day_of_month(reference_date.year, end_month)
        return _build_result(start, end, f"'last quarter' resolved to {start} – {end}", query)
    
    # "this quarter"
    if "this quarter" in query_lower:
        current_q = (reference_date.month - 1) // 3 + 1
        start_month = (current_q - 1) * 3 + 1
        start = date(reference_date.year, start_month, 1)
        end = reference_date
        return _build_result(start, end, f"'this quarter' resolved to {start} – {end}", query)
    
    # "last month"
    if "last month" in query_lower:
        first_of_current = reference_date.replace(day=1)
        end = first_of_current - timedelta(days=1)
        start = end.replace(day=1)
        return _build_result(start, end, f"'last month' resolved to {start} – {end}", query)
    
    # "this month"
    if "this month" in query_lower:
        start = reference_date.replace(day=1)
        end = reference_date
        return _build_result(start, end, f"'this month' resolved to {start} – {end}", query)
    
    # "YTD" or "year to date"
    if "ytd" in query_lower or "year to date" in query_lower:
        start = date(reference_date.year, 1, 1)
        end = reference_date
        return _build_result(start, end, f"'YTD' resolved to {start} – {end}", query)
    
    # "this year"
    if "this year" in query_lower:
        start = date(reference_date.year, 1, 1)
        end = reference_date
        return _build_result(start, end, f"'this year' resolved to {start} – {end}", query)
    
    # "last year"
    if "last year" in query_lower:
        start = date(reference_date.year - 1, 1, 1)
        end = date(reference_date.year - 1, 12, 31)
        return _build_result(start, end, f"'last year' resolved to {start} – {end}", query)
    
    # "recent" / "recently"
    if "recent" in query_lower:
        start = reference_date - timedelta(days=30)
        end = reference_date
        return _build_result(start, end, f"'recent' resolved to last 30 days: {start} – {end}", query)
    
    # Specific month + year: "January 2026", "Feb 2026"
    month_match = re.search(
        r'(january|february|march|april|may|june|july|august|september|october|november|december|'
        r'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s*(\d{4})',
        query_lower
    )
    if month_match:
        month_name = month_match.group(1)
        year = int(month_match.group(2))
        month_num = _month_name_to_num(month_name)
        if month_num:
            start = date(year, month_num, 1)
            end = _last_day_of_month(year, month_num)
            return _build_result(start, end, f"'{month_name.title()} {year}' resolved to {start} – {end}", query)
    
    # No temporal reference found
    return result


def _build_result(start: date, end: date, note: str, original_query: str) -> dict:
    """Build a standardized result dict with out-of-range detection."""
    out_of_range = start > DATA_END or end < DATA_START
    
    # Clamp to data range if partially overlapping
    clamped_start = max(start, DATA_START)
    clamped_end = min(end, DATA_END)
    
    if out_of_range:
        note += f" ⚠️ This is outside our data range ({DATA_START} to {DATA_END}). Showing nearest available data."
        clamped_start = DATA_START
        clamped_end = DATA_END
    
    date_clause = f"SALE_DATE >= '{clamped_start}' AND SALE_DATE <= '{clamped_end}'"
    
    return {
        "resolved_dates": {"start": str(clamped_start), "end": str(clamped_end)},
        "temporal_note": note,
        "date_clause": date_clause,
        "out_of_range": out_of_range,
        "modified_query": original_query,
    }


def _last_day_of_month(year: int, month: int) -> date:
    """Get the last day of a given month."""
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _month_name_to_num(name: str) -> Optional[int]:
    """Convert month name or abbreviation to number."""
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2,
        "march": 3, "mar": 3, "april": 4, "apr": 4,
        "may": 5, "june": 6, "jun": 6,
        "july": 7, "jul": 7, "august": 8, "aug": 8,
        "september": 9, "sep": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12,
    }
    return months.get(name.lower())
