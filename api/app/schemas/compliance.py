"""Pydantic schemas for compliance requirements."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.database import RequirementType, RequirementStatus


class ComplianceRequirementBase(BaseModel):
    """Base schema for compliance requirement."""

    requirement_id: str = Field(..., description="Requirement identifier (e.g., L.1.2)")
    requirement_text: str = Field(..., description="Full requirement text")
    source_document: Optional[str] = Field(None, description="Source document name")
    source_section: Optional[str] = Field(None, description="Section reference")
    source_page: Optional[int] = Field(None, description="Page number")
    requirement_type: RequirementType = Field(default=RequirementType.MANDATORY)
    is_mandatory: bool = Field(default=True)


class ComplianceRequirementCreate(ComplianceRequirementBase):
    """Schema for creating a compliance requirement."""

    pass


class ComplianceRequirementUpdate(BaseModel):
    """Schema for updating a compliance requirement."""

    requirement_text: Optional[str] = None
    source_document: Optional[str] = None
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    requirement_type: Optional[RequirementType] = None
    is_mandatory: Optional[bool] = None
    status: Optional[RequirementStatus] = None
    response_text: Optional[str] = None
    compliance_indicator: Optional[str] = None
    confidence_score: Optional[float] = None
    order_index: Optional[int] = None
    assigned_to: Optional[str] = None


class ComplianceRequirementResponse(ComplianceRequirementBase):
    """Schema for compliance requirement response."""

    id: int
    rfp_id: int
    status: RequirementStatus
    response_text: Optional[str]
    compliance_indicator: Optional[str]
    confidence_score: Optional[float]
    order_index: int
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceRequirementList(BaseModel):
    """Schema for list of compliance requirements with summary."""

    requirements: List[ComplianceRequirementResponse]
    total: int
    completed: int
    in_progress: int
    not_started: int
    compliance_rate: float = Field(..., description="Percentage of completed requirements")


class BulkStatusUpdate(BaseModel):
    """Schema for bulk status update."""

    requirement_ids: List[int]
    status: RequirementStatus


class ReorderRequirements(BaseModel):
    """Schema for reordering requirements."""

    requirement_ids: List[int] = Field(..., description="Ordered list of requirement IDs")


class AIResponseRequest(BaseModel):
    """Schema for AI response generation request."""

    requirement_id: int
    include_rag_context: bool = Field(default=True)


class AIResponseResult(BaseModel):
    """Schema for AI-generated response."""

    response_text: str
    confidence_score: float
    supporting_evidence: List[str]


class ExtractionRequest(BaseModel):
    """Schema for extraction request."""

    document_ids: Optional[List[int]] = Field(
        None, description="Specific document IDs to extract from"
    )
    use_llm: bool = Field(default=True, description="Use LLM for enhanced extraction")


class ExtractionResult(BaseModel):
    """Schema for extraction result."""

    extracted_count: int
    requirements: List[ComplianceRequirementResponse]
    source_documents: List[str]
