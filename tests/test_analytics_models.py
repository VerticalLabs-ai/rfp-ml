"""Tests for analytics database models."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.models.database import Base, BidOutcome, RFPOpportunity, CompetitorProfile


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_rfp(test_db):
    """Create a sample RFP for testing."""
    rfp = RFPOpportunity(
        rfp_id="TEST-001",
        title="Test RFP",
        description="Test description",
        agency="Test Agency",
        estimated_value=100000.0,
    )
    test_db.add(rfp)
    test_db.commit()
    return rfp


def test_bid_outcome_creation(test_db, sample_rfp):
    """BidOutcome can be created with required fields."""
    outcome = BidOutcome(
        rfp_id=sample_rfp.id,
        status="won",
        award_amount=95000.0,
        our_bid_amount=92000.0,
    )
    test_db.add(outcome)
    test_db.commit()

    assert outcome.id is not None
    assert outcome.status == "won"
    assert outcome.award_amount == 95000.0


def test_bid_outcome_to_dict(test_db, sample_rfp):
    """BidOutcome.to_dict() returns expected structure."""
    outcome = BidOutcome(
        rfp_id=sample_rfp.id,
        status="lost",
        award_amount=100000.0,
        our_bid_amount=105000.0,
        winning_bidder="Competitor Inc",
        loss_reason="Price too high",
    )
    test_db.add(outcome)
    test_db.commit()

    result = outcome.to_dict()

    assert result["status"] == "lost"
    assert result["winning_bidder"] == "Competitor Inc"
    assert result["loss_reason"] == "Price too high"
    assert "created_at" in result


def test_competitor_profile_creation(test_db):
    """CompetitorProfile can be created and tracks win counts."""
    competitor = CompetitorProfile(
        name="Acme Corp",
        wins_against_us=3,
        total_encounters=5,
    )
    test_db.add(competitor)
    test_db.commit()

    assert competitor.id is not None
    assert competitor.name == "Acme Corp"
    assert competitor.win_rate_against_us == 0.6  # 3/5


def test_competitor_profile_categories(test_db):
    """CompetitorProfile tracks categories as JSON."""
    competitor = CompetitorProfile(
        name="Tech Solutions",
        categories=["IT Services", "Cloud Computing"],
        agencies_won=["DoD", "GSA"],
    )
    test_db.add(competitor)
    test_db.commit()

    loaded = test_db.query(CompetitorProfile).first()
    assert "IT Services" in loaded.categories
    assert "DoD" in loaded.agencies_won
