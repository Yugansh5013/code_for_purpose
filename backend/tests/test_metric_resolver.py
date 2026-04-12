"""
Tests for Metric Resolver — alias matching, ambiguity detection, jargon map.
"""

import pytest
from src.clarification.metric_resolver import resolve_metrics, get_jargon_map, get_all_metrics_for_glossary


class TestDirectMetricMatching:
    """Test that known metric aliases resolve correctly."""

    def test_revenue_alias_sales(self):
        result = resolve_metrics("what are total sales?")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "revenue" in matched

    def test_revenue_alias_turnover(self):
        result = resolve_metrics("turnover by region")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "revenue" in matched

    def test_churn_alias_attrition(self):
        result = resolve_metrics("customer attrition rate")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "churn" in matched

    def test_churn_alias_lost_customers(self):
        result = resolve_metrics("how many lost customers?")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "churn" in matched

    def test_return_rate_alias(self):
        result = resolve_metrics("product returns by region")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "return_rate" in matched

    def test_units_sold_alias_volume(self):
        result = resolve_metrics("what's the volume by product?")
        assert not result["ambiguous"]
        matched = result["matched_metrics"]
        assert "units_sold" in matched

    def test_ad_spend_alias(self):
        result = resolve_metrics("how much we spent on ads last quarter")
        assert not result["ambiguous"]


class TestAmbiguousMetrics:
    """Test that ambiguous terms trigger clarification."""

    def test_performance_is_ambiguous(self):
        result = resolve_metrics("How is our performance?")
        assert result["ambiguous"] is True
        assert len(result["clarification_options"]) > 0

    def test_kpis_is_ambiguous(self):
        result = resolve_metrics("show me the KPIs")
        assert result["ambiguous"] is True

    def test_results_is_ambiguous(self):
        result = resolve_metrics("what are our results?")
        assert result["ambiguous"] is True

    def test_clarification_options_have_labels(self):
        result = resolve_metrics("How are we performing?")
        if result["ambiguous"]:
            for opt in result["clarification_options"]:
                assert "label" in opt
                assert "value" in opt


class TestResolvedInfo:
    """Test that resolved_info includes correct column mappings."""

    def test_revenue_resolved_info(self):
        result = resolve_metrics("total sales by region")
        info = result["resolved_info"]
        assert len(info) > 0
        revenue_info = next((i for i in info if i.get("canonical_column") == "ACTUAL_SALES"), None)
        assert revenue_info is not None
        assert revenue_info["display_name"] == "Total Sales"

    def test_churn_resolved_info(self):
        result = resolve_metrics("churn rate trends")
        info = result["resolved_info"]
        churn_info = next((i for i in info if i.get("canonical_column") == "CHURN_RATE"), None)
        assert churn_info is not None


class TestNoMetricMatch:
    """Test queries that don't match any metric."""

    def test_random_question(self):
        result = resolve_metrics("what is the weather today?")
        assert not result["ambiguous"]
        assert len(result["matched_metrics"]) == 0

    def test_product_name_query(self):
        """Product-specific queries may not match a metric alias."""
        result = resolve_metrics("Tell me about AuraSound Pro")
        # Should not be ambiguous — just no match
        assert not result["ambiguous"]


class TestJargonMap:
    """Test the jargon substitution map."""

    def test_jargon_map_not_empty(self):
        jmap = get_jargon_map()
        assert len(jmap) > 0

    def test_actual_sales_in_jargon(self):
        jmap = get_jargon_map()
        assert "ACTUAL_SALES" in jmap or "actual_sales" in jmap

    def test_churn_rate_in_jargon(self):
        jmap = get_jargon_map()
        assert "CHURN_RATE" in jmap or "churn_rate" in jmap


class TestGlossaryEndpoint:
    """Test the glossary output format."""

    def test_glossary_returns_list(self):
        result = get_all_metrics_for_glossary()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_glossary_items_have_fields(self):
        result = get_all_metrics_for_glossary()
        for item in result:
            assert "key" in item
            assert "display_name" in item
            assert "description" in item
