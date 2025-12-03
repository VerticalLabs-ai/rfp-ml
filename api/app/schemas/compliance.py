"""Pydantic schemas for compliance requirements."""
from datetime import datetime

from app.models.database import RequirementStatus, RequirementType
from pydantic import BaseModel, Field


class ComplianceRequirementBase(BaseModel):
    """Base schema for compliance requirement."""

    requirement_id: str = Field(..., description="Requirement identifier (e.g., L.1.2)")
    requirement_text: str = Field(..., description="Full requirement text")
    source_document: str | None = Field(None, description="Source document name")
    source_section: str | None = Field(None, description="Section reference")
    source_page: int | None = Field(None, description="Page number")
    requirement_type: RequirementType = Field(default=RequirementType.MANDATORY)
    is_mandatory: bool = Field(default=True)


class ComplianceRequirementCreate(ComplianceRequirementBase):
    """Schema for creating a compliance requirement."""

    pass


class ComplianceRequirementUpdate(BaseModel):
    """Schema for updating a compliance requirement."""

    requirement_text: str | None = None
    source_document: str | None = None
    source_section: str | None = None
    source_page: int | None = None
    requirement_type: RequirementType | None = None
    is_mandatory: bool | None = None
    status: RequirementStatus | None = None
    response_text: str | None = None
    compliance_indicator: str | None = None
    confidence_score: float | None = None
    order_index: int | None = None
    assigned_to: str | None = None


class ComplianceRequirementResponse(ComplianceRequirementBase):
    """Schema for compliance requirement response."""

    id: int
    rfp_id: int
    status: RequirementStatus
    response_text: str | None
    compliance_indicator: str | None
    confidence_score: float | None
    order_index: int
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceRequirementList(BaseModel):
    """Schema for list of compliance requirements with summary."""

    requirements: list[ComplianceRequirementResponse]
    total: int
    completed: int
    in_progress: int
    not_started: int
    compliance_rate: float = Field(..., description="Percentage of completed requirements")


class BulkStatusUpdate(BaseModel):
    """Schema for bulk status update."""

    requirement_ids: list[int]
    status: RequirementStatus


class ReorderRequirements(BaseModel):
    """Schema for reordering requirements."""

    requirement_ids: list[int] = Field(..., description="Ordered list of requirement IDs")


class AIResponseRequest(BaseModel):
    """Schema for AI response generation request."""

    requirement_id: int
    include_rag_context: bool = Field(default=True)


class AIResponseResult(BaseModel):
    """Schema for AI-generated response."""

    response_text: str
    confidence_score: float
    supporting_evidence: list[str]


class ExtractionRequest(BaseModel):
    """Schema for extraction request."""

    document_ids: list[int] | None = Field(
        None, description="Specific document IDs to extract from"
    )
    use_llm: bool = Field(default=True, description="Use LLM for enhanced extraction")


class ExtractionResult(BaseModel):
    """Schema for extraction result."""

    extracted_count: int
    requirements: list[ComplianceRequirementResponse]
    source_documents: list[str]
