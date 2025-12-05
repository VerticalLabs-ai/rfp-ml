"""Tests for analytics API routes."""
import pytest
from api.app.models.database import RFPOpportunity, BidOutcome


@pytest.fixture
def analytics_data(db_session):
    """Seed test data for analytics tests."""
    # Create RFPs with outcomes
    for i in range(10):
        rfp = RFPOpportunity(
            rfp_id=f"TEST-{i:03d}",
            title=f"Test RFP {i}",
            agency="Test Agency",
            estimated_value=100000.0 * (i + 1),
        )
        db_session.add(rfp)
        db_session.flush()

        status = "won" if i < 4 else ("lost" if i < 8 else "pending")
        outcome = BidOutcome(
            rfp_id=rfp.id,
            status=status,
            award_amount=rfp.estimated_value if status == "won" else None,
            our_bid_amount=rfp.estimated_value * 0.95,
        )
        db_session.add(outcome)

    db_session.commit()


def test_get_analytics_overview(client, analytics_data):
    """GET /analytics/overview returns stats."""
    response = client.get("/api/v1/analytics/overview")

    assert response.status_code == 200
    data = response.json()

    assert "stats" in data
    assert data["stats"]["total_bids"] == 10
    assert data["stats"]["wins"] == 4
    assert data["stats"]["losses"] == 4
    assert data["stats"]["pending"] == 2
    assert data["stats"]["win_rate"] == 0.5  # 4/(4+4) excluding pending


def test_get_analytics_overview_empty(client):
    """GET /analytics/overview returns zeros when no data."""
    response = client.get("/api/v1/analytics/overview")

    assert response.status_code == 200
    data = response.json()

    assert data["stats"]["total_bids"] == 0
    assert data["stats"]["win_rate"] == 0.0
