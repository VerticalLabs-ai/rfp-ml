"""Tests for analytics Pydantic schemas."""
import pytest
from datetime import datetime
from pydantic import ValidationError


def test_bid_outcome_create_schema():
    """BidOutcomeCreate validates required fields."""
    from api.app.schemas.analytics import BidOutcomeCreate

    # Valid creation
    outcome = BidOutcomeCreate(
        rfp_id=1,
        status="won",
        award_amount=100000.0,
    )
    assert outcome.status == "won"

    # Invalid status
    with pytest.raises(ValidationError):
        BidOutcomeCreate(rfp_id=1, status="invalid_status")


def test_win_loss_stats_schema():
    """WinLossStats schema has correct structure."""
    from api.app.schemas.analytics import WinLossStats

    stats = WinLossStats(
        total_bids=100,
        wins=45,
        losses=40,
        pending=10,
        no_bid=5,
        win_rate=0.529,
        total_revenue_won=5000000.0,
        average_deal_size=111111.11,
    )

    assert stats.win_rate == 0.529
    assert stats.total_bids == 100


def test_competitor_stats_schema():
    """CompetitorStats schema validates correctly."""
    from api.app.schemas.analytics import CompetitorStats

    stats = CompetitorStats(
        competitor_name="Acme Corp",
        encounters=10,
        wins_against_us=6,
        win_rate=0.6,
        categories=["IT", "Cloud"],
    )

    assert stats.win_rate == 0.6
