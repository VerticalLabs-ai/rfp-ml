"""
Database models for RFP Dashboard and Submission System.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PipelineStage(str, PyEnum):
    """Pipeline stage enumeration."""
    DISCOVERED = "discovered"
    TRIAGED = "triaged"
    ANALYZING = "analyzing"
    PRICING = "pricing"
    DECISION_PENDING = "decision_pending"
    APPROVED = "approved"
    DOCUMENT_GENERATION = "document_generation"
    REVIEW = "review"
    SUBMISSION_READY = "submission_ready"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    FAILED = "failed"


class SubmissionStatus(str, PyEnum):
    """Submission status enumeration."""
    QUEUED = "queued"
    VALIDATING = "validating"
    FORMATTING = "formatting"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"


class RFPOpportunity(Base):
    """RFP opportunity in the pipeline."""
    __tablename__ = "rfp_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(String, unique=True, index=True, nullable=False)
    solicitation_number = Column(String, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    agency = Column(String)
    office = Column(String)
    naics_code = Column(String)
    category = Column(String)

    # Dates
    posted_date = Column(DateTime)
    response_deadline = Column(DateTime)
    award_date = Column(DateTime, nullable=True)

    # Amounts
    award_amount = Column(Float, nullable=True)
    estimated_value = Column(Float, nullable=True)

    # Pipeline tracking
    current_stage = Column(Enum(PipelineStage), default=PipelineStage.DISCOVERED)
    triage_score = Column(Float)
    overall_score = Column(Float, nullable=True)
    decision_recommendation = Column(String, nullable=True)
    confidence_level = Column(Float, nullable=True)

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Assignment
    assigned_to = Column(String, nullable=True)
    priority = Column(Integer, default=0)

    # Metadata (using rfp_metadata to avoid SQLAlchemy reserved name)
    rfp_metadata = Column(JSON, default={})

    # Relationships
    compliance_matrix = relationship("ComplianceMatrix", back_populates="rfp", uselist=False)
    pricing_result = relationship("PricingResult", back_populates="rfp", uselist=False)
    bid_document = relationship("BidDocument", back_populates="rfp", uselist=False)
    submissions = relationship("Submission", back_populates="rfp")
    pipeline_events = relationship("PipelineEvent", back_populates="rfp")


class ComplianceMatrix(Base):
    """Compliance matrix for an RFP."""
    __tablename__ = "compliance_matrices"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), unique=True)

    requirements_extracted = Column(Integer, default=0)
    requirements_met = Column(Integer, default=0)
    compliance_score = Column(Float)

    matrix_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfp = relationship("RFPOpportunity", back_populates="compliance_matrix")


class PricingResult(Base):
    """Pricing result for an RFP."""
    __tablename__ = "pricing_results"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), unique=True)

    total_price = Column(Float, nullable=False)
    base_cost = Column(Float, nullable=False)
    margin_percentage = Column(Float, nullable=False)
    pricing_strategy = Column(String)
    competitive_score = Column(Float)
    confidence_score = Column(Float)

    price_breakdown = Column(JSON)
    risk_factors = Column(JSON)
    justification = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfp = relationship("RFPOpportunity", back_populates="pricing_result")


class BidDocument(Base):
    """Generated bid document."""
    __tablename__ = "bid_documents"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), unique=True)
    document_id = Column(String, unique=True, index=True)

    content_markdown = Column(Text)
    content_html = Column(Text)
    content_json = Column(JSON)

    version = Column(Integer, default=1)
    status = Column(String, default="draft")  # draft, review, approved, submitted

    # Metadata
    document_stats = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String, nullable=True)

    rfp = relationship("RFPOpportunity", back_populates="bid_document")
    versions = relationship("BidDocumentVersion", back_populates="document")


class BidDocumentVersion(Base):
    """Version history for bid documents."""
    __tablename__ = "bid_document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("bid_documents.id"))
    version = Column(Integer, nullable=False)

    content_markdown = Column(Text)
    content_html = Column(Text)
    content_json = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    change_description = Column(String)

    document = relationship("BidDocument", back_populates="versions")


class Submission(Base):
    """Bid submission to government portal."""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(String, unique=True, index=True, nullable=False)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"))

    portal = Column(String, nullable=False)  # sam.gov, gsa_ebuy, etc.
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.QUEUED)

    # Submission details
    scheduled_time = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    confirmation_number = Column(String, nullable=True)
    receipt_data = Column(JSON, nullable=True)

    # Retry logic
    attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)

    # Priority
    priority = Column(Integer, default=0)
    deadline = Column(DateTime)

    # Metadata
    submission_package = Column(JSON)  # Files, forms, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfp = relationship("RFPOpportunity", back_populates="submissions")
    audit_logs = relationship("SubmissionAuditLog", back_populates="submission")


class SubmissionAuditLog(Base):
    """Audit log for submission events."""
    __tablename__ = "submission_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))

    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, nullable=False)
    user = Column(String, nullable=True)

    success = Column(Boolean, default=True)
    details = Column(JSON)
    error_message = Column(Text, nullable=True)

    submission = relationship("Submission", back_populates="audit_logs")


class PipelineEvent(Base):
    """Pipeline stage transition events."""
    __tablename__ = "pipeline_events"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"))

    from_stage = Column(Enum(PipelineStage), nullable=True)
    to_stage = Column(Enum(PipelineStage), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Float, nullable=True)

    user = Column(String, nullable=True)
    automated = Column(Boolean, default=True)

    notes = Column(Text, nullable=True)
    event_metadata = Column(JSON, default={})

    rfp = relationship("RFPOpportunity", back_populates="pipeline_events")


class DashboardMetrics(Base):
    """Cached dashboard metrics for performance."""
    __tablename__ = "dashboard_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(DateTime, default=datetime.utcnow, index=True)

    total_discovered = Column(Integer, default=0)
    in_pipeline = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    submitted_count = Column(Integer, default=0)

    avg_processing_time = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    pending_reviews = Column(Integer, default=0)

    # Category breakdown
    category_stats = Column(JSON, default={})

    # Performance metrics
    performance_stats = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
