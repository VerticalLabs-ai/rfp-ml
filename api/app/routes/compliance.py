"""Compliance matrix API routes."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.database import (
    RFPOpportunity,
    ComplianceRequirement,
    RequirementStatus,
    RequirementType,
)
from app.schemas.compliance import (
    ComplianceRequirementCreate,
    ComplianceRequirementUpdate,
    ComplianceRequirementResponse,
    ComplianceRequirementList,
    BulkStatusUpdate,
    ReorderRequirements,
    ExtractionRequest,
    ExtractionResult,
    AIResponseRequest,
    AIResponseResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


def get_rfp_or_404(rfp_id: int, db: Session) -> RFPOpportunity:
    """Get RFP by ID or raise 404."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP with id {rfp_id} not found")
    return rfp


def get_requirement_or_404(requirement_id: int, db: Session) -> ComplianceRequirement:
    """Get requirement by ID or raise 404."""
    req = (
        db.query(ComplianceRequirement)
        .filter(ComplianceRequirement.id == requirement_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=404, detail=f"Requirement with id {requirement_id} not found"
        )
    return req


@router.get("/rfps/{rfp_id}/requirements", response_model=ComplianceRequirementList)
async def list_requirements(
    rfp_id: int,
    status_filter: Optional[RequirementStatus] = None,
    type_filter: Optional[RequirementType] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all requirements for an RFP with optional filtering."""
    get_rfp_or_404(rfp_id, db)

    query = db.query(ComplianceRequirement).filter(
        ComplianceRequirement.rfp_id == rfp_id
    )

    if status_filter:
        query = query.filter(ComplianceRequirement.status == status_filter)
    if type_filter:
        query = query.filter(ComplianceRequirement.requirement_type == type_filter)
    if search:
        query = query.filter(ComplianceRequirement.requirement_text.ilike(f"%{search}%"))

    requirements = query.order_by(ComplianceRequirement.order_index).all()

    # Calculate summary stats
    total = len(requirements)
    completed = sum(1 for r in requirements if r.status == RequirementStatus.COMPLETE)
    in_progress = sum(
        1 for r in requirements if r.status == RequirementStatus.IN_PROGRESS
    )
    not_started = sum(
        1 for r in requirements if r.status == RequirementStatus.NOT_STARTED
    )
    compliance_rate = (completed / total * 100) if total > 0 else 0.0

    return ComplianceRequirementList(
        requirements=requirements,
        total=total,
        completed=completed,
        in_progress=in_progress,
        not_started=not_started,
        compliance_rate=compliance_rate,
    )


@router.post(
    "/rfps/{rfp_id}/requirements",
    response_model=ComplianceRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement(
    rfp_id: int,
    requirement: ComplianceRequirementCreate,
    db: Session = Depends(get_db),
):
    """Manually add a requirement to an RFP."""
    get_rfp_or_404(rfp_id, db)

    # Get next order index
    max_order = (
        db.query(func.max(ComplianceRequirement.order_index))
        .filter(ComplianceRequirement.rfp_id == rfp_id)
        .scalar()
        or -1
    )

    db_requirement = ComplianceRequirement(
        rfp_id=rfp_id,
        requirement_id=requirement.requirement_id,
        requirement_text=requirement.requirement_text,
        source_document=requirement.source_document,
        source_section=requirement.source_section,
        source_page=requirement.source_page,
        requirement_type=requirement.requirement_type,
        is_mandatory=requirement.is_mandatory,
        status=RequirementStatus.NOT_STARTED,
        order_index=max_order + 1,
    )

    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)

    logger.info(f"Created requirement {db_requirement.requirement_id} for RFP {rfp_id}")
    return db_requirement


@router.put(
    "/requirements/{requirement_id}", response_model=ComplianceRequirementResponse
)
async def update_requirement(
    requirement_id: int,
    update: ComplianceRequirementUpdate,
    db: Session = Depends(get_db),
):
    """Update a requirement's status, response, or other fields."""
    requirement = get_requirement_or_404(requirement_id, db)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(requirement, field, value)

    db.commit()
    db.refresh(requirement)

    logger.info(f"Updated requirement {requirement_id}: {list(update_data.keys())}")
    return requirement


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
):
    """Delete a requirement."""
    requirement = get_requirement_or_404(requirement_id, db)
    db.delete(requirement)
    db.commit()
    logger.info(f"Deleted requirement {requirement_id}")


@router.put("/rfps/{rfp_id}/requirements/bulk-status")
async def bulk_update_status(
    rfp_id: int,
    update: BulkStatusUpdate,
    db: Session = Depends(get_db),
):
    """Bulk update status for multiple requirements."""
    get_rfp_or_404(rfp_id, db)

    updated = (
        db.query(ComplianceRequirement)
        .filter(
            ComplianceRequirement.id.in_(update.requirement_ids),
            ComplianceRequirement.rfp_id == rfp_id,
        )
        .update({"status": update.status}, synchronize_session=False)
    )

    db.commit()

    logger.info(f"Bulk updated {updated} requirements to status {update.status}")
    return {"updated_count": updated}


@router.put("/rfps/{rfp_id}/requirements/reorder")
async def reorder_requirements(
    rfp_id: int,
    reorder: ReorderRequirements,
    db: Session = Depends(get_db),
):
    """Reorder requirements (for drag-and-drop)."""
    get_rfp_or_404(rfp_id, db)

    for index, req_id in enumerate(reorder.requirement_ids):
        db.query(ComplianceRequirement).filter(
            ComplianceRequirement.id == req_id, ComplianceRequirement.rfp_id == rfp_id
        ).update({"order_index": index}, synchronize_session=False)

    db.commit()

    logger.info(
        f"Reordered {len(reorder.requirement_ids)} requirements for RFP {rfp_id}"
    )
    return {"reordered_count": len(reorder.requirement_ids)}


@router.post("/rfps/{rfp_id}/extract-requirements", response_model=ExtractionResult)
async def extract_requirements(
    rfp_id: int,
    request: Optional[ExtractionRequest] = None,
    db: Session = Depends(get_db),
):
    """Extract requirements from RFP description and Q&A using LLM or rule-based extraction."""
    rfp = get_rfp_or_404(rfp_id, db)

    # Combine RFP description and Q&A content
    text_parts = []
    if rfp.description:
        text_parts.append(f"[RFP Description]\n{rfp.description}")

    # Include Q&A content if available
    if rfp.qa_items:
        qa_text = "\n".join(
            [
                f"Q: {qa.question_text}\nA: {qa.answer_text or 'No answer'}"
                for qa in rfp.qa_items
            ]
        )
        text_parts.append(f"[Q&A]\n{qa_text}")

    combined_text = "\n\n".join(text_parts)

    if not combined_text.strip():
        raise HTTPException(
            status_code=400, detail="No text content found in RFP for extraction"
        )

    # Initialize compliance generator
    try:
        from src.compliance.compliance_matrix import ComplianceMatrixGenerator
        from src.rag.chroma_rag_engine import get_rag_engine

        rag_engine = get_rag_engine()
    except Exception:
        rag_engine = None

    try:
        generator = ComplianceMatrixGenerator(rag_engine=rag_engine)
    except Exception as e:
        logger.warning(f"Failed to initialize ComplianceMatrixGenerator: {e}")
        # Fallback to simple rule-based extraction without RAG
        generator = None

    # Extract requirements
    use_llm = request.use_llm if request else True
    if generator:
        if use_llm:
            extracted = generator.extract_requirements_llm(combined_text)
        else:
            extracted = generator.extract_requirements_rule_based(combined_text)
    else:
        # Simple fallback extraction
        extracted = _simple_requirement_extraction(combined_text)

    # Get current max order index
    max_order = (
        db.query(func.max(ComplianceRequirement.order_index))
        .filter(ComplianceRequirement.rfp_id == rfp_id)
        .scalar()
        or -1
    )

    # Create requirement records
    created_requirements = []
    source_docs = ["RFP Description"]
    if rfp.qa_items:
        source_docs.append("Q&A Responses")

    for idx, req_data in enumerate(extracted):
        # Map category to requirement type
        type_mapping = {
            "mandatory": RequirementType.MANDATORY,
            "technical": RequirementType.TECHNICAL,
            "financial": RequirementType.ADMINISTRATIVE,
            "qualification": RequirementType.EVALUATION,
            "performance": RequirementType.PERFORMANCE,
            "security": RequirementType.MANDATORY,
            "legal": RequirementType.MANDATORY,
            "administrative": RequirementType.ADMINISTRATIVE,
        }
        req_type = type_mapping.get(
            req_data.get("category", "").lower(), RequirementType.MANDATORY
        )

        db_req = ComplianceRequirement(
            rfp_id=rfp_id,
            requirement_id=req_data.get("requirement_id", f"EXT.{idx + 1}"),
            requirement_text=req_data.get("text", req_data.get("requirement_text", "")),
            source_document=", ".join(source_docs),
            requirement_type=req_type,
            is_mandatory=req_data.get("mandatory", True),
            status=RequirementStatus.NOT_STARTED,
            order_index=max_order + idx + 1,
        )
        db.add(db_req)
        created_requirements.append(db_req)

    db.commit()

    # Refresh to get IDs
    for req in created_requirements:
        db.refresh(req)

    logger.info(
        f"Extracted {len(created_requirements)} requirements for RFP {rfp_id}"
    )

    return ExtractionResult(
        extracted_count=len(created_requirements),
        requirements=created_requirements,
        source_documents=source_docs,
    )


def _simple_requirement_extraction(text: str) -> list[dict]:
    """Simple fallback extraction using pattern matching."""
    import re

    requirements = []
    patterns = [
        r"(?:shall|must|will|required to)\s+([^.]+\.)",
        r"(?:the contractor|the vendor|offeror)\s+(?:shall|must|will)\s+([^.]+\.)",
    ]

    seen = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            text_clean = match.strip()
            if text_clean and text_clean not in seen and len(text_clean) > 20:
                seen.add(text_clean)
                requirements.append(
                    {
                        "text": text_clean,
                        "category": "mandatory",
                        "mandatory": True,
                    }
                )

    return requirements[:50]  # Limit to 50 requirements


@router.post(
    "/requirements/{requirement_id}/ai-response", response_model=AIResponseResult
)
async def generate_ai_response(
    requirement_id: int,
    request: Optional[AIResponseRequest] = None,
    db: Session = Depends(get_db),
):
    """Generate an AI-assisted response for a requirement."""
    requirement = get_requirement_or_404(requirement_id, db)
    rfp = (
        db.query(RFPOpportunity)
        .filter(RFPOpportunity.id == requirement.rfp_id)
        .first()
    )

    # Get RAG context if requested
    supporting_evidence = []
    rag_context = ""

    include_rag = request.include_rag_context if request else True
    if include_rag:
        try:
            from src.rag.chroma_rag_engine import get_rag_engine

            rag_engine = get_rag_engine()
            results = rag_engine.retrieve(requirement.requirement_text, top_k=3)
            supporting_evidence = [r.get("content", "")[:200] for r in results]
            rag_context = "\n".join([f"- {r.get('content', '')}" for r in results])
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

    # Build prompt
    prompt = f"""Generate a compliance response for the following RFP requirement.

RFP: {rfp.title if rfp else 'Unknown'}
Agency: {rfp.agency if rfp else 'Unknown'}

Requirement ID: {requirement.requirement_id}
Requirement Type: {requirement.requirement_type.value}
Requirement Text: {requirement.requirement_text}

{f'Relevant Context from Past Proposals:{chr(10)}{rag_context}' if rag_context else ''}

Write a professional compliance response that:
1. Directly addresses the requirement
2. Demonstrates capability to meet the requirement
3. Provides specific examples or evidence where possible
4. Uses confident, professional language

Response:"""

    # Generate response using streaming service
    from app.services.streaming import StreamingService

    streaming_service = StreamingService()

    try:
        response_text = ""
        async for chunk in streaming_service.stream_llm_response(
            prompt=prompt,
            system_message="You are an expert government proposal writer. Generate concise, compliant responses.",
            task_type="compliance_response",
            max_tokens=1000,
        ):
            response_text += chunk
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AI response")

    # Calculate confidence based on RAG match quality
    confidence = 0.85 if supporting_evidence else 0.70

    return AIResponseResult(
        response_text=response_text.strip(),
        confidence_score=confidence,
        supporting_evidence=supporting_evidence,
    )
