"""
Tests for Confidence Scorer — score calculation, tier assignment, signal weighting.
"""

import pytest
from src.validation.confidence_scorer import (
    calculate_confidence,
    WEIGHTS,
    TIER_GREEN,
    TIER_AMBER,
    PINECONE_LOW_THRESHOLD,
)


class TestTierAssignment:
    """Test that confidence tiers are assigned correctly."""

    def test_perfect_score_is_green(self):
        """High Pinecone score + no retries + data returned = green."""
        result = calculate_confidence(
            pinecone_top_score=0.95,
            retry_count=0,
            row_count=10,
            is_aggregate=False,
        )
        assert result["tier"] == "green"
        assert result["score"] >= TIER_GREEN

    def test_one_retry_is_amber(self):
        """Good Pinecone but 1 retry should drop into amber range."""
        result = calculate_confidence(
            pinecone_top_score=0.85,
            retry_count=1,
            row_count=5,
            is_aggregate=False,
        )
        assert result["tier"] in ("amber", "green")
        # With pinecone=0.85*0.4=0.34, retry=0.5*0.4=0.2, sanity=1.0*0.2=0.2 => 0.74 = amber
        assert result["score"] >= TIER_AMBER

    def test_two_retries_low_pinecone_is_red(self):
        """Low Pinecone + 2 retries + no rows = definitely red."""
        result = calculate_confidence(
            pinecone_top_score=0.3,
            retry_count=2,
            row_count=0,
            is_aggregate=False,
        )
        assert result["tier"] == "red"
        assert result["score"] < TIER_AMBER

    def test_no_rows_non_aggregate_penalized(self):
        """Zero rows on a non-aggregate query should reduce sanity signal."""
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=0,
            row_count=0,
            is_aggregate=False,
        )
        assert result["signals"]["result_sanity"] < 1.0

    def test_no_rows_aggregate_less_penalized(self):
        """Zero rows on aggregate is suspicious but possible."""
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=0,
            row_count=0,
            is_aggregate=True,
        )
        assert result["signals"]["result_sanity"] == 0.5


class TestScoreCalculation:
    """Test the exact math of the scoring formula."""

    def test_perfect_signals(self):
        """All signals at maximum."""
        result = calculate_confidence(
            pinecone_top_score=1.0,
            retry_count=0,
            row_count=100,
        )
        # 1.0*0.4 + 1.0*0.4 + 1.0*0.2 = 1.0
        assert result["score"] == 1.0

    def test_score_clamped_at_1(self):
        """Score should never exceed 1.0."""
        result = calculate_confidence(
            pinecone_top_score=1.5,  # Intentionally over 1
            retry_count=0,
            row_count=50,
        )
        assert result["score"] <= 1.0

    def test_score_clamped_at_0(self):
        """Score should never go below 0.0."""
        result = calculate_confidence(
            pinecone_top_score=0.0,
            retry_count=5,
            row_count=0,
        )
        assert result["score"] >= 0.0


class TestPineconeSignal:
    """Test the Pinecone relevance signal behavior."""

    def test_high_pinecone_full_weight(self):
        """Scores >= threshold get full weight."""
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=0,
            row_count=10,
        )
        # Signal should be 0.9 (not penalized)
        assert result["signals"]["pinecone_relevance"] == 0.9

    def test_low_pinecone_penalized(self):
        """Scores below threshold get 0.6x penalty."""
        result = calculate_confidence(
            pinecone_top_score=0.5,
            retry_count=0,
            row_count=10,
        )
        # Signal = 0.5 * 0.6 = 0.3
        assert result["signals"]["pinecone_relevance"] == 0.3


class TestRetrySignal:
    """Test the retry count signal behavior."""

    def test_zero_retries_full_score(self):
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=0,
            row_count=10,
        )
        assert result["signals"]["retry_penalty"] == 1.0

    def test_one_retry_half_score(self):
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=1,
            row_count=10,
        )
        assert result["signals"]["retry_penalty"] == 0.5

    def test_two_retries_zero_score(self):
        result = calculate_confidence(
            pinecone_top_score=0.9,
            retry_count=2,
            row_count=10,
        )
        assert result["signals"]["retry_penalty"] == 0.0


class TestSignalBreakdown:
    """Test that signal breakdown is always returned."""

    def test_signals_dict_present(self):
        result = calculate_confidence(0.85, 0, 5)
        assert "signals" in result
        assert "pinecone_relevance" in result["signals"]
        assert "retry_penalty" in result["signals"]
        assert "result_sanity" in result["signals"]

    def test_all_signals_are_floats(self):
        result = calculate_confidence(0.85, 0, 5)
        for key, val in result["signals"].items():
            assert isinstance(val, float), f"Signal {key} should be float, got {type(val)}"

    def test_score_is_float(self):
        result = calculate_confidence(0.85, 0, 5)
        assert isinstance(result["score"], float)

    def test_tier_is_string(self):
        result = calculate_confidence(0.85, 0, 5)
        assert result["tier"] in ("green", "amber", "red")
