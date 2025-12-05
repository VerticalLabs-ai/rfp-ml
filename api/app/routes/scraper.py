"""
RFP Scraper API endpoints for importing RFPs from external portals.
"""

import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

from app.dependencies import DBDep
from app.models.database import PipelineStage, RFPDocument, RFPOpportunity, RFPQandA
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas
class ScrapeRequest(BaseModel):
    url: str
    company_profile_id: int | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is well-formed and uses HTTPS."""
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("Invalid URL: missing domain")
        # Basic sanitization - remove any control characters
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        return v


class ScrapeResponse(BaseModel):
    rfp_id: str
    status: str
    title: str
    documents_count: int
    qa_count: int
    message: str | None = None


class RefreshResponse(BaseModel):
    rfp_id: str
    has_changes: bool
    new_qa_count: int
    new_document_count: int
    metadata_changed: bool
    message: str


class RFPDocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str | None
    file_size: int | None
    document_type: str | None
    source_url: str | None
    downloaded_at: datetime | None
    download_status: str  # "completed", "pending", or "failed"

    class Config:
        from_attributes = True


class RFPQandAResponse(BaseModel):
    id: int
    question_number: str | None
    question_text: str
    answer_text: str | None
    asked_date: datetime | None
    answered_date: datetime | None
    category: str | None
    key_insights: list[str]
    is_new: bool

    class Config:
        from_attributes = True


def get_scraper(url: str):
    """
    Get the appropriate scraper for a URL.

    Priority order:
    1. Platform-specific scrapers (BeaconBid, SAM.gov) - use specialized extraction
    2. Generic web scraper - fallback for any HTTP(S) URL using AI extraction
    """
    from src.agents.scrapers import BeaconBidScraper, GenericWebScraper, SAMGovScraper

    # Platform-specific scrapers in priority order
    scrapers = [
        BeaconBidScraper(),
        SAMGovScraper(),
    ]

    for scraper in scrapers:
        if scraper.is_valid_url(url):
            return scraper

    # Fallback: GenericWebScraper accepts any HTTP(S) URL
    generic = GenericWebScraper()
    if generic.is_valid_url(url):
        return generic

    return None


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_rfp(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: DBDep = ...,
):
    """
    Scrape an RFP from an external portal URL.

    Supports:
    - BeaconBid (beaconbid.com)

    Returns the created RFP with scraped metadata, documents, and Q&A.
    """
    url = request.url

    # Find appropriate scraper
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(
            status_code=400,
            detail="Unsupported URL. Currently supported portals: BeaconBid",
        )

    try:
        # Scrape the RFP
        logger.info("Starting scrape of URL: %s", url)
        scraped_rfp = await scraper.scrape(url)

        # Generate unique RFP ID
        rfp_id = f"RFP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"

        # Check for existing RFP with same URL
        existing = (
            db.query(RFPOpportunity).filter(RFPOpportunity.source_url == url).first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"RFP already exists with ID: {existing.rfp_id}. Use refresh endpoint to update.",
            )

        # Create RFP in database
        rfp = RFPOpportunity(
            rfp_id=rfp_id,
            solicitation_number=scraped_rfp.solicitation_number,
            title=scraped_rfp.title,
            description=scraped_rfp.description,
            agency=scraped_rfp.agency,
            office=scraped_rfp.office,
            naics_code=scraped_rfp.naics_code,
            category=scraped_rfp.category,
            posted_date=scraped_rfp.posted_date,
            response_deadline=scraped_rfp.response_deadline,
            award_amount=scraped_rfp.award_amount,
            estimated_value=scraped_rfp.estimated_value,
            current_stage=PipelineStage.DISCOVERED,
            source_url=url,
            source_platform=scraped_rfp.source_platform,
            last_scraped_at=datetime.now(timezone.utc),
            scrape_checksum=scraped_rfp.scrape_checksum,
            company_profile_id=request.company_profile_id,
            rfp_metadata=scraped_rfp.raw_data,
        )
        db.add(rfp)
        db.commit()
        db.refresh(rfp)

        # Download documents in background
        background_tasks.add_task(
            _download_and_save_documents, scraper, scraped_rfp, rfp.id, rfp_id
        )

        # Save Q&A items
        for qa in scraped_rfp.qa_items:
            qa_record = RFPQandA(
                rfp_id=rfp.id,
                question_number=qa.question_number,
                question_text=qa.question_text,
                answer_text=qa.answer_text,
                asked_date=qa.asked_date,
                answered_date=qa.answered_date,
                is_new=True,
            )
            db.add(qa_record)

        db.commit()

        # Broadcast RFP created to connected clients
        from app.websockets.websocket_router import broadcast_rfp_update

        await broadcast_rfp_update(
            rfp_id,
            "rfp_scraped",
            {
                "title": scraped_rfp.title,
                "documents_count": len(scraped_rfp.documents),
                "qa_count": len(scraped_rfp.qa_items),
            },
        )

        return ScrapeResponse(
            rfp_id=rfp_id,
            status="success",
            title=scraped_rfp.title,
            documents_count=len(scraped_rfp.documents),
            qa_count=len(scraped_rfp.qa_items),
            message="RFP scraped successfully. Documents are downloading in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error scraping RFP: %s", e)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e!s}") from e


async def _download_and_save_documents(
    scraper, scraped_rfp, rfp_db_id: int, rfp_id: str
) -> None:
    """Background task to download documents and save to database."""
    from app.core.database import SessionLocal

    try:
        # First, save all document metadata so they appear in the UI
        with SessionLocal() as session:
            for doc in scraped_rfp.documents:
                # Check if document already exists
                existing = (
                    session.query(RFPDocument)
                    .filter(
                        RFPDocument.rfp_id == rfp_db_id,
                        RFPDocument.filename == doc.filename,
                    )
                    .first()
                )

                if not existing:
                    doc_record = RFPDocument(
                        rfp_id=rfp_db_id,
                        filename=doc.filename,
                        file_type=doc.file_type,
                        document_type=doc.document_type,
                        source_url=doc.source_url,
                        # file_path, file_size, checksum will be set after download
                    )
                    session.add(doc_record)

            session.commit()
            logger.info(
                "Saved %d document records for RFP %s",
                len(scraped_rfp.documents),
                rfp_id,
            )

        # Then attempt to download the files
        downloaded_docs = await scraper.download_documents(scraped_rfp, rfp_id)

        # Update records with download info
        with SessionLocal() as session:
            for doc in downloaded_docs:
                existing = (
                    session.query(RFPDocument)
                    .filter(
                        RFPDocument.rfp_id == rfp_db_id,
                        RFPDocument.filename == doc.filename,
                    )
                    .first()
                )

                if existing:
                    existing.file_path = doc.file_path
                    existing.file_size = doc.file_size
                    existing.checksum = doc.checksum
                    existing.downloaded_at = doc.downloaded_at

            session.commit()
            logger.info(
                "Updated %d documents with download info for RFP %s",
                len(downloaded_docs),
                rfp_id,
            )

    except Exception as e:
        logger.error("Error processing documents for RFP %s: %s", rfp_id, e)


@router.post("/{rfp_id}/refresh", response_model=RefreshResponse)
async def refresh_rfp(
    rfp_id: str,
    background_tasks: BackgroundTasks,
    db: DBDep = ...,
):
    """
    Refresh/re-scrape an existing RFP to check for updates.

    Detects:
    - New Q&A entries
    - New documents
    - Metadata changes (deadline, description, etc.)
    """
    # Find the RFP
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    if not rfp.source_url:
        raise HTTPException(status_code=400, detail="RFP was not scraped from a URL")

    # Get appropriate scraper
    scraper = get_scraper(rfp.source_url)
    if not scraper:
        raise HTTPException(status_code=400, detail="No scraper available for this URL")

    try:
        # Refresh check
        result = await scraper.refresh(rfp.source_url, rfp.scrape_checksum)
        updated_rfp = result["updated_rfp"]

        # Count existing Q&A and docs in database
        existing_qa_count = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).count()
        existing_doc_count = (
            db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).count()
        )

        # Check if database is missing documents/Q&A that were scraped
        # (This can happen if previous saves failed due to constraints)
        scraped_doc_count = len(updated_rfp.documents) if updated_rfp else 0
        scraped_qa_count = len(updated_rfp.qa_items) if updated_rfp else 0

        # Also check for documents that exist but failed to download (file_path is None)
        pending_downloads = (
            db.query(RFPDocument)
            .filter(RFPDocument.rfp_id == rfp.id, RFPDocument.file_path.is_(None))
            .count()
        )

        has_missing_data = (
            (scraped_doc_count > existing_doc_count)
            or (scraped_qa_count > existing_qa_count)
            or (pending_downloads > 0)
        )

        if not result["has_changes"] and not has_missing_data:
            return RefreshResponse(
                rfp_id=rfp_id,
                has_changes=False,
                new_qa_count=0,
                new_document_count=0,
                metadata_changed=False,
                message="No changes detected",
            )

        # Check for new Q&A
        new_qa_count = len(updated_rfp.qa_items) - existing_qa_count
        if new_qa_count > 0:
            # Mark existing Q&A as not new
            db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).update(
                {RFPQandA.is_new: False}
            )

            # Add new Q&A
            for qa in updated_rfp.qa_items[existing_qa_count:]:
                qa_record = RFPQandA(
                    rfp_id=rfp.id,
                    question_number=qa.question_number,
                    question_text=qa.question_text,
                    answer_text=qa.answer_text,
                    asked_date=qa.asked_date,
                    answered_date=qa.answered_date,
                    is_new=True,
                )
                db.add(qa_record)

        # Check for new documents OR documents that failed to download (file_path is None)
        new_doc_count = len(updated_rfp.documents) - existing_doc_count
        docs_needing_download = (
            db.query(RFPDocument)
            .filter(RFPDocument.rfp_id == rfp.id, RFPDocument.file_path.is_(None))
            .count()
        )

        if new_doc_count > 0 or docs_needing_download > 0:
            # Download documents in background (includes retrying failed downloads)
            background_tasks.add_task(
                _download_and_save_documents, scraper, updated_rfp, rfp.id, rfp_id
            )
            logger.info(
                "Triggering download: %d new, %d pending",
                new_doc_count,
                docs_needing_download,
            )

        # Check for metadata changes
        metadata_changed = (
            rfp.title != updated_rfp.title
            or rfp.description != updated_rfp.description
            or rfp.response_deadline != updated_rfp.response_deadline
        )

        # Update RFP metadata - only if extraction succeeded (not fallback values)
        if updated_rfp.title and updated_rfp.title != "Untitled RFP":
            rfp.title = updated_rfp.title
        if updated_rfp.description:
            rfp.description = updated_rfp.description
        if updated_rfp.response_deadline:
            rfp.response_deadline = updated_rfp.response_deadline
        rfp.last_scraped_at = datetime.now(timezone.utc)
        rfp.scrape_checksum = updated_rfp.scrape_checksum

        db.commit()

        return RefreshResponse(
            rfp_id=rfp_id,
            has_changes=True,
            new_qa_count=max(0, new_qa_count),
            new_document_count=max(0, new_doc_count),
            metadata_changed=metadata_changed,
            message=f"Found {max(0, new_qa_count)} new Q&A and {max(0, new_doc_count)} new documents",
        )

    except Exception as e:
        logger.error("Error refreshing RFP %s: %s", rfp_id, e)
        raise HTTPException(status_code=500, detail=f"Refresh failed: {e!s}") from e


@router.get("/{rfp_id}/documents", response_model=list[RFPDocumentResponse])
async def get_rfp_documents(rfp_id: str, db: DBDep):
    """Get all documents for an RFP, including download status."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    documents = db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).all()

    # Add download_status based on file_path presence
    response = []
    for doc in documents:
        # Determine download status
        if doc.file_path and os.path.exists(doc.file_path):
            download_status = "completed"
        elif doc.file_path:
            # file_path set but file doesn't exist - download failed
            download_status = "failed"
        else:
            # file_path not set - still pending
            download_status = "pending"

        response.append(
            RFPDocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                document_type=doc.document_type,
                source_url=doc.source_url,
                downloaded_at=doc.downloaded_at,
                download_status=download_status,
            )
        )

    return response


@router.get("/{rfp_id}/documents/{doc_id}/download")
async def download_document(rfp_id: str, doc_id: int, db: DBDep):
    """Download a specific document."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    document = (
        db.query(RFPDocument)
        .filter(RFPDocument.id == doc_id, RFPDocument.rfp_id == rfp.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not available")

    return FileResponse(
        path=document.file_path,
        filename=document.filename,
        media_type="application/octet-stream",
    )


@router.get("/{rfp_id}/qa", response_model=list[RFPQandAResponse])
async def get_rfp_qa(
    rfp_id: str,
    *,
    new_only: bool = False,
    db: DBDep = ...,
):
    """Get Q&A items for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    query = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id)

    if new_only:
        query = query.filter(RFPQandA.is_new)

    qa_items = query.order_by(RFPQandA.question_number).all()
    return qa_items


@router.post("/{rfp_id}/qa/analyze")
async def analyze_qa(rfp_id: str, db: DBDep):
    """
    Run AI analysis on Q&A items to categorize and extract insights.
    """
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    qa_items = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).all()

    if not qa_items:
        return {"message": "No Q&A items to analyze", "analyzed_count": 0}

    # Import the QA analyzer
    from src.agents.scrapers.qa_analyzer import QAAnalyzer

    analyzer = QAAnalyzer()
    analyzed_count = 0

    for qa in qa_items:
        try:
            analysis = await analyzer.analyze(qa.question_text, qa.answer_text)
            qa.category = analysis.get("category")
            qa.key_insights = analysis.get("insights", [])
            qa.related_sections = analysis.get("related_sections", [])
            analyzed_count += 1
        except Exception as e:
            logger.warning("Failed to analyze Q&A %d: %s", qa.id, e)

    db.commit()

    return {
        "message": f"Analyzed {analyzed_count} Q&A items",
        "analyzed_count": analyzed_count,
    }


# =============================================================================
# Preview & Confirm Import Endpoints
# =============================================================================


class PreviewRequest(BaseModel):
    """Request to preview RFP extraction from a URL."""

    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is well-formed."""
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("Invalid URL: missing domain")
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        return v


class DetectedFields(BaseModel):
    """Extracted RFP fields from preview."""

    title: str | None = None
    solicitation_number: str | None = None
    agency: str | None = None
    office: str | None = None
    description: str | None = None
    posted_date: str | None = None
    response_deadline: str | None = None
    naics_code: str | None = None
    category: str | None = None
    estimated_value: float | None = None


class PreviewDocument(BaseModel):
    """Document info from preview."""

    filename: str
    source_url: str
    file_type: str | None = None


class PreviewQA(BaseModel):
    """Q&A item from preview."""

    question: str
    answer: str | None = None
    number: str | None = None


class DuplicateCheck(BaseModel):
    """Info about existing RFP if URL was already imported."""

    rfp_id: str
    title: str
    imported_at: str | None = None


class PreviewResponse(BaseModel):
    """Preview of extracted RFP data before saving."""

    source_url: str
    source_platform: str
    detected_fields: DetectedFields
    documents: list[PreviewDocument]
    qa_items: list[PreviewQA]
    duplicate_check: DuplicateCheck | None = None


@router.post("/preview", response_model=PreviewResponse)
async def preview_rfp(request: PreviewRequest, db: DBDep):
    """
    Extract RFP data from URL without saving to database.

    Returns extracted data for user review/editing before confirming import.
    This allows users to:
    1. See what will be imported before committing
    2. Edit/correct any misextracted fields
    3. Check for duplicates before importing
    """
    url = request.url

    # Check for duplicates first
    existing = db.query(RFPOpportunity).filter(RFPOpportunity.source_url == url).first()

    duplicate_check = None
    if existing:
        duplicate_check = DuplicateCheck(
            rfp_id=existing.rfp_id,
            title=existing.title or "Untitled",
            imported_at=existing.discovered_at.isoformat() if existing.discovered_at else None,
        )

    # Get appropriate scraper
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(
            status_code=400,
            detail="URL not supported. Must be a valid HTTP or HTTPS URL.",
        )

    try:
        # Scrape without saving
        logger.info("Preview scrape of URL: %s", url)
        scraped = await scraper.scrape(url)

        return PreviewResponse(
            source_url=url,
            source_platform=scraped.source_platform,
            detected_fields=DetectedFields(
                title=scraped.title,
                solicitation_number=scraped.solicitation_number,
                agency=scraped.agency,
                office=scraped.office,
                description=scraped.description,
                posted_date=scraped.posted_date.isoformat() if scraped.posted_date else None,
                response_deadline=scraped.response_deadline.isoformat() if scraped.response_deadline else None,
                naics_code=scraped.naics_code,
                category=scraped.category,
                estimated_value=scraped.estimated_value,
            ),
            documents=[
                PreviewDocument(
                    filename=d.filename,
                    source_url=d.source_url,
                    file_type=d.file_type,
                )
                for d in scraped.documents
            ],
            qa_items=[
                PreviewQA(
                    question=q.question_text,
                    answer=q.answer_text,
                    number=q.question_number,
                )
                for q in scraped.qa_items
            ],
            duplicate_check=duplicate_check,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error previewing RFP from %s: %s", url, e)
        raise HTTPException(status_code=500, detail=f"Preview failed: {e!s}") from e


class ConfirmImportRequest(BaseModel):
    """Request to confirm and save a previewed RFP with optional edits."""

    source_url: str
    company_profile_id: int | None = None
    # User can override any field extracted during preview
    overrides: dict[str, str | float | None] = {}

    @field_validator("source_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is well-formed."""
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https scheme")
        if not parsed.netloc:
            raise ValueError("Invalid URL: missing domain")
        v = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", v)
        return v


@router.post("/confirm", response_model=ScrapeResponse)
async def confirm_import(
    request: ConfirmImportRequest,
    background_tasks: BackgroundTasks,
    db: DBDep,
):
    """
    Confirm import of a previewed RFP with optional field overrides.

    After previewing an RFP, users can edit the extracted fields and then
    confirm the import. This endpoint:
    1. Re-scrapes the URL to get fresh data
    2. Applies any user overrides to the extracted fields
    3. Saves the RFP to the database
    4. Triggers background document download
    """
    url = request.source_url

    # Check for duplicates
    existing = db.query(RFPOpportunity).filter(RFPOpportunity.source_url == url).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"RFP already exists with ID: {existing.rfp_id}. Use refresh endpoint to update.",
        )

    # Get appropriate scraper
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(
            status_code=400,
            detail="URL not supported. Must be a valid HTTP or HTTPS URL.",
        )

    try:
        # Re-scrape to get fresh data
        logger.info("Confirm import scrape of URL: %s", url)
        scraped_rfp = await scraper.scrape(url)

        # Apply user overrides
        overrides = request.overrides
        if overrides:
            if "title" in overrides and overrides["title"]:
                scraped_rfp.title = str(overrides["title"])
            if "solicitation_number" in overrides:
                scraped_rfp.solicitation_number = str(overrides["solicitation_number"]) if overrides["solicitation_number"] else None
            if "agency" in overrides:
                scraped_rfp.agency = str(overrides["agency"]) if overrides["agency"] else None
            if "office" in overrides:
                scraped_rfp.office = str(overrides["office"]) if overrides["office"] else None
            if "description" in overrides:
                scraped_rfp.description = str(overrides["description"]) if overrides["description"] else None
            if "naics_code" in overrides:
                scraped_rfp.naics_code = str(overrides["naics_code"]) if overrides["naics_code"] else None
            if "category" in overrides:
                scraped_rfp.category = str(overrides["category"]) if overrides["category"] else None
            if "estimated_value" in overrides:
                try:
                    scraped_rfp.estimated_value = float(overrides["estimated_value"]) if overrides["estimated_value"] else None
                except (ValueError, TypeError):
                    pass

            # Recompute checksum after changes
            scraped_rfp.compute_checksum()

        # Generate unique RFP ID
        rfp_id = f"RFP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"

        # Create RFP in database
        rfp = RFPOpportunity(
            rfp_id=rfp_id,
            solicitation_number=scraped_rfp.solicitation_number,
            title=scraped_rfp.title,
            description=scraped_rfp.description,
            agency=scraped_rfp.agency,
            office=scraped_rfp.office,
            naics_code=scraped_rfp.naics_code,
            category=scraped_rfp.category,
            posted_date=scraped_rfp.posted_date,
            response_deadline=scraped_rfp.response_deadline,
            award_amount=scraped_rfp.award_amount,
            estimated_value=scraped_rfp.estimated_value,
            current_stage=PipelineStage.DISCOVERED,
            source_url=url,
            source_platform=scraped_rfp.source_platform,
            last_scraped_at=datetime.now(timezone.utc),
            scrape_checksum=scraped_rfp.scrape_checksum,
            company_profile_id=request.company_profile_id,
            rfp_metadata=scraped_rfp.raw_data,
        )
        db.add(rfp)
        db.commit()
        db.refresh(rfp)

        # Download documents in background
        background_tasks.add_task(
            _download_and_save_documents, scraper, scraped_rfp, rfp.id, rfp_id
        )

        # Save Q&A items
        for qa in scraped_rfp.qa_items:
            qa_record = RFPQandA(
                rfp_id=rfp.id,
                question_number=qa.question_number,
                question_text=qa.question_text,
                answer_text=qa.answer_text,
                asked_date=qa.asked_date,
                answered_date=qa.answered_date,
                is_new=True,
            )
            db.add(qa_record)

        db.commit()

        # Broadcast RFP created to connected clients
        from app.websockets.websocket_router import broadcast_rfp_update

        await broadcast_rfp_update(
            rfp_id,
            "rfp_scraped",
            {
                "title": scraped_rfp.title,
                "documents_count": len(scraped_rfp.documents),
                "qa_count": len(scraped_rfp.qa_items),
            },
        )

        return ScrapeResponse(
            rfp_id=rfp_id,
            status="success",
            title=scraped_rfp.title,
            documents_count=len(scraped_rfp.documents),
            qa_count=len(scraped_rfp.qa_items),
            message="RFP imported successfully. Documents are downloading in background.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error confirming RFP import from %s: %s", url, e)
        raise HTTPException(status_code=500, detail=f"Import failed: {e!s}") from e
