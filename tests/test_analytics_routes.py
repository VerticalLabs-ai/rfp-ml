"""Tests for analytics API routes."""
import pytest
from sqlalchemy.orm import sessionmaker
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


# =============================================================================
# CRUD Endpoints for Bid Outcomes (Task 5)
# =============================================================================


def test_create_bid_outcome(client, db_session):
    """POST /analytics/outcomes creates a new outcome."""
    # First create an RFP
    rfp = RFPOpportunity(rfp_id="CREATE-001", title="Test", agency="Test")
    db_session.add(rfp)
    db_session.commit()
    rfp_id = rfp.id

    response = client.post("/api/v1/analytics/outcomes", json={
        "rfp_id": rfp_id,
        "status": "won",
        "award_amount": 150000.0,
        "our_bid_amount": 145000.0,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "won"
    assert data["award_amount"] == 150000.0


def test_get_bid_outcome(client, db_session):
    """GET /analytics/outcomes/{id} returns outcome details."""
    rfp = RFPOpportunity(rfp_id="GET-001", title="Test", agency="Test")
    db_session.add(rfp)
    db_session.flush()
    outcome = BidOutcome(rfp_id=rfp.id, status="lost", winning_bidder="Competitor")
    db_session.add(outcome)
    db_session.commit()
    outcome_id = outcome.id

    response = client.get(f"/api/v1/analytics/outcomes/{outcome_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "lost"
    assert data["winning_bidder"] == "Competitor"


def test_update_bid_outcome(client, db_session):
    """PATCH /analytics/outcomes/{id} updates outcome."""
    rfp = RFPOpportunity(rfp_id="UPDATE-001", title="Test", agency="Test")
    db_session.add(rfp)
    db_session.flush()
    outcome = BidOutcome(rfp_id=rfp.id, status="pending")
    db_session.add(outcome)
    db_session.commit()
    outcome_id = outcome.id

    response = client.patch(f"/api/v1/analytics/outcomes/{outcome_id}", json={
        "status": "won",
        "award_amount": 200000.0,
        "lessons_learned": "Price was competitive",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "won"
    assert data["lessons_learned"] == "Price was competitive"


def test_list_bid_outcomes(client, analytics_data):
    """GET /analytics/outcomes returns paginated list."""
    response = client.get("/api/v1/analytics/outcomes")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 10
