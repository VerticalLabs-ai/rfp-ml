# Win/Loss Analytics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build comprehensive win/loss analytics to help users understand proposal success patterns, track competitors, and improve bid strategy.

**Architecture:** Backend-first approach with SQLAlchemy models for BidOutcome and CompetitorProfile, FastAPI routes for analytics data, and a React dashboard with Recharts for visualization. Leverages existing Go/No-Go engine for win probability predictions.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, TanStack Query, Recharts, TypeScript

---

## Task 1: Create BidOutcome Database Model

**Files:**
- Modify: `api/app/models/database.py` (add after line ~790, before DashboardMetrics)

**Step 1: Write the failing test**

Create test file first:

```python
# tests/test_analytics_models.py
"""Tests for analytics database models."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.models.database import Base, BidOutcome, RFPOpportunity


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_models.py -v`
Expected: FAIL with "cannot import name 'BidOutcome' from 'api.app.models.database'"

**Step 3: Write minimal implementation**

Add to `api/app/models/database.py` after line ~790:

```python
class BidOutcome(Base):
    """Tracks win/loss outcomes for submitted proposals."""
    __tablename__ = "bid_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), nullable=False)

    # Outcome details
    status = Column(String(20), nullable=False)  # won, lost, pending, no_bid, withdrawn
    award_amount = Column(Float, nullable=True)
    our_bid_amount = Column(Float, nullable=True)
    winning_bidder = Column(String(255), nullable=True)
    winning_bid_amount = Column(Float, nullable=True)

    # Analysis fields
    loss_reason = Column(Text, nullable=True)
    debrief_notes = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    price_delta_percentage = Column(Float, nullable=True)  # How far off we were

    # Dates
    award_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    rfp = relationship("RFPOpportunity", back_populates="bid_outcome")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "status": self.status,
            "award_amount": self.award_amount,
            "our_bid_amount": self.our_bid_amount,
            "winning_bidder": self.winning_bidder,
            "winning_bid_amount": self.winning_bid_amount,
            "loss_reason": self.loss_reason,
            "debrief_notes": self.debrief_notes,
            "lessons_learned": self.lessons_learned,
            "price_delta_percentage": self.price_delta_percentage,
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

Also add the back_populates relationship to RFPOpportunity class (around line 130):

```python
# Add to RFPOpportunity class relationships section:
bid_outcome = relationship("BidOutcome", back_populates="rfp", uselist=False)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_models.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add tests/test_analytics_models.py api/app/models/database.py
git commit -m "feat(models): add BidOutcome model for win/loss tracking"
```

---

## Task 2: Create CompetitorProfile Database Model

**Files:**
- Modify: `api/app/models/database.py` (add after BidOutcome)
- Modify: `tests/test_analytics_models.py`

**Step 1: Write the failing test**

Add to `tests/test_analytics_models.py`:

```python
from api.app.models.database import CompetitorProfile


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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_models.py::test_competitor_profile_creation -v`
Expected: FAIL with "cannot import name 'CompetitorProfile'"

**Step 3: Write minimal implementation**

Add to `api/app/models/database.py` after BidOutcome:

```python
class CompetitorProfile(Base):
    """Tracks competitor information and win patterns."""
    __tablename__ = "competitor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)

    # Win tracking
    wins_against_us = Column(Integer, default=0)
    losses_against_us = Column(Integer, default=0)
    total_encounters = Column(Integer, default=0)

    # Pattern tracking (JSON arrays)
    categories = Column(JSON, default=list)  # NAICS categories they win
    agencies_won = Column(JSON, default=list)  # Agencies they've won with
    typical_bid_range = Column(JSON, nullable=True)  # {"min": X, "max": Y}

    # Notes
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def win_rate_against_us(self) -> float:
        """Calculate win rate against us."""
        if self.total_encounters == 0:
            return 0.0
        return self.wins_against_us / self.total_encounters

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "wins_against_us": self.wins_against_us,
            "losses_against_us": self.losses_against_us,
            "total_encounters": self.total_encounters,
            "win_rate_against_us": self.win_rate_against_us,
            "categories": self.categories or [],
            "agencies_won": self.agencies_won or [],
            "typical_bid_range": self.typical_bid_range,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "notes": self.notes,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_models.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add api/app/models/database.py tests/test_analytics_models.py
git commit -m "feat(models): add CompetitorProfile model for competitive intelligence"
```

---

## Task 3: Create Analytics Pydantic Schemas

**Files:**
- Create: `api/app/schemas/analytics.py`

**Step 1: Write the failing test**

```python
# tests/test_analytics_schemas.py
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_schemas.py -v`
Expected: FAIL with "No module named 'api.app.schemas.analytics'"

**Step 3: Write minimal implementation**

```python
# api/app/schemas/analytics.py
"""Pydantic schemas for win/loss analytics."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class BidOutcomeCreate(BaseModel):
    """Schema for creating a bid outcome record."""
    rfp_id: int
    status: str = Field(..., description="won, lost, pending, no_bid, withdrawn")
    award_amount: Optional[float] = None
    our_bid_amount: Optional[float] = None
    winning_bidder: Optional[str] = None
    winning_bid_amount: Optional[float] = None
    loss_reason: Optional[str] = None
    debrief_notes: Optional[str] = None
    award_date: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"won", "lost", "pending", "no_bid", "withdrawn"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v


class BidOutcomeUpdate(BaseModel):
    """Schema for updating a bid outcome record."""
    status: Optional[str] = None
    award_amount: Optional[float] = None
    our_bid_amount: Optional[float] = None
    winning_bidder: Optional[str] = None
    winning_bid_amount: Optional[float] = None
    loss_reason: Optional[str] = None
    debrief_notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    award_date: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"won", "lost", "pending", "no_bid", "withdrawn"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v


class BidOutcomeResponse(BaseModel):
    """Schema for bid outcome API response."""
    id: int
    rfp_id: int
    status: str
    award_amount: Optional[float] = None
    our_bid_amount: Optional[float] = None
    winning_bidder: Optional[str] = None
    winning_bid_amount: Optional[float] = None
    loss_reason: Optional[str] = None
    debrief_notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    price_delta_percentage: Optional[float] = None
    award_date: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WinLossStats(BaseModel):
    """Aggregated win/loss statistics."""
    total_bids: int
    wins: int
    losses: int
    pending: int
    no_bid: int = 0
    withdrawn: int = 0
    win_rate: float = Field(..., ge=0, le=1)
    total_revenue_won: float = 0.0
    total_revenue_lost: float = 0.0
    average_deal_size: float = 0.0
    average_margin: Optional[float] = None


class WinLossTrend(BaseModel):
    """Win/loss trend data point."""
    period: str  # "2024-Q1", "2024-01", etc.
    wins: int
    losses: int
    win_rate: float
    revenue: float


class CompetitorStats(BaseModel):
    """Statistics for a single competitor."""
    competitor_name: str
    encounters: int
    wins_against_us: int
    losses_against_us: int = 0
    win_rate: float
    categories: list[str] = []
    agencies: list[str] = []
    average_winning_margin: Optional[float] = None


class AnalyticsFilters(BaseModel):
    """Filters for analytics queries."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    agency: Optional[str] = None
    naics_code: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    status: Optional[str] = None


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard response."""
    stats: WinLossStats
    trends: list[WinLossTrend] = []
    top_competitors: list[CompetitorStats] = []
    win_rate_by_category: dict[str, float] = {}
    win_rate_by_agency: dict[str, float] = {}
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_schemas.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add api/app/schemas/analytics.py tests/test_analytics_schemas.py
git commit -m "feat(schemas): add Pydantic schemas for analytics API"
```

---

## Task 4: Create Analytics API Routes - Overview Endpoint

**Files:**
- Create: `api/app/routes/analytics.py`
- Modify: `api/app/main.py` (register router)

**Step 1: Write the failing test**

```python
# tests/test_analytics_routes.py
"""Tests for analytics API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.models.database import Base, RFPOpportunity, BidOutcome
from api.app.main import app
from api.app.core.database import get_db


# Test database setup
SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client with overridden DB."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data():
    """Seed test data."""
    db = TestingSessionLocal()

    # Create RFPs with outcomes
    for i in range(10):
        rfp = RFPOpportunity(
            rfp_id=f"TEST-{i:03d}",
            title=f"Test RFP {i}",
            agency="Test Agency",
            estimated_value=100000.0 * (i + 1),
        )
        db.add(rfp)
        db.flush()

        status = "won" if i < 4 else ("lost" if i < 8 else "pending")
        outcome = BidOutcome(
            rfp_id=rfp.id,
            status=status,
            award_amount=rfp.estimated_value if status == "won" else None,
            our_bid_amount=rfp.estimated_value * 0.95,
        )
        db.add(outcome)

    db.commit()
    db.close()


def test_get_analytics_overview(client, seed_data):
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py::test_get_analytics_overview -v`
Expected: FAIL with 404 (route not found)

**Step 3: Write minimal implementation**

```python
# api/app/routes/analytics.py
"""Win/Loss Analytics API routes."""
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Optional

from app.dependencies import DBDep
from app.models.database import BidOutcome, RFPOpportunity, CompetitorProfile
from app.schemas.analytics import (
    AnalyticsDashboard,
    WinLossStats,
    WinLossTrend,
    CompetitorStats,
    BidOutcomeCreate,
    BidOutcomeUpdate,
    BidOutcomeResponse,
    AnalyticsFilters,
)

router = APIRouter()


@router.get("/overview", response_model=AnalyticsDashboard)
async def get_analytics_overview(
    db: DBDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agency: Optional[str] = None,
    naics_code: Optional[str] = None,
):
    """
    Get comprehensive analytics dashboard data.

    Returns win/loss stats, trends, and competitor analysis.
    """
    # Base query for outcomes
    query = db.query(BidOutcome).join(RFPOpportunity)

    # Apply filters
    if start_date:
        query = query.filter(BidOutcome.created_at >= start_date)
    if end_date:
        query = query.filter(BidOutcome.created_at <= end_date)
    if agency:
        query = query.filter(RFPOpportunity.agency == agency)
    if naics_code:
        query = query.filter(RFPOpportunity.naics_code == naics_code)

    outcomes = query.all()

    # Calculate stats
    total = len(outcomes)
    wins = sum(1 for o in outcomes if o.status == "won")
    losses = sum(1 for o in outcomes if o.status == "lost")
    pending = sum(1 for o in outcomes if o.status == "pending")
    no_bid = sum(1 for o in outcomes if o.status == "no_bid")
    withdrawn = sum(1 for o in outcomes if o.status == "withdrawn")

    # Win rate excludes pending/no_bid/withdrawn
    decided = wins + losses
    win_rate = wins / decided if decided > 0 else 0.0

    # Revenue calculations
    revenue_won = sum(o.award_amount or 0 for o in outcomes if o.status == "won")
    revenue_lost = sum(o.award_amount or 0 for o in outcomes if o.status == "lost")
    avg_deal = revenue_won / wins if wins > 0 else 0.0

    stats = WinLossStats(
        total_bids=total,
        wins=wins,
        losses=losses,
        pending=pending,
        no_bid=no_bid,
        withdrawn=withdrawn,
        win_rate=round(win_rate, 3),
        total_revenue_won=revenue_won,
        total_revenue_lost=revenue_lost,
        average_deal_size=round(avg_deal, 2),
    )

    # Get trends (last 6 months)
    trends = _calculate_trends(db, outcomes)

    # Get top competitors
    top_competitors = _get_top_competitors(db, limit=5)

    # Win rate by category
    win_rate_by_category = _win_rate_by_field(db, outcomes, "naics_code")
    win_rate_by_agency = _win_rate_by_field(db, outcomes, "agency")

    return AnalyticsDashboard(
        stats=stats,
        trends=trends,
        top_competitors=top_competitors,
        win_rate_by_category=win_rate_by_category,
        win_rate_by_agency=win_rate_by_agency,
    )


def _calculate_trends(db, outcomes: list[BidOutcome]) -> list[WinLossTrend]:
    """Calculate win/loss trends by month."""
    if not outcomes:
        return []

    # Group by month
    monthly = {}
    for outcome in outcomes:
        if outcome.created_at:
            key = outcome.created_at.strftime("%Y-%m")
            if key not in monthly:
                monthly[key] = {"wins": 0, "losses": 0, "revenue": 0}

            if outcome.status == "won":
                monthly[key]["wins"] += 1
                monthly[key]["revenue"] += outcome.award_amount or 0
            elif outcome.status == "lost":
                monthly[key]["losses"] += 1

    # Convert to trend objects
    trends = []
    for period in sorted(monthly.keys())[-6:]:  # Last 6 months
        data = monthly[period]
        total = data["wins"] + data["losses"]
        win_rate = data["wins"] / total if total > 0 else 0.0

        trends.append(WinLossTrend(
            period=period,
            wins=data["wins"],
            losses=data["losses"],
            win_rate=round(win_rate, 3),
            revenue=data["revenue"],
        ))

    return trends


def _get_top_competitors(db, limit: int = 5) -> list[CompetitorStats]:
    """Get competitors with most encounters."""
    competitors = (
        db.query(CompetitorProfile)
        .order_by(CompetitorProfile.total_encounters.desc())
        .limit(limit)
        .all()
    )

    return [
        CompetitorStats(
            competitor_name=c.name,
            encounters=c.total_encounters,
            wins_against_us=c.wins_against_us,
            losses_against_us=c.losses_against_us,
            win_rate=c.win_rate_against_us,
            categories=c.categories or [],
            agencies=c.agencies_won or [],
        )
        for c in competitors
    ]


def _win_rate_by_field(db, outcomes: list[BidOutcome], field: str) -> dict[str, float]:
    """Calculate win rate grouped by RFP field."""
    grouped = {}

    for outcome in outcomes:
        if outcome.rfp:
            key = getattr(outcome.rfp, field, None) or "Unknown"
            if key not in grouped:
                grouped[key] = {"wins": 0, "total": 0}

            if outcome.status in ("won", "lost"):
                grouped[key]["total"] += 1
                if outcome.status == "won":
                    grouped[key]["wins"] += 1

    return {
        k: round(v["wins"] / v["total"], 3) if v["total"] > 0 else 0.0
        for k, v in grouped.items()
    }
```

Register router in `api/app/main.py` - add after other router includes (~line 140):

```python
from app.routes import analytics

app.include_router(
    analytics.router,
    prefix=f"{settings.API_V1_STR}/analytics",
    tags=["analytics"],
)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add api/app/routes/analytics.py api/app/main.py tests/test_analytics_routes.py
git commit -m "feat(api): add analytics overview endpoint with win/loss stats"
```

---

## Task 5: Add CRUD Endpoints for Bid Outcomes

**Files:**
- Modify: `api/app/routes/analytics.py`
- Modify: `tests/test_analytics_routes.py`

**Step 1: Write the failing test**

Add to `tests/test_analytics_routes.py`:

```python
def test_create_bid_outcome(client):
    """POST /analytics/outcomes creates a new outcome."""
    # First create an RFP
    db = TestingSessionLocal()
    rfp = RFPOpportunity(rfp_id="CREATE-001", title="Test", agency="Test")
    db.add(rfp)
    db.commit()
    rfp_id = rfp.id
    db.close()

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


def test_get_bid_outcome(client):
    """GET /analytics/outcomes/{id} returns outcome details."""
    db = TestingSessionLocal()
    rfp = RFPOpportunity(rfp_id="GET-001", title="Test", agency="Test")
    db.add(rfp)
    db.flush()
    outcome = BidOutcome(rfp_id=rfp.id, status="lost", winning_bidder="Competitor")
    db.add(outcome)
    db.commit()
    outcome_id = outcome.id
    db.close()

    response = client.get(f"/api/v1/analytics/outcomes/{outcome_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "lost"
    assert data["winning_bidder"] == "Competitor"


def test_update_bid_outcome(client):
    """PATCH /analytics/outcomes/{id} updates outcome."""
    db = TestingSessionLocal()
    rfp = RFPOpportunity(rfp_id="UPDATE-001", title="Test", agency="Test")
    db.add(rfp)
    db.flush()
    outcome = BidOutcome(rfp_id=rfp.id, status="pending")
    db.add(outcome)
    db.commit()
    outcome_id = outcome.id
    db.close()

    response = client.patch(f"/api/v1/analytics/outcomes/{outcome_id}", json={
        "status": "won",
        "award_amount": 200000.0,
        "lessons_learned": "Price was competitive",
    })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "won"
    assert data["lessons_learned"] == "Price was competitive"


def test_list_bid_outcomes(client, seed_data):
    """GET /analytics/outcomes returns paginated list."""
    response = client.get("/api/v1/analytics/outcomes")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) == 10
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py::test_create_bid_outcome -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `api/app/routes/analytics.py`:

```python
from fastapi import status
from typing import List


@router.post("/outcomes", response_model=BidOutcomeResponse, status_code=status.HTTP_201_CREATED)
async def create_bid_outcome(
    data: BidOutcomeCreate,
    db: DBDep,
):
    """Create a new bid outcome record."""
    # Verify RFP exists
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == data.rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Check if outcome already exists
    existing = db.query(BidOutcome).filter(BidOutcome.rfp_id == data.rfp_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Outcome already exists for this RFP")

    # Calculate price delta if we have both amounts
    price_delta = None
    if data.our_bid_amount and data.winning_bid_amount:
        price_delta = ((data.our_bid_amount - data.winning_bid_amount) / data.winning_bid_amount) * 100

    outcome = BidOutcome(
        rfp_id=data.rfp_id,
        status=data.status,
        award_amount=data.award_amount,
        our_bid_amount=data.our_bid_amount,
        winning_bidder=data.winning_bidder,
        winning_bid_amount=data.winning_bid_amount,
        loss_reason=data.loss_reason,
        debrief_notes=data.debrief_notes,
        award_date=data.award_date,
        price_delta_percentage=price_delta,
    )

    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    # Update competitor profile if lost
    if data.status == "lost" and data.winning_bidder:
        _update_competitor_profile(db, data.winning_bidder, won=True, rfp=rfp)

    return outcome.to_dict()


@router.get("/outcomes/{outcome_id}", response_model=BidOutcomeResponse)
async def get_bid_outcome(
    outcome_id: int,
    db: DBDep,
):
    """Get a specific bid outcome by ID."""
    outcome = db.query(BidOutcome).filter(BidOutcome.id == outcome_id).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    return outcome.to_dict()


@router.patch("/outcomes/{outcome_id}", response_model=BidOutcomeResponse)
async def update_bid_outcome(
    outcome_id: int,
    data: BidOutcomeUpdate,
    db: DBDep,
):
    """Update a bid outcome record."""
    outcome = db.query(BidOutcome).filter(BidOutcome.id == outcome_id).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    # Update fields that are provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(outcome, field, value)

    # Recalculate price delta if relevant fields changed
    if outcome.our_bid_amount and outcome.winning_bid_amount:
        outcome.price_delta_percentage = (
            (outcome.our_bid_amount - outcome.winning_bid_amount) / outcome.winning_bid_amount
        ) * 100

    db.commit()
    db.refresh(outcome)

    return outcome.to_dict()


class PaginatedOutcomes(BaseModel):
    """Paginated list of bid outcomes."""
    items: List[BidOutcomeResponse]
    total: int
    page: int
    page_size: int


@router.get("/outcomes", response_model=PaginatedOutcomes)
async def list_bid_outcomes(
    db: DBDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agency: Optional[str] = None,
):
    """List bid outcomes with pagination and filters."""
    query = db.query(BidOutcome).join(RFPOpportunity)

    if status:
        query = query.filter(BidOutcome.status == status)
    if agency:
        query = query.filter(RFPOpportunity.agency == agency)

    total = query.count()

    outcomes = (
        query
        .order_by(BidOutcome.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedOutcomes(
        items=[o.to_dict() for o in outcomes],
        total=total,
        page=page,
        page_size=page_size,
    )


def _update_competitor_profile(db, competitor_name: str, won: bool, rfp: RFPOpportunity):
    """Update or create competitor profile."""
    profile = db.query(CompetitorProfile).filter(
        CompetitorProfile.name == competitor_name
    ).first()

    if not profile:
        profile = CompetitorProfile(name=competitor_name)
        db.add(profile)

    profile.total_encounters += 1
    if won:
        profile.wins_against_us += 1
    else:
        profile.losses_against_us += 1

    # Update categories
    if rfp.naics_code and rfp.naics_code not in (profile.categories or []):
        profile.categories = (profile.categories or []) + [rfp.naics_code]

    # Update agencies
    if rfp.agency and rfp.agency not in (profile.agencies_won or []):
        profile.agencies_won = (profile.agencies_won or []) + [rfp.agency]

    profile.last_seen = datetime.utcnow()
    db.commit()
```

Add the import at top:

```python
from pydantic import BaseModel
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add api/app/routes/analytics.py tests/test_analytics_routes.py
git commit -m "feat(api): add CRUD endpoints for bid outcomes"
```

---

## Task 6: Create TypeScript Types for Analytics

**Files:**
- Create: `frontend/src/types/analytics.ts`

**Step 1: Write the failing test**

TypeScript types don't have runtime tests, but we verify by importing in a test file:

```typescript
// frontend/src/types/__tests__/analytics.test.ts
import { describe, it, expect } from 'vitest'
import type {
  BidOutcome,
  WinLossStats,
  AnalyticsDashboard,
  CompetitorStats,
} from '../analytics'

describe('Analytics Types', () => {
  it('BidOutcome has required fields', () => {
    const outcome: BidOutcome = {
      id: 1,
      rfp_id: 1,
      status: 'won',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    }
    expect(outcome.status).toBe('won')
  })

  it('WinLossStats has correct structure', () => {
    const stats: WinLossStats = {
      total_bids: 100,
      wins: 45,
      losses: 40,
      pending: 15,
      win_rate: 0.529,
      total_revenue_won: 5000000,
      total_revenue_lost: 3000000,
      average_deal_size: 111111,
    }
    expect(stats.win_rate).toBe(0.529)
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/types/__tests__/analytics.test.ts`
Expected: FAIL with "Cannot find module '../analytics'"

**Step 3: Write minimal implementation**

```typescript
// frontend/src/types/analytics.ts
/**
 * TypeScript types for Win/Loss Analytics feature.
 */

export type BidStatus = 'won' | 'lost' | 'pending' | 'no_bid' | 'withdrawn'

export interface BidOutcome {
  id: number
  rfp_id: number
  status: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  lessons_learned?: string
  price_delta_percentage?: number
  award_date?: string
  created_at: string
  updated_at: string
}

export interface BidOutcomeCreate {
  rfp_id: number
  status: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  award_date?: string
}

export interface BidOutcomeUpdate {
  status?: BidStatus
  award_amount?: number
  our_bid_amount?: number
  winning_bidder?: string
  winning_bid_amount?: number
  loss_reason?: string
  debrief_notes?: string
  lessons_learned?: string
  award_date?: string
}

export interface WinLossStats {
  total_bids: number
  wins: number
  losses: number
  pending: number
  no_bid?: number
  withdrawn?: number
  win_rate: number
  total_revenue_won: number
  total_revenue_lost: number
  average_deal_size: number
  average_margin?: number
}

export interface WinLossTrend {
  period: string
  wins: number
  losses: number
  win_rate: number
  revenue: number
}

export interface CompetitorStats {
  competitor_name: string
  encounters: number
  wins_against_us: number
  losses_against_us: number
  win_rate: number
  categories: string[]
  agencies: string[]
  average_winning_margin?: number
}

export interface AnalyticsDashboard {
  stats: WinLossStats
  trends: WinLossTrend[]
  top_competitors: CompetitorStats[]
  win_rate_by_category: Record<string, number>
  win_rate_by_agency: Record<string, number>
}

export interface AnalyticsFilters {
  start_date?: string
  end_date?: string
  agency?: string
  naics_code?: string
  min_value?: number
  max_value?: number
  status?: BidStatus
}

export interface PaginatedOutcomes {
  items: BidOutcome[]
  total: number
  page: number
  page_size: number
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/types/__tests__/analytics.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/types/analytics.ts frontend/src/types/__tests__/analytics.test.ts
git commit -m "feat(types): add TypeScript types for analytics"
```

---

## Task 7: Add Analytics API Methods to Frontend Service

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/services/__tests__/api.analytics.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../api'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      interceptors: {
        response: { use: vi.fn() },
        request: { use: vi.fn() },
      },
    }),
  },
}))

describe('Analytics API Methods', () => {
  it('has getAnalyticsOverview method', () => {
    expect(api.getAnalyticsOverview).toBeDefined()
    expect(typeof api.getAnalyticsOverview).toBe('function')
  })

  it('has createBidOutcome method', () => {
    expect(api.createBidOutcome).toBeDefined()
    expect(typeof api.createBidOutcome).toBe('function')
  })

  it('has updateBidOutcome method', () => {
    expect(api.updateBidOutcome).toBeDefined()
    expect(typeof api.updateBidOutcome).toBe('function')
  })

  it('has listBidOutcomes method', () => {
    expect(api.listBidOutcomes).toBeDefined()
    expect(typeof api.listBidOutcomes).toBe('function')
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/services/__tests__/api.analytics.test.ts`
Expected: FAIL with "api.getAnalyticsOverview is undefined"

**Step 3: Write minimal implementation**

Add to `frontend/src/services/api.ts` in the api object (around line 400):

```typescript
  // ============= Analytics =============

  getAnalyticsOverview: (filters?: {
    start_date?: string
    end_date?: string
    agency?: string
    naics_code?: string
  }) =>
    apiClient.get('/analytics/overview', { params: filters }).then(res => res.data),

  getBidOutcome: (outcomeId: number) =>
    apiClient.get(`/analytics/outcomes/${outcomeId}`).then(res => res.data),

  createBidOutcome: (data: {
    rfp_id: number
    status: string
    award_amount?: number
    our_bid_amount?: number
    winning_bidder?: string
    loss_reason?: string
  }) =>
    apiClient.post('/analytics/outcomes', data).then(res => res.data),

  updateBidOutcome: (outcomeId: number, data: {
    status?: string
    award_amount?: number
    winning_bidder?: string
    loss_reason?: string
    lessons_learned?: string
  }) =>
    apiClient.patch(`/analytics/outcomes/${outcomeId}`, data).then(res => res.data),

  listBidOutcomes: (params?: {
    page?: number
    page_size?: number
    status?: string
    agency?: string
  }) =>
    apiClient.get('/analytics/outcomes', { params }).then(res => res.data),

  getCompetitors: (limit?: number) =>
    apiClient.get('/analytics/competitors', { params: { limit } }).then(res => res.data),

  exportAnalytics: (format: 'csv' | 'pdf' = 'csv') =>
    apiClient.get(`/analytics/export/${format}`, { responseType: 'blob' }).then(res => res.data),
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/services/__tests__/api.analytics.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/services/__tests__/api.analytics.test.ts
git commit -m "feat(api): add analytics API methods to frontend service"
```

---

## Task 8: Create Analytics Dashboard Page - Stats Cards

**Files:**
- Create: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/src/pages/__tests__/WinLossAnalytics.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import WinLossAnalytics from '../WinLossAnalytics'

// Mock the API
vi.mock('@/services/api', () => ({
  api: {
    getAnalyticsOverview: vi.fn().mockResolvedValue({
      stats: {
        total_bids: 100,
        wins: 45,
        losses: 40,
        pending: 15,
        win_rate: 0.529,
        total_revenue_won: 5000000,
        total_revenue_lost: 3000000,
        average_deal_size: 111111,
      },
      trends: [],
      top_competitors: [],
      win_rate_by_category: {},
      win_rate_by_agency: {},
    }),
  },
}))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  )
}

describe('WinLossAnalytics Page', () => {
  it('renders page title', async () => {
    renderWithProviders(<WinLossAnalytics />)

    expect(await screen.findByText('Win/Loss Analytics')).toBeInTheDocument()
  })

  it('displays stats cards with data', async () => {
    renderWithProviders(<WinLossAnalytics />)

    // Should show win rate
    expect(await screen.findByText(/52\.9%/)).toBeInTheDocument()

    // Should show total bids
    expect(await screen.findByText('100')).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: FAIL with "Cannot find module '../WinLossAnalytics'"

**Step 3: Write minimal implementation**

```tsx
// frontend/src/pages/WinLossAnalytics.tsx
/**
 * Win/Loss Analytics Dashboard
 *
 * Comprehensive analytics for tracking proposal outcomes,
 * competitor analysis, and bid strategy optimization.
 */
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp,
  TrendingDown,
  Target,
  DollarSign,
  Users,
  Clock,
  Trophy,
  XCircle,
} from 'lucide-react'

import { api } from '@/services/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { AnalyticsDashboard } from '@/types/analytics'

export default function WinLossAnalytics() {
  const { data, isLoading, error } = useQuery<AnalyticsDashboard>({
    queryKey: ['analytics-overview'],
    queryFn: () => api.getAnalyticsOverview(),
    staleTime: 60 * 1000, // 1 minute
  })

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-red-500">
          Failed to load analytics data. Please try again.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Win/Loss Analytics</h1>
          <p className="text-muted-foreground">
            Track proposal outcomes and optimize your bid strategy
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Win Rate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {((data?.stats.win_rate ?? 0) * 100).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  {data?.stats.wins ?? 0} wins / {(data?.stats.wins ?? 0) + (data?.stats.losses ?? 0)} decided
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Total Bids */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Bids</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">{data?.stats.total_bids ?? 0}</div>
                <p className="text-xs text-muted-foreground">
                  {data?.stats.pending ?? 0} pending decisions
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Revenue Won */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Revenue Won</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold">
                  ${((data?.stats.total_revenue_won ?? 0) / 1000000).toFixed(1)}M
                </div>
                <p className="text-xs text-muted-foreground">
                  Avg deal: ${((data?.stats.average_deal_size ?? 0) / 1000).toFixed(0)}K
                </p>
              </>
            )}
          </CardContent>
        </Card>

        {/* Wins vs Losses */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Wins vs Losses</CardTitle>
            <Trophy className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <>
                <div className="text-2xl font-bold flex items-center gap-2">
                  <span className="text-green-600">{data?.stats.wins ?? 0}</span>
                  <span className="text-muted-foreground">/</span>
                  <span className="text-red-600">{data?.stats.losses ?? 0}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <span className="flex items-center text-green-600">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    Won
                  </span>
                  <span className="flex items-center text-red-600">
                    <TrendingDown className="h-3 w-3 mr-1" />
                    Lost
                  </span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Placeholder for charts - will be added in next task */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Win Rate Trends</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              'Chart coming in next task'
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Competitors</CardTitle>
          </CardHeader>
          <CardContent className="h-[300px] flex items-center justify-center text-muted-foreground">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : (
              'Competitor table coming in next task'
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WinLossAnalytics.tsx frontend/src/pages/__tests__/WinLossAnalytics.test.tsx
git commit -m "feat(ui): add WinLossAnalytics page with stats cards"
```

---

## Task 9: Add Navigation Menu Item and Route

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/src/components/__tests__/Layout.navigation.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Layout from '../Layout'

describe('Layout Navigation', () => {
  it('includes Win/Loss Analytics in navigation', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>Content</div>
        </Layout>
      </BrowserRouter>
    )

    expect(screen.getByText('Win/Loss')).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/components/__tests__/Layout.navigation.test.tsx`
Expected: FAIL with "Unable to find 'Win/Loss'"

**Step 3: Write minimal implementation**

Modify `frontend/src/components/Layout.tsx`:

Add import at top:

```tsx
import { BarChart3 } from 'lucide-react'
```

Add to navigation array (around line 20, after Submissions):

```tsx
  { name: 'Win/Loss', path: '/analytics', icon: BarChart3 },
```

Modify `frontend/src/App.tsx`:

Add import at top:

```tsx
import WinLossAnalytics from './pages/WinLossAnalytics'
```

Add route (inside Routes, after other routes):

```tsx
<Route path="/analytics" element={<WinLossAnalytics />} />
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/components/__tests__/Layout.navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/App.tsx frontend/src/components/__tests__/Layout.navigation.test.tsx
git commit -m "feat(nav): add Win/Loss Analytics to navigation menu"
```

---

## Task 10: Add Win Rate Trend Chart

**Files:**
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

Add to test file:

```typescript
it('renders trend chart when data has trends', async () => {
  // Update mock to include trends
  vi.mocked(api.getAnalyticsOverview).mockResolvedValueOnce({
    stats: { /* ... same as before */ },
    trends: [
      { period: '2024-01', wins: 5, losses: 3, win_rate: 0.625, revenue: 500000 },
      { period: '2024-02', wins: 4, losses: 4, win_rate: 0.5, revenue: 400000 },
    ],
    top_competitors: [],
    win_rate_by_category: {},
    win_rate_by_agency: {},
  })

  renderWithProviders(<WinLossAnalytics />)

  // Should render chart container
  expect(await screen.findByTestId('win-rate-chart')).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: FAIL with "Unable to find element with testId 'win-rate-chart'"

**Step 3: Write minimal implementation**

Replace the "Win Rate Trends" Card section in `WinLossAnalytics.tsx`:

```tsx
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'

// ... in the component, replace the placeholder Card:

<Card>
  <CardHeader>
    <CardTitle>Win Rate Trends</CardTitle>
  </CardHeader>
  <CardContent className="h-[300px]">
    {isLoading ? (
      <Skeleton className="h-full w-full" />
    ) : data?.trends && data.trends.length > 0 ? (
      <div data-testid="win-rate-chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.trends}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              domain={[0, 1]}
            />
            <Tooltip
              formatter={(value: number) => [`${(value * 100).toFixed(1)}%`, 'Win Rate']}
              labelFormatter={(label) => `Period: ${label}`}
            />
            <Line
              type="monotone"
              dataKey="win_rate"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    ) : (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        No trend data available yet
      </div>
    )}
  </CardContent>
</Card>
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WinLossAnalytics.tsx
git commit -m "feat(ui): add win rate trend chart to analytics dashboard"
```

---

## Task 11: Add Competitor Table

**Files:**
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

```typescript
it('renders competitor table with data', async () => {
  vi.mocked(api.getAnalyticsOverview).mockResolvedValueOnce({
    stats: { /* ... */ },
    trends: [],
    top_competitors: [
      {
        competitor_name: 'Acme Corp',
        encounters: 10,
        wins_against_us: 6,
        losses_against_us: 4,
        win_rate: 0.6,
        categories: ['IT'],
        agencies: ['DoD'],
      },
    ],
    win_rate_by_category: {},
    win_rate_by_agency: {},
  })

  renderWithProviders(<WinLossAnalytics />)

  expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
  expect(await screen.findByText('60%')).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace the "Top Competitors" Card:

```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

// ... replace the Top Competitors Card:

<Card>
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      <Users className="h-5 w-5" />
      Top Competitors
    </CardTitle>
  </CardHeader>
  <CardContent>
    {isLoading ? (
      <Skeleton className="h-[280px] w-full" />
    ) : data?.top_competitors && data.top_competitors.length > 0 ? (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Competitor</TableHead>
            <TableHead className="text-center">Encounters</TableHead>
            <TableHead className="text-center">Their Win Rate</TableHead>
            <TableHead>Categories</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.top_competitors.map((competitor) => (
            <TableRow key={competitor.competitor_name}>
              <TableCell className="font-medium">
                {competitor.competitor_name}
              </TableCell>
              <TableCell className="text-center">
                <span className="text-green-600">{competitor.losses_against_us}</span>
                {' / '}
                <span className="text-red-600">{competitor.wins_against_us}</span>
                {' / '}
                <span className="text-muted-foreground">{competitor.encounters}</span>
              </TableCell>
              <TableCell className="text-center">
                <div className="flex items-center gap-2">
                  <Progress
                    value={competitor.win_rate * 100}
                    className="w-16 h-2"
                  />
                  <span className={competitor.win_rate > 0.5 ? 'text-red-600' : 'text-green-600'}>
                    {(competitor.win_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {competitor.categories.slice(0, 2).map((cat) => (
                    <Badge key={cat} variant="secondary" className="text-xs">
                      {cat}
                    </Badge>
                  ))}
                  {competitor.categories.length > 2 && (
                    <Badge variant="outline" className="text-xs">
                      +{competitor.categories.length - 2}
                    </Badge>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    ) : (
      <div className="h-[280px] flex items-center justify-center text-muted-foreground">
        No competitor data yet. Record bid outcomes to track competitors.
      </div>
    )}
  </CardContent>
</Card>
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WinLossAnalytics.tsx
git commit -m "feat(ui): add competitor table to analytics dashboard"
```

---

## Task 12: Add Win Rate by Category Chart

**Files:**
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

```typescript
it('renders category breakdown chart', async () => {
  vi.mocked(api.getAnalyticsOverview).mockResolvedValueOnce({
    stats: { /* ... */ },
    trends: [],
    top_competitors: [],
    win_rate_by_category: {
      'IT Services': 0.65,
      'Construction': 0.45,
      'Consulting': 0.55,
    },
    win_rate_by_agency: {},
  })

  renderWithProviders(<WinLossAnalytics />)

  expect(await screen.findByTestId('category-chart')).toBeInTheDocument()
  expect(await screen.findByText('IT Services')).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Add a new row of charts after the existing grid:

```tsx
{/* Category and Agency Breakdown */}
<div className="grid gap-4 md:grid-cols-2">
  {/* Win Rate by Category */}
  <Card>
    <CardHeader>
      <CardTitle>Win Rate by Category</CardTitle>
    </CardHeader>
    <CardContent className="h-[300px]">
      {isLoading ? (
        <Skeleton className="h-full w-full" />
      ) : data?.win_rate_by_category && Object.keys(data.win_rate_by_category).length > 0 ? (
        <div data-testid="category-chart">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={Object.entries(data.win_rate_by_category).map(([name, rate]) => ({
                name,
                winRate: rate * 100,
              }))}
              layout="vertical"
              margin={{ left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                type="number"
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12 }}
                width={75}
              />
              <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'Win Rate']} />
              <Bar
                dataKey="winRate"
                fill="#3b82f6"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          No category data available yet
        </div>
      )}
    </CardContent>
  </Card>

  {/* Win Rate by Agency */}
  <Card>
    <CardHeader>
      <CardTitle>Win Rate by Agency</CardTitle>
    </CardHeader>
    <CardContent className="h-[300px]">
      {isLoading ? (
        <Skeleton className="h-full w-full" />
      ) : data?.win_rate_by_agency && Object.keys(data.win_rate_by_agency).length > 0 ? (
        <div data-testid="agency-chart">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={Object.entries(data.win_rate_by_agency).map(([name, rate]) => ({
                name: name.length > 20 ? name.slice(0, 17) + '...' : name,
                winRate: rate * 100,
              }))}
              layout="vertical"
              margin={{ left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                type="number"
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                tick={{ fontSize: 12 }}
                width={75}
              />
              <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'Win Rate']} />
              <Bar
                dataKey="winRate"
                fill="#10b981"
                radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-full flex items-center justify-center text-muted-foreground">
          No agency data available yet
        </div>
      )}
    </CardContent>
  </Card>
</div>
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WinLossAnalytics.tsx
git commit -m "feat(ui): add category and agency breakdown charts"
```

---

## Task 13: Add Record Outcome Dialog

**Files:**
- Create: `frontend/src/components/RecordOutcomeDialog.tsx`
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

```typescript
// frontend/src/components/__tests__/RecordOutcomeDialog.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RecordOutcomeDialog from '../RecordOutcomeDialog'

const queryClient = new QueryClient()

describe('RecordOutcomeDialog', () => {
  it('renders form fields when open', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RecordOutcomeDialog
          open={true}
          onOpenChange={() => {}}
          rfpId={1}
          rfpTitle="Test RFP"
        />
      </QueryClientProvider>
    )

    expect(screen.getByText('Record Bid Outcome')).toBeInTheDocument()
    expect(screen.getByLabelText(/Status/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Award Amount/i)).toBeInTheDocument()
  })

  it('shows competitor field when status is lost', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RecordOutcomeDialog
          open={true}
          onOpenChange={() => {}}
          rfpId={1}
          rfpTitle="Test RFP"
        />
      </QueryClientProvider>
    )

    // Select "lost" status
    fireEvent.click(screen.getByRole('combobox'))
    fireEvent.click(screen.getByText('Lost'))

    await waitFor(() => {
      expect(screen.getByLabelText(/Winning Bidder/i)).toBeInTheDocument()
    })
  })
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/components/__tests__/RecordOutcomeDialog.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

```tsx
// frontend/src/components/RecordOutcomeDialog.tsx
/**
 * Dialog for recording bid outcome (win/loss) for an RFP.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/services/api'
import type { BidStatus } from '@/types/analytics'

interface RecordOutcomeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  rfpId: number
  rfpTitle: string
}

export default function RecordOutcomeDialog({
  open,
  onOpenChange,
  rfpId,
  rfpTitle,
}: RecordOutcomeDialogProps) {
  const queryClient = useQueryClient()

  const [status, setStatus] = useState<BidStatus>('pending')
  const [awardAmount, setAwardAmount] = useState('')
  const [ourBidAmount, setOurBidAmount] = useState('')
  const [winningBidder, setWinningBidder] = useState('')
  const [lossReason, setLossReason] = useState('')
  const [lessonsLearned, setLessonsLearned] = useState('')

  const mutation = useMutation({
    mutationFn: () =>
      api.createBidOutcome({
        rfp_id: rfpId,
        status,
        award_amount: awardAmount ? parseFloat(awardAmount) : undefined,
        our_bid_amount: ourBidAmount ? parseFloat(ourBidAmount) : undefined,
        winning_bidder: status === 'lost' ? winningBidder : undefined,
        loss_reason: status === 'lost' ? lossReason : undefined,
      }),
    onSuccess: () => {
      toast.success('Outcome recorded successfully')
      queryClient.invalidateQueries({ queryKey: ['analytics-overview'] })
      onOpenChange(false)
      resetForm()
    },
    onError: (error: Error) => {
      toast.error('Failed to record outcome', { description: error.message })
    },
  })

  const resetForm = () => {
    setStatus('pending')
    setAwardAmount('')
    setOurBidAmount('')
    setWinningBidder('')
    setLossReason('')
    setLessonsLearned('')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Record Bid Outcome</DialogTitle>
          <DialogDescription className="line-clamp-2">
            {rfpTitle}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Status */}
          <div className="grid gap-2">
            <Label htmlFor="status">Status</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as BidStatus)}>
              <SelectTrigger id="status">
                <SelectValue placeholder="Select outcome" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="won">Won</SelectItem>
                <SelectItem value="lost">Lost</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="no_bid">No Bid</SelectItem>
                <SelectItem value="withdrawn">Withdrawn</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Award Amount */}
          <div className="grid gap-2">
            <Label htmlFor="awardAmount">Award Amount ($)</Label>
            <Input
              id="awardAmount"
              type="number"
              placeholder="e.g., 150000"
              value={awardAmount}
              onChange={(e) => setAwardAmount(e.target.value)}
            />
          </div>

          {/* Our Bid Amount */}
          <div className="grid gap-2">
            <Label htmlFor="ourBidAmount">Our Bid Amount ($)</Label>
            <Input
              id="ourBidAmount"
              type="number"
              placeholder="e.g., 145000"
              value={ourBidAmount}
              onChange={(e) => setOurBidAmount(e.target.value)}
            />
          </div>

          {/* Fields for Lost status */}
          {status === 'lost' && (
            <>
              <div className="grid gap-2">
                <Label htmlFor="winningBidder">Winning Bidder</Label>
                <Input
                  id="winningBidder"
                  placeholder="Company name"
                  value={winningBidder}
                  onChange={(e) => setWinningBidder(e.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="lossReason">Loss Reason</Label>
                <Textarea
                  id="lossReason"
                  placeholder="Why did we lose this bid?"
                  value={lossReason}
                  onChange={(e) => setLossReason(e.target.value)}
                  rows={3}
                />
              </div>
            </>
          )}

          {/* Lessons Learned (shown for all decided outcomes) */}
          {(status === 'won' || status === 'lost') && (
            <div className="grid gap-2">
              <Label htmlFor="lessonsLearned">Lessons Learned</Label>
              <Textarea
                id="lessonsLearned"
                placeholder="What can we learn from this outcome?"
                value={lessonsLearned}
                onChange={(e) => setLessonsLearned(e.target.value)}
                rows={3}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? 'Saving...' : 'Save Outcome'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/components/__tests__/RecordOutcomeDialog.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/RecordOutcomeDialog.tsx frontend/src/components/__tests__/RecordOutcomeDialog.test.tsx
git commit -m "feat(ui): add RecordOutcomeDialog for tracking bid outcomes"
```

---

## Task 14: Add Filters to Analytics Dashboard

**Files:**
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

```typescript
it('has date range and agency filters', async () => {
  renderWithProviders(<WinLossAnalytics />)

  expect(await screen.findByLabelText(/Date Range/i)).toBeInTheDocument()
  expect(await screen.findByLabelText(/Agency/i)).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

Add filter state and UI to `WinLossAnalytics.tsx`:

```tsx
import { useState } from 'react'
import { CalendarIcon, Filter } from 'lucide-react'
import { format, subMonths } from 'date-fns'
import { DateRange } from 'react-day-picker'

import { Calendar } from '@/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'

// ... in component:

const [dateRange, setDateRange] = useState<DateRange | undefined>({
  from: subMonths(new Date(), 6),
  to: new Date(),
})
const [agencyFilter, setAgencyFilter] = useState<string>('')

// Update query to use filters
const { data, isLoading, error } = useQuery<AnalyticsDashboard>({
  queryKey: ['analytics-overview', dateRange, agencyFilter],
  queryFn: () => api.getAnalyticsOverview({
    start_date: dateRange?.from?.toISOString(),
    end_date: dateRange?.to?.toISOString(),
    agency: agencyFilter || undefined,
  }),
  staleTime: 60 * 1000,
})

// Add after the header div, before stats cards:

{/* Filters */}
<div className="flex items-center gap-4 flex-wrap">
  {/* Date Range Picker */}
  <div className="flex items-center gap-2">
    <Label htmlFor="date-range" className="text-sm">Date Range</Label>
    <Popover>
      <PopoverTrigger asChild>
        <Button
          id="date-range"
          variant="outline"
          className={cn(
            'w-[280px] justify-start text-left font-normal',
            !dateRange && 'text-muted-foreground'
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {dateRange?.from ? (
            dateRange.to ? (
              <>
                {format(dateRange.from, 'LLL dd, y')} -{' '}
                {format(dateRange.to, 'LLL dd, y')}
              </>
            ) : (
              format(dateRange.from, 'LLL dd, y')
            )
          ) : (
            <span>Pick a date range</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          initialFocus
          mode="range"
          defaultMonth={dateRange?.from}
          selected={dateRange}
          onSelect={setDateRange}
          numberOfMonths={2}
        />
      </PopoverContent>
    </Popover>
  </div>

  {/* Agency Filter */}
  <div className="flex items-center gap-2">
    <Label htmlFor="agency-filter" className="text-sm">Agency</Label>
    <Input
      id="agency-filter"
      placeholder="Filter by agency..."
      value={agencyFilter}
      onChange={(e) => setAgencyFilter(e.target.value)}
      className="w-[200px]"
    />
  </div>

  {/* Clear Filters */}
  {(dateRange || agencyFilter) && (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        setDateRange(undefined)
        setAgencyFilter('')
      }}
    >
      <Filter className="h-4 w-4 mr-2" />
      Clear Filters
    </Button>
  )}
</div>
```

**Step 4: Run test to verify it passes**

Run: `npm run test:run -- src/pages/__tests__/WinLossAnalytics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WinLossAnalytics.tsx
git commit -m "feat(ui): add date range and agency filters to analytics"
```

---

## Task 15: Add Export Functionality

**Files:**
- Modify: `api/app/routes/analytics.py`
- Modify: `frontend/src/pages/WinLossAnalytics.tsx`

**Step 1: Write the failing test**

Backend test in `tests/test_analytics_routes.py`:

```python
def test_export_analytics_csv(client, seed_data):
    """GET /analytics/export/csv returns CSV file."""
    response = client.get("/api/v1/analytics/export/csv")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers.get("content-disposition", "")
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py::test_export_analytics_csv -v`
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `api/app/routes/analytics.py`:

```python
from fastapi.responses import StreamingResponse
import csv
import io


@router.get("/export/{format}")
async def export_analytics(
    format: str,
    db: DBDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Export analytics data in CSV or PDF format.

    Args:
        format: 'csv' or 'pdf'
    """
    if format not in ('csv', 'pdf'):
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'pdf'")

    # Get all outcomes with RFP data
    query = db.query(BidOutcome).join(RFPOpportunity)

    if start_date:
        query = query.filter(BidOutcome.created_at >= start_date)
    if end_date:
        query = query.filter(BidOutcome.created_at <= end_date)

    outcomes = query.all()

    if format == 'csv':
        return _export_csv(outcomes)
    else:
        # PDF export would require additional library (reportlab, weasyprint, etc.)
        raise HTTPException(status_code=501, detail="PDF export not yet implemented")


def _export_csv(outcomes: list[BidOutcome]) -> StreamingResponse:
    """Generate CSV export of bid outcomes."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'RFP ID',
        'RFP Title',
        'Agency',
        'Status',
        'Award Amount',
        'Our Bid Amount',
        'Winning Bidder',
        'Price Delta %',
        'Loss Reason',
        'Award Date',
        'Created At',
    ])

    # Data rows
    for outcome in outcomes:
        rfp = outcome.rfp
        writer.writerow([
            rfp.rfp_id if rfp else '',
            rfp.title if rfp else '',
            rfp.agency if rfp else '',
            outcome.status,
            outcome.award_amount or '',
            outcome.our_bid_amount or '',
            outcome.winning_bidder or '',
            f"{outcome.price_delta_percentage:.1f}" if outcome.price_delta_percentage else '',
            outcome.loss_reason or '',
            outcome.award_date.isoformat() if outcome.award_date else '',
            outcome.created_at.isoformat() if outcome.created_at else '',
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=win_loss_analytics_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        }
    )
```

Add export button to `WinLossAnalytics.tsx` header:

```tsx
import { Download } from 'lucide-react'

// In the header div, add:
<Button
  variant="outline"
  onClick={async () => {
    try {
      const blob = await api.exportAnalytics('csv')
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analytics_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
      toast.success('Export downloaded')
    } catch {
      toast.error('Export failed')
    }
  }}
>
  <Download className="h-4 w-4 mr-2" />
  Export CSV
</Button>
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_routes.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/app/routes/analytics.py frontend/src/pages/WinLossAnalytics.tsx
git commit -m "feat: add CSV export for analytics data"
```

---

## Task 16: Final Integration Test

**Files:**
- Create: `tests/test_analytics_integration.py`

**Step 1: Write the integration test**

```python
# tests/test_analytics_integration.py
"""Integration tests for the complete analytics feature."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app.models.database import Base, RFPOpportunity, BidOutcome, CompetitorProfile
from api.app.main import app
from api.app.core.database import get_db


SQLALCHEMY_TEST_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestAnalyticsWorkflow:
    """Test complete analytics workflow."""

    def test_full_workflow(self, client):
        """Test recording outcomes and viewing analytics."""
        db = TestingSessionLocal()

        # 1. Create some RFPs
        rfps = []
        for i in range(5):
            rfp = RFPOpportunity(
                rfp_id=f"WORKFLOW-{i:03d}",
                title=f"Test RFP {i}",
                agency="Test Agency" if i < 3 else "Other Agency",
                naics_code="541511" if i < 2 else "541512",
                estimated_value=100000.0 * (i + 1),
            )
            db.add(rfp)
            db.flush()
            rfps.append(rfp)
        db.commit()

        # 2. Record outcomes via API
        # Won
        response = client.post("/api/v1/analytics/outcomes", json={
            "rfp_id": rfps[0].id,
            "status": "won",
            "award_amount": 95000.0,
            "our_bid_amount": 92000.0,
        })
        assert response.status_code == 201

        # Lost to competitor
        response = client.post("/api/v1/analytics/outcomes", json={
            "rfp_id": rfps[1].id,
            "status": "lost",
            "award_amount": 180000.0,
            "our_bid_amount": 195000.0,
            "winning_bidder": "Acme Corp",
            "loss_reason": "Price too high",
        })
        assert response.status_code == 201

        # Won
        response = client.post("/api/v1/analytics/outcomes", json={
            "rfp_id": rfps[2].id,
            "status": "won",
            "award_amount": 280000.0,
            "our_bid_amount": 275000.0,
        })
        assert response.status_code == 201

        # Pending
        response = client.post("/api/v1/analytics/outcomes", json={
            "rfp_id": rfps[3].id,
            "status": "pending",
        })
        assert response.status_code == 201

        # 3. Get analytics overview
        response = client.get("/api/v1/analytics/overview")
        assert response.status_code == 200

        data = response.json()
        stats = data["stats"]

        assert stats["total_bids"] == 4
        assert stats["wins"] == 2
        assert stats["losses"] == 1
        assert stats["pending"] == 1
        assert stats["win_rate"] == pytest.approx(0.667, rel=0.01)  # 2/3
        assert stats["total_revenue_won"] == 375000.0  # 95000 + 280000

        # 4. Verify competitor was tracked
        db.close()
        db = TestingSessionLocal()
        competitor = db.query(CompetitorProfile).filter(
            CompetitorProfile.name == "Acme Corp"
        ).first()

        assert competitor is not None
        assert competitor.wins_against_us == 1
        assert competitor.total_encounters == 1

        # 5. Test filtering
        response = client.get("/api/v1/analytics/overview", params={
            "agency": "Test Agency"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_bids"] == 3  # Filtered to Test Agency only

        # 6. Test export
        response = client.get("/api/v1/analytics/export/csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        db.close()

    def test_update_outcome_flow(self, client):
        """Test updating an outcome from pending to decided."""
        db = TestingSessionLocal()

        # Create RFP and pending outcome
        rfp = RFPOpportunity(rfp_id="UPDATE-001", title="Test", agency="Test")
        db.add(rfp)
        db.flush()

        response = client.post("/api/v1/analytics/outcomes", json={
            "rfp_id": rfp.id,
            "status": "pending",
        })
        outcome_id = response.json()["id"]
        db.commit()
        db.close()

        # Update to won
        response = client.patch(f"/api/v1/analytics/outcomes/{outcome_id}", json={
            "status": "won",
            "award_amount": 150000.0,
            "lessons_learned": "Competitive pricing was key",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "won"
        assert data["lessons_learned"] == "Competitive pricing was key"
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest tests/test_analytics_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_analytics_integration.py
git commit -m "test: add integration tests for analytics feature"
```

---

## Summary

This plan creates a comprehensive win/loss analytics feature with:

### Backend (Tasks 1-5, 15)
- `BidOutcome` model for tracking proposal results
- `CompetitorProfile` model for competitive intelligence
- Pydantic schemas for validation
- REST API endpoints: overview, CRUD for outcomes, export

### Frontend (Tasks 6-14)
- TypeScript types for type safety
- API service methods
- Analytics dashboard page with:
  - Stats cards (win rate, total bids, revenue, wins/losses)
  - Win rate trend line chart
  - Competitor analysis table
  - Category and agency breakdown bar charts
  - Date range and agency filters
  - Record outcome dialog
  - CSV export

### Navigation (Task 9)
- Menu item in sidebar
- Route registration

### Testing (Tasks 1-16)
- Unit tests for models and schemas
- API endpoint tests
- Frontend component tests
- Full integration test

**Total: 16 tasks with TDD approach throughout**
