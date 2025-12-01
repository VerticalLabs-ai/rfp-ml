"""
Proposal Copilot API endpoints.

Provides AI-assisted proposal writing with section-by-section generation,
compliance checking, and draft management.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from app.dependencies import DBDep, RFPDep
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class SectionContent(BaseModel):
    """Content for a single proposal section."""
    content: str = ""


class DraftSaveRequest(BaseModel):
    """Request to save a proposal draft."""
    sections: dict[str, str] = Field(..., description="Section ID to content mapping")


class ComplianceCheckRequest(BaseModel):
    """Request to check compliance of proposal sections."""
    sections: dict[str, SectionContent] = Field(..., description="Section ID to content mapping")


class ComplianceIssue(BaseModel):
    """A compliance issue found during checking."""
    severity: str  # "error", "warning", "info"
    message: str
    section: str | None = None
    requirement: str | None = None


class ComplianceCheckResponse(BaseModel):
    """Response from compliance check."""
    score: float = Field(..., description="Overall compliance score (0-100)")
    issues: list[ComplianceIssue] = Field(default_factory=list)
    section_scores: dict[str, float] = Field(default_factory=dict)


class DraftResponse(BaseModel):
    """Response from draft operations."""
    rfp_id: str
    saved_at: str
    sections: dict[str, str]
    status: str


@router.post("/{rfp_id}/draft", response_model=DraftResponse)
async def save_draft(rfp: RFPDep, request: DraftSaveRequest, db: DBDep):
    """
    Save a proposal draft for an RFP.

    Saves the current state of all proposal sections to the database.
    """
    from app.models.database import BidDocument
    import uuid

    try:
        # Check if bid document exists
        existing = db.query(BidDocument).filter(
            BidDocument.rfp_id == rfp.id
        ).first()

        if existing:
            # Update existing
            existing.content_json = {"sections": request.sections}
            existing.updated_at = datetime.now(timezone.utc)
            existing.status = "draft"
        else:
            # Create new
            bid_doc = BidDocument(
                rfp_id=rfp.id,
                document_id=f"bid-{uuid.uuid4().hex[:8]}",
                content_json={"sections": request.sections},
                status="draft",
            )
            db.add(bid_doc)

        db.commit()

        return DraftResponse(
            rfp_id=rfp.rfp_id,
            saved_at=datetime.now(timezone.utc).isoformat(),
            sections=request.sections,
            status="draft",
        )

    except Exception as e:
        logger.exception(f"Failed to save draft for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Failed to save draft") from e


@router.get("/{rfp_id}/draft", response_model=DraftResponse)
async def get_draft(rfp: RFPDep, db: DBDep):
    """
    Get the current draft for an RFP.
    """
    from app.models.database import BidDocument

    bid_doc = db.query(BidDocument).filter(
        BidDocument.rfp_id == rfp.id
    ).first()

    if not bid_doc or not bid_doc.content_json:
        return DraftResponse(
            rfp_id=rfp.rfp_id,
            saved_at=datetime.now(timezone.utc).isoformat(),
            sections={},
            status="empty",
        )

    return DraftResponse(
        rfp_id=rfp.rfp_id,
        saved_at=bid_doc.updated_at.isoformat() if bid_doc.updated_at else datetime.now(timezone.utc).isoformat(),
        sections=bid_doc.content_json.get("sections", {}),
        status=bid_doc.status or "draft",
    )


@router.post("/{rfp_id}/compliance-check", response_model=ComplianceCheckResponse)
async def check_compliance(rfp: RFPDep, request: ComplianceCheckRequest):
    """
    Check proposal compliance against RFP requirements.

    Analyzes each section for:
    - Required content coverage
    - Missing mandatory elements
    - Word count requirements
    - Regulatory compliance
    """
    try:
        issues: list[ComplianceIssue] = []
        section_scores: dict[str, float] = {}

        # Required sections and their minimum word counts
        required_sections = {
            "executive_summary": {"min_words": 200, "required": True},
            "technical_approach": {"min_words": 500, "required": True},
            "management_approach": {"min_words": 300, "required": True},
            "past_performance": {"min_words": 200, "required": True},
            "compliance_matrix": {"min_words": 100, "required": True},
            "staffing_plan": {"min_words": 150, "required": False},
            "quality_assurance": {"min_words": 100, "required": False},
            "risk_mitigation": {"min_words": 100, "required": False},
        }

        # Key phrases that should be addressed
        key_phrases_by_section = {
            "executive_summary": ["value proposition", "qualifications", "approach", "benefits"],
            "technical_approach": ["methodology", "solution", "technology", "implementation"],
            "management_approach": ["project management", "communication", "reporting", "governance"],
            "past_performance": ["contract", "client", "results", "similar"],
            "compliance_matrix": ["requirement", "compliance", "response"],
        }

        total_score = 0
        section_count = 0

        for section_id, config in required_sections.items():
            section_data = request.sections.get(section_id)
            content = section_data.content if section_data else ""
            word_count = len(content.split()) if content else 0

            score = 0

            # Check if required section is empty
            if config["required"] and word_count == 0:
                issues.append(ComplianceIssue(
                    severity="error",
                    message=f"Required section '{section_id.replace('_', ' ').title()}' is empty",
                    section=section_id,
                ))
            elif word_count > 0:
                # Word count scoring
                min_words = config["min_words"]
                if word_count >= min_words:
                    score += 50
                elif word_count >= min_words * 0.5:
                    score += 25
                    issues.append(ComplianceIssue(
                        severity="warning",
                        message=f"Section '{section_id.replace('_', ' ').title()}' is below recommended word count ({word_count}/{min_words} words)",
                        section=section_id,
                    ))
                else:
                    issues.append(ComplianceIssue(
                        severity="warning",
                        message=f"Section '{section_id.replace('_', ' ').title()}' needs more content ({word_count}/{min_words} words)",
                        section=section_id,
                    ))

                # Key phrase coverage
                key_phrases = key_phrases_by_section.get(section_id, [])
                content_lower = content.lower()
                phrases_found = sum(1 for phrase in key_phrases if phrase in content_lower)
                if key_phrases:
                    phrase_coverage = phrases_found / len(key_phrases)
                    score += phrase_coverage * 50

                    missing_phrases = [p for p in key_phrases if p not in content_lower]
                    if missing_phrases and phrase_coverage < 0.75:
                        issues.append(ComplianceIssue(
                            severity="info",
                            message=f"Consider addressing: {', '.join(missing_phrases[:3])}",
                            section=section_id,
                        ))

            section_scores[section_id] = round(score, 1)
            if config["required"]:
                total_score += score
                section_count += 1

        # Calculate overall score
        overall_score = round(total_score / section_count, 1) if section_count > 0 else 0

        # Add RFP-specific checks
        if rfp.naics_code and overall_score > 0:
            # Check if NAICS is mentioned
            all_content = " ".join([
                s.content for s in request.sections.values() if s.content
            ]).lower()

            if rfp.naics_code not in all_content:
                issues.append(ComplianceIssue(
                    severity="info",
                    message=f"Consider referencing NAICS code {rfp.naics_code} in your proposal",
                ))

        return ComplianceCheckResponse(
            score=overall_score,
            issues=issues,
            section_scores=section_scores,
        )

    except Exception as e:
        logger.exception(f"Compliance check failed for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Compliance check failed") from e


@router.get("/{rfp_id}/suggestions")
async def get_section_suggestions(
    rfp: RFPDep,
    section: str,
):
    """
    Get AI suggestions for improving a proposal section.

    Returns contextual suggestions based on the RFP requirements
    and the current section.
    """
    suggestions_map = {
        "executive_summary": [
            "Open with a compelling value proposition that addresses the agency's core need",
            "Highlight 2-3 key differentiators that set your company apart",
            "Include a brief overview of your approach and methodology",
            "Mention relevant past performance with similar agencies",
            "Close with a strong compliance statement",
        ],
        "technical_approach": [
            "Start with your understanding of the technical requirements",
            "Describe your methodology framework (Agile, Waterfall, etc.)",
            "Include specific technologies and tools you'll use",
            "Address how you'll handle technical risks",
            "Provide a high-level architecture or solution diagram reference",
        ],
        "management_approach": [
            "Define clear roles and responsibilities",
            "Describe your communication and reporting cadence",
            "Include your quality management processes",
            "Address change management procedures",
            "Mention relevant certifications (ISO, CMMI, etc.)",
        ],
        "past_performance": [
            "Focus on contracts similar in size and scope",
            "Include specific metrics and outcomes",
            "Highlight work with similar agencies or in the same industry",
            "Address any lessons learned that apply",
            "Provide contact information for references",
        ],
        "compliance_matrix": [
            "Map each RFP requirement to a response",
            "Use clear compliance language (Compliant, Partial, Exception)",
            "Reference proposal sections for detailed responses",
            "Highlight where you exceed requirements",
            "Note any clarifications or assumptions",
        ],
    }

    default_suggestions = [
        "Review the RFP requirements carefully before writing",
        "Use clear, concise language",
        "Include specific examples and evidence",
        "Address evaluation criteria directly",
        "Proofread for consistency and accuracy",
    ]

    return {
        "rfp_id": rfp.rfp_id,
        "section": section,
        "suggestions": suggestions_map.get(section, default_suggestions),
    }


@router.post("/{rfp_id}/generate-outline")
async def generate_proposal_outline(rfp: RFPDep):
    """
    Generate a proposal outline based on the RFP.

    Creates section headers and key points to address.
    """
    try:
        from src.config.llm_adapter import create_llm_interface

        llm = create_llm_interface()

        prompt = f"""Generate a proposal outline for the following RFP:

Title: {rfp.title}
Agency: {rfp.agency or 'Not specified'}
Description: {rfp.description or 'Not available'}
NAICS Code: {rfp.naics_code or 'Not specified'}
Category: {rfp.category or 'General'}

Create a structured outline with:
1. Executive Summary key points
2. Technical Approach sections
3. Management Approach elements
4. Past Performance focus areas
5. Compliance considerations

Format as a clear, actionable outline."""

        result = llm.generate_text(prompt, use_case="outline")
        outline = result.get("content", result.get("text", ""))

        return {
            "rfp_id": rfp.rfp_id,
            "outline": outline,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to generate outline for RFP {rfp.rfp_id}")
        raise HTTPException(status_code=500, detail="Outline generation failed") from e
