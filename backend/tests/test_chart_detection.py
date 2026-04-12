"""
Tests for Chart Type Detection — validates _detect_chart_type heuristics.
"""

import pytest
from src.branches.branch_sql import _detect_chart_type


class TestNumberCard:
    """Single-value results should render as a number card."""

    def test_single_value(self):
        cols = ["TOTAL_SALES"]
        rows = [{"TOTAL_SALES": 1234567.89}]
        assert _detect_chart_type(cols, rows, "SELECT SUM(ACTUAL_SALES) FROM AURA_SALES") == "number"

    def test_single_row_few_cols(self):
        cols = ["TOTAL_SALES", "TOTAL_UNITS"]
        rows = [{"TOTAL_SALES": 100000, "TOTAL_UNITS": 500}]
        assert _detect_chart_type(cols, rows, "SELECT SUM(ACTUAL_SALES), SUM(UNITS_SOLD) FROM AURA_SALES") == "number"

    def test_single_row_three_cols(self):
        cols = ["TOTAL", "AVG", "COUNT"]
        rows = [{"TOTAL": 100, "AVG": 50, "COUNT": 2}]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "number"


class TestTimeSeriesDetection:
    """Time-series data should render as line charts."""

    def test_month_column(self):
        cols = ["SALE_MONTH", "TOTAL_SALES"]
        rows = [
            {"SALE_MONTH": "2025-10", "TOTAL_SALES": 100},
            {"SALE_MONTH": "2025-11", "TOTAL_SALES": 200},
            {"SALE_MONTH": "2025-12", "TOTAL_SALES": 300},
        ]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"

    def test_date_column(self):
        cols = ["SALE_DATE", "REVENUE"]
        rows = [
            {"SALE_DATE": "2026-01-01", "REVENUE": 100},
            {"SALE_DATE": "2026-01-15", "REVENUE": 200},
            {"SALE_DATE": "2026-02-01", "REVENUE": 300},
        ]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"

    def test_metric_month_column(self):
        cols = ["METRIC_MONTH", "CHURN_RATE"]
        rows = [
            {"METRIC_MONTH": "2025-10-01", "CHURN_RATE": 0.05},
            {"METRIC_MONTH": "2025-11-01", "CHURN_RATE": 0.06},
            {"METRIC_MONTH": "2025-12-01", "CHURN_RATE": 0.07},
        ]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"

    def test_date_trunc_in_sql(self):
        cols = ["M", "TOTAL"]
        rows = [
            {"M": "2025-10-01", "TOTAL": 100},
            {"M": "2025-11-01", "TOTAL": 200},
            {"M": "2025-12-01", "TOTAL": 300},
        ]
        assert _detect_chart_type(cols, rows, "SELECT DATE_TRUNC('month', SALE_DATE) AS M, SUM(ACTUAL_SALES)") == "line"

    def test_date_like_first_value(self):
        """First column value looks like a date string (YYYY-MM-...)."""
        cols = ["PERIOD", "VALUE"]
        rows = [
            {"PERIOD": "2026-01", "VALUE": 100},
            {"PERIOD": "2026-02", "VALUE": 200},
            {"PERIOD": "2026-03", "VALUE": 300},
        ]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"


class TestRateColumns:
    """Columns with RATE/PERCENT in the name → line chart when trending."""

    def test_churn_rate_trend(self):
        cols = ["REGION", "CHURN_RATE"]
        rows = [
            {"REGION": "North", "CHURN_RATE": 0.05},
            {"REGION": "South", "CHURN_RATE": 0.08},
            {"REGION": "East", "CHURN_RATE": 0.06},
            {"REGION": "West", "CHURN_RATE": 0.04},
        ]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"

    def test_return_rate_trend(self):
        cols = ["PRODUCT", "RETURN_RATE"]
        rows = [{"PRODUCT": f"P{i}", "RETURN_RATE": 0.01 * i} for i in range(1, 6)]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "line"


class TestCategoricalBar:
    """Categorical data with numeric values → bar chart."""

    def test_region_sales_bar(self):
        cols = ["REGION", "TOTAL_SALES"]
        rows = [
            {"REGION": "North", "TOTAL_SALES": 3000000},
            {"REGION": "South", "TOTAL_SALES": 2000000},
            {"REGION": "East", "TOTAL_SALES": 2500000},
            {"REGION": "West", "TOTAL_SALES": 2200000},
        ]
        # hint=bar should respect when no time column detected
        # But RATE detection may trigger — let's use a column without RATE
        result = _detect_chart_type(cols, rows, "SELECT ...", hint="bar")
        assert result == "bar"


class TestDoughnutHint:
    """Small categorical sets with doughnut hint → doughnut."""

    def test_small_set_doughnut(self):
        cols = ["CHANNEL", "SHARE"]
        rows = [
            {"CHANNEL": "Online", "SHARE": 35},
            {"CHANNEL": "In-Store", "SHARE": 45},
            {"CHANNEL": "Partner", "SHARE": 20},
        ]
        # Only returns doughnut if explicitly hinted
        result = _detect_chart_type(cols, rows, "SELECT ...", hint="doughnut")
        assert result == "doughnut"


class TestTable:
    """Large or non-numeric results → table."""

    def test_empty_rows(self):
        assert _detect_chart_type([], [], "SELECT ...") == "table"

    def test_many_rows_no_numeric(self):
        cols = ["NAME", "CATEGORY", "STATUS"]
        rows = [{"NAME": f"P{i}", "CATEGORY": "A", "STATUS": "Active"} for i in range(50)]
        assert _detect_chart_type(cols, rows, "SELECT ...") == "table"
