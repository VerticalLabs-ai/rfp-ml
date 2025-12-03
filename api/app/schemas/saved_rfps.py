"""Pydantic schemas for saved RFPs."""
from datetime import datetime

from pydantic import BaseModel, Field


class SavedRfpBase(BaseModel):
    """Base schema for saved RFP."""

    notes: str | None = Field(None, description="User notes about this RFP")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    folder: str | None = Field(None, description="Folder/category for organization")


class SavedRfpCreate(SavedRfpBase):
    """Schema for saving an RFP."""

    rfp_id: int = Field(..., description="ID of the RFP to save")


class SavedRfpUpdate(BaseModel):
    """Schema for updating a saved RFP."""

    notes: str | None = None
    tags: list[str] | None = None
    folder: str | None = None


class SavedRfpResponse(SavedRfpBase):
    """Schema for saved RFP response."""

    id: int
    rfp_id: int
    user_id: str
    saved_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedRfpWithRfp(SavedRfpResponse):
    """Schema for saved RFP with full RFP details."""

    rfp_title: str
    rfp_agency: str | None
    rfp_deadline: datetime | None
    rfp_stage: str | None
    rfp_triage_score: float | None


class SavedRfpList(BaseModel):
    """Schema for list of saved RFPs with summary."""

    saved_rfps: list[SavedRfpWithRfp]
    total: int
    tags_summary: dict[str, int] = Field(default_factory=dict, description="Count per tag")
    folders_summary: dict[str, int] = Field(default_factory=dict, description="Count per folder")


class TagsList(BaseModel):
    """Schema for user's tags."""

    tags: list[str]
    counts: dict[str, int]


class BulkSaveRequest(BaseModel):
    """Schema for bulk saving multiple RFPs."""

    rfp_ids: list[int]
    tags: list[str] = Field(default_factory=list)
    folder: str | None = None


class BulkDeleteRequest(BaseModel):
    """Schema for bulk deleting saved RFPs."""

    saved_rfp_ids: list[int]
