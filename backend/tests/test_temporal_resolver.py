"""
Tests for Temporal Resolver — verifies all date phrase → range mappings.
"""

import pytest
from datetime import date
from src.clarification.temporal_resolver import resolve_temporal_references, DATA_START, DATA_END


class TestQuarterResolution:
    """Test explicit quarter references like Q1 2026, Q4 2025."""

    def test_q1_2026(self):
        result = resolve_temporal_references("Total sales in Q1 2026")
        dates = result["resolved_dates"]
        assert dates["start"] == "2026-01-01"
        assert dates["end"] == "2026-03-31"

    def test_q4_2025(self):
        result = resolve_temporal_references("Revenue in Q4 2025")
        dates = result["resolved_dates"]
        assert dates["start"] == "2025-10-01"
        assert dates["end"] == "2025-12-31"

    def test_q2_2026_out_of_range(self):
        """Q2 2026 is after our data range — should be flagged."""
        result = resolve_temporal_references("Sales in Q2 2026")
        assert result["out_of_range"] is True
        # Dates should be clamped to data boundaries
        dates = result["resolved_dates"]
        assert dates["start"] == str(DATA_START)
        assert dates["end"] == str(DATA_END)

    def test_q3_2025_out_of_range(self):
        """Q3 2025 is before our data range — should be flagged."""
        result = resolve_temporal_references("Sales in Q3 2025")
        assert result["out_of_range"] is True


class TestRelativeResolution:
    """Test relative references like 'last month', 'this quarter'."""

    def test_last_quarter(self):
        """With reference date = 2026-03-31, last quarter = Q4 2025."""
        result = resolve_temporal_references("What happened last quarter?")
        dates = result["resolved_dates"]
        assert dates["start"] == "2025-10-01"
        assert dates["end"] == "2025-12-31"

    def test_this_quarter(self):
        result = resolve_temporal_references("This quarter sales")
        dates = result["resolved_dates"]
        assert dates is not None
        assert result["temporal_note"] is not None

    def test_last_month(self):
        result = resolve_temporal_references("Revenue last month")
        dates = result["resolved_dates"]
        assert dates is not None

    def test_ytd(self):
        result = resolve_temporal_references("YTD revenue")
        dates = result["resolved_dates"]
        assert dates["start"] == "2026-01-01"
        assert result["temporal_note"] is not None

    def test_year_to_date_full(self):
        result = resolve_temporal_references("year to date performance")
        dates = result["resolved_dates"]
        assert dates["start"] == "2026-01-01"

    def test_recent(self):
        result = resolve_temporal_references("recent sales trends")
        dates = result["resolved_dates"]
        assert dates is not None
        assert "30 days" in result["temporal_note"]


class TestSpecificMonth:
    """Test specific month references like 'January 2026'."""

    def test_january_2026(self):
        result = resolve_temporal_references("Sales in January 2026")
        dates = result["resolved_dates"]
        assert dates["start"] == "2026-01-01"
        assert dates["end"] == "2026-01-31"

    def test_feb_2026_abbreviated(self):
        result = resolve_temporal_references("Revenue in Feb 2026")
        dates = result["resolved_dates"]
        assert dates["start"] == "2026-02-01"
        assert dates["end"] == "2026-02-28"

    def test_october_2025(self):
        result = resolve_temporal_references("October 2025 data")
        dates = result["resolved_dates"]
        assert dates["start"] == "2025-10-01"
        assert dates["end"] == "2025-10-31"


class TestNoTemporal:
    """Test queries with no temporal references."""

    def test_no_date(self):
        result = resolve_temporal_references("Top selling products")
        assert result["resolved_dates"] is None
        assert result["temporal_note"] is None
        assert result["date_clause"] is None

    def test_just_numbers(self):
        result = resolve_temporal_references("Show me the top 5 regions")
        assert result["resolved_dates"] is None


class TestDateClause:
    """Test that date_clause is generated correctly."""

    def test_date_clause_format(self):
        result = resolve_temporal_references("Q1 2026 sales")
        assert result["date_clause"] is not None
        assert "SALE_DATE" in result["date_clause"]
        assert "2026-01-01" in result["date_clause"]
        assert "2026-03-31" in result["date_clause"]

    def test_date_clause_none_when_no_date(self):
        result = resolve_temporal_references("Total revenue")
        assert result["date_clause"] is None
