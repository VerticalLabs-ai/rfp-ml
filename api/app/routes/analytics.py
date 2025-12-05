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
