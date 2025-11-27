"""
RFP Scraper API endpoints for importing RFPs from external portals.
"""
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from app.core.database import get_db
from app.models.database import (
    RFPOpportunity,
    RFPDocument,
    RFPQandA,
    CompanyProfile,
    PipelineStage,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas
class ScrapeRequest(BaseModel):
    url: str
    company_profile_id: Optional[int] = None


class ScrapeResponse(BaseModel):
    rfp_id: str
    status: str
    title: str
    documents_count: int
    qa_count: int
    message: Optional[str] = None


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
    file_type: Optional[str]
    file_size: Optional[int]
    document_type: Optional[str]
    downloaded_at: Optional[datetime]

    class Config:
        from_attributes = True


class RFPQandAResponse(BaseModel):
    id: int
    question_number: Optional[str]
    question_text: str
    answer_text: Optional[str]
    asked_date: Optional[datetime]
    answered_date: Optional[datetime]
    category: Optional[str]
    key_insights: List[str]
    is_new: bool

    class Config:
        from_attributes = True


def get_scraper(url: str):
    """Get the appropriate scraper for a URL."""
    from src.agents.scrapers import BeaconBidScraper

    scrapers = [BeaconBidScraper()]

    for scraper in scrapers:
        if scraper.is_valid_url(url):
            return scraper

    return None


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_rfp(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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
            detail=f"Unsupported URL. Currently supported portals: BeaconBid"
        )

    try:
        # Scrape the RFP
        logger.info(f"Starting scrape of URL: {url}")
        scraped_rfp = await scraper.scrape(url)

        # Generate unique RFP ID
        rfp_id = f"RFP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"

        # Check for existing RFP with same URL
        existing = db.query(RFPOpportunity).filter(RFPOpportunity.source_url == url).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"RFP already exists with ID: {existing.rfp_id}. Use refresh endpoint to update."
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
            last_scraped_at=datetime.utcnow(),
            scrape_checksum=scraped_rfp.scrape_checksum,
            company_profile_id=request.company_profile_id,
            rfp_metadata=scraped_rfp.raw_data,
        )
        db.add(rfp)
        db.commit()
        db.refresh(rfp)

        # Download documents in background
        background_tasks.add_task(
            _download_and_save_documents,
            scraper,
            scraped_rfp,
            rfp.id,
            rfp_id,
            db
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

        return ScrapeResponse(
            rfp_id=rfp_id,
            status="success",
            title=scraped_rfp.title,
            documents_count=len(scraped_rfp.documents),
            qa_count=len(scraped_rfp.qa_items),
            message="RFP scraped successfully. Documents are downloading in background."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scraping RFP: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


async def _download_and_save_documents(scraper, scraped_rfp, rfp_db_id: int, rfp_id: str, db: Session):
    """Background task to download documents and save to database."""
    try:
        downloaded_docs = await scraper.download_documents(scraped_rfp, rfp_id)

        # Get a fresh session since we're in a background task
        from app.core.database import SessionLocal
        with SessionLocal() as session:
            for doc in downloaded_docs:
                doc_record = RFPDocument(
                    rfp_id=rfp_db_id,
                    filename=doc.filename,
                    file_path=doc.file_path,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    document_type=doc.document_type,
                    source_url=doc.source_url,
                    downloaded_at=doc.downloaded_at,
                    checksum=doc.checksum,
                )
                session.add(doc_record)

            session.commit()
            logger.info(f"Saved {len(downloaded_docs)} documents for RFP {rfp_id}")

    except Exception as e:
        logger.error(f"Error downloading documents for RFP {rfp_id}: {e}")


@router.post("/{rfp_id}/refresh", response_model=RefreshResponse)
async def refresh_rfp(
    rfp_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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

        if not result["has_changes"]:
            return RefreshResponse(
                rfp_id=rfp_id,
                has_changes=False,
                new_qa_count=0,
                new_document_count=0,
                metadata_changed=False,
                message="No changes detected"
            )

        updated_rfp = result["updated_rfp"]

        # Count existing Q&A and docs
        existing_qa_count = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).count()
        existing_doc_count = db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).count()

        # Check for new Q&A
        new_qa_count = len(updated_rfp.qa_items) - existing_qa_count
        if new_qa_count > 0:
            # Mark existing Q&A as not new
            db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id).update({RFPQandA.is_new: False})

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

        # Check for new documents
        new_doc_count = len(updated_rfp.documents) - existing_doc_count
        if new_doc_count > 0:
            # Download new documents in background
            background_tasks.add_task(
                _download_and_save_documents,
                scraper,
                updated_rfp,
                rfp.id,
                rfp_id,
                db
            )

        # Check for metadata changes
        metadata_changed = (
            rfp.title != updated_rfp.title or
            rfp.description != updated_rfp.description or
            rfp.response_deadline != updated_rfp.response_deadline
        )

        # Update RFP metadata
        rfp.title = updated_rfp.title
        rfp.description = updated_rfp.description
        rfp.response_deadline = updated_rfp.response_deadline
        rfp.last_scraped_at = datetime.utcnow()
        rfp.scrape_checksum = updated_rfp.scrape_checksum

        db.commit()

        return RefreshResponse(
            rfp_id=rfp_id,
            has_changes=True,
            new_qa_count=max(0, new_qa_count),
            new_document_count=max(0, new_doc_count),
            metadata_changed=metadata_changed,
            message=f"Found {max(0, new_qa_count)} new Q&A and {max(0, new_doc_count)} new documents"
        )

    except Exception as e:
        logger.error(f"Error refreshing RFP {rfp_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@router.get("/{rfp_id}/documents", response_model=List[RFPDocumentResponse])
async def get_rfp_documents(rfp_id: str, db: Session = Depends(get_db)):
    """Get all documents for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    documents = db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp.id).all()
    return documents


@router.get("/{rfp_id}/documents/{doc_id}/download")
async def download_document(rfp_id: str, doc_id: int, db: Session = Depends(get_db)):
    """Download a specific document."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    document = db.query(RFPDocument).filter(
        RFPDocument.id == doc_id,
        RFPDocument.rfp_id == rfp.id
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not available")

    return FileResponse(
        path=document.file_path,
        filename=document.filename,
        media_type="application/octet-stream"
    )


@router.get("/{rfp_id}/qa", response_model=List[RFPQandAResponse])
async def get_rfp_qa(
    rfp_id: str,
    new_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get Q&A items for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    query = db.query(RFPQandA).filter(RFPQandA.rfp_id == rfp.id)

    if new_only:
        query = query.filter(RFPQandA.is_new == True)

    qa_items = query.order_by(RFPQandA.question_number).all()
    return qa_items


@router.post("/{rfp_id}/qa/analyze")
async def analyze_qa(rfp_id: str, db: Session = Depends(get_db)):
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
            logger.warning(f"Failed to analyze Q&A {qa.id}: {e}")

    db.commit()

    return {
        "message": f"Analyzed {analyzed_count} Q&A items",
        "analyzed_count": analyzed_count
    }
