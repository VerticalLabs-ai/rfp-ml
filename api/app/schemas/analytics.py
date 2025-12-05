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
    award_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
