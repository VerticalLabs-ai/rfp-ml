"""
Database models for RFP Dashboard and Submission System.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
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
    AWARDED = "awarded"


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
    rfp_metadata = Column(JSON, default=lambda: {})

    # Source tracking (for scraped RFPs)
    source_url = Column(String, nullable=True)  # BeaconBid URL, etc.
    source_platform = Column(String, nullable=True)  # "beaconbid", "sam.gov", "manual"
    last_scraped_at = Column(DateTime, nullable=True)
    scrape_checksum = Column(String, nullable=True)  # For detecting page changes

    # Company profile for proposal generation
    company_profile_id = Column(
        Integer, ForeignKey("company_profiles.id"), nullable=True
    )

    # Relationships
    compliance_matrix = relationship(
        "ComplianceMatrix", back_populates="rfp", uselist=False
    )
    pricing_result = relationship("PricingResult", back_populates="rfp", uselist=False)
    bid_document = relationship("BidDocument", back_populates="rfp", uselist=False)
    submissions = relationship("Submission", back_populates="rfp")
    pipeline_events = relationship("PipelineEvent", back_populates="rfp")
    post_award_checklist = relationship(
        "PostAwardChecklist", back_populates="rfp", uselist=False
    )
    documents = relationship("RFPDocument", back_populates="rfp")
    qa_items = relationship("RFPQandA", back_populates="rfp")
    company_profile = relationship("CompanyProfile", back_populates="rfps")

    def to_dict(self):
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "solicitation_number": self.solicitation_number,
            "title": self.title,
            "description": self.description,
            "agency": self.agency,
            "office": self.office,
            "naics_code": self.naics_code,
            "category": self.category,
            "posted_date": self.posted_date.isoformat() if self.posted_date else None,
            "response_deadline": (
                self.response_deadline.isoformat() if self.response_deadline else None
            ),
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "award_amount": self.award_amount,
            "estimated_value": self.estimated_value,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "triage_score": self.triage_score,
            "overall_score": self.overall_score,
            "decision_recommendation": self.decision_recommendation,
            "confidence_level": self.confidence_level,
            "discovered_at": (
                self.discovered_at.isoformat() if self.discovered_at else None
            ),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "rfp_metadata": self.rfp_metadata,
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "last_scraped_at": (
                self.last_scraped_at.isoformat() if self.last_scraped_at else None
            ),
            "company_profile_id": self.company_profile_id,
        }


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
    event_metadata = Column(JSON, default=lambda: {})

    rfp = relationship("RFPOpportunity", back_populates="pipeline_events")


class PostAwardChecklist(Base):
    """Post-award compliance checklist for an awarded RFP."""

    __tablename__ = "post_award_checklists"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(
        Integer, ForeignKey("rfp_opportunities.id"), unique=True, nullable=False
    )
    bid_document_id = Column(
        String, nullable=True
    )  # Reference to the specific bid that won

    generated_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="draft")  # draft, active, completed
    items = Column(JSON, default=lambda: [])  # List of checklist items
    summary = Column(JSON, default=lambda: {})  # Summary statistics about the checklist

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    rfp = relationship("RFPOpportunity", back_populates="post_award_checklist")

    def to_dict(self):
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "bid_document_id": self.bid_document_id,
            "generated_at": (
                self.generated_at.isoformat() if self.generated_at else None
            ),
            "status": self.status,
            "items": self.items,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CompanyProfile(Base):
    """Multi-tenant company profiles for proposal generation."""

    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # Display name
    legal_name = Column(String, nullable=True)  # Full legal business name
    is_default = Column(Boolean, default=False)  # Default profile for new RFPs

    # Identifiers
    uei = Column(String, nullable=True)  # Unique Entity Identifier
    cage_code = Column(String, nullable=True)
    duns_number = Column(String, nullable=True)

    # Contact Information
    headquarters = Column(String, nullable=True)
    website = Column(String, nullable=True)
    primary_contact_name = Column(String, nullable=True)
    primary_contact_email = Column(String, nullable=True)
    primary_contact_phone = Column(String, nullable=True)

    # Business Information
    established_year = Column(Integer, nullable=True)
    employee_count = Column(String, nullable=True)  # "50-100", "150+"
    certifications = Column(JSON, default=lambda: [])  # ["8(a)", "HUBZone", "ISO 9001"]
    naics_codes = Column(JSON, default=lambda: [])  # ["541512", "541519"]
    core_competencies = Column(JSON, default=lambda: [])  # List of capabilities
    past_performance = Column(JSON, default=lambda: [])  # List of past contracts

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfps = relationship("RFPOpportunity", back_populates="company_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "legal_name": self.legal_name,
            "is_default": self.is_default,
            "uei": self.uei,
            "cage_code": self.cage_code,
            "duns_number": self.duns_number,
            "headquarters": self.headquarters,
            "website": self.website,
            "primary_contact_name": self.primary_contact_name,
            "primary_contact_email": self.primary_contact_email,
            "primary_contact_phone": self.primary_contact_phone,
            "established_year": self.established_year,
            "employee_count": self.employee_count,
            "certifications": self.certifications,
            "naics_codes": self.naics_codes,
            "core_competencies": self.core_competencies,
            "past_performance": self.past_performance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RFPDocument(Base):
    """Document attachments for RFPs (downloaded from scraped sources)."""

    __tablename__ = "rfp_documents"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), nullable=False)

    filename = Column(String, nullable=False)  # Original filename
    file_path = Column(
        String, nullable=True
    )  # Local storage path (set after download completes)
    file_type = Column(String, nullable=True)  # "pdf", "docx", "xlsx"
    file_size = Column(Integer, nullable=True)  # Size in bytes
    document_type = Column(
        String, nullable=True
    )  # "solicitation", "amendment", "attachment", "qa_response"
    source_url = Column(String, nullable=True)  # Original download URL
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    checksum = Column(String, nullable=True)  # For change detection (MD5/SHA256)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfp = relationship("RFPOpportunity", back_populates="documents")

    def to_dict(self):
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "document_type": self.document_type,
            "source_url": self.source_url,
            "downloaded_at": (
                self.downloaded_at.isoformat() if self.downloaded_at else None
            ),
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RFPQandA(Base):
    """Q&A entries for RFPs with AI-powered analysis."""

    __tablename__ = "rfp_qa"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), nullable=False)

    question_number = Column(String, nullable=True)  # "Q1", "Q2", etc.
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    asked_date = Column(DateTime, nullable=True)
    answered_date = Column(DateTime, nullable=True)

    # AI Analysis
    category = Column(
        String, nullable=True
    )  # "technical", "pricing", "scope", "timeline", "compliance"
    key_insights = Column(JSON, default=lambda: [])  # AI-extracted insights
    related_sections = Column(JSON, default=lambda: [])  # Proposal sections affected

    # Tracking
    is_new = Column(Boolean, default=True)  # Flag for newly detected Q&A
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfp = relationship("RFPOpportunity", back_populates="qa_items")

    def to_dict(self):
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "question_number": self.question_number,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "asked_date": self.asked_date.isoformat() if self.asked_date else None,
            "answered_date": (
                self.answered_date.isoformat() if self.answered_date else None
            ),
            "category": self.category,
            "key_insights": self.key_insights,
            "related_sections": self.related_sections,
            "is_new": self.is_new,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlertType(str, PyEnum):
    """Alert type enumeration."""

    NEW_RFP = "new_rfp"
    DEADLINE_APPROACHING = "deadline_approaching"
    STAGE_CHANGE = "stage_change"
    SCORE_THRESHOLD = "score_threshold"
    KEYWORD_MATCH = "keyword_match"
    AGENCY_MATCH = "agency_match"
    NAICS_MATCH = "naics_match"
    DOCUMENT_UPDATED = "document_updated"
    QA_POSTED = "qa_posted"
    AWARD_ANNOUNCED = "award_announced"


class AlertPriority(str, PyEnum):
    """Alert priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, PyEnum):
    """Notification delivery channels."""

    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


class AlertRule(Base):
    """User-defined alert rules for RFP monitoring (GovGPT Smart Alerts parity)."""

    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Rule configuration
    alert_type = Column(Enum(AlertType), nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Enum(AlertPriority), default=AlertPriority.MEDIUM)

    # Matching criteria (JSON for flexibility)
    criteria = Column(JSON, default=lambda: {})
    # Examples:
    # For KEYWORD_MATCH: {"keywords": ["cybersecurity", "cloud"], "match_title": true, "match_description": true}
    # For AGENCY_MATCH: {"agencies": ["Department of Defense", "NASA"]}
    # For NAICS_MATCH: {"naics_codes": ["541512", "541519"]}
    # For DEADLINE_APPROACHING: {"days_before": 7}
    # For SCORE_THRESHOLD: {"min_score": 0.75, "score_type": "triage"}

    # Notification settings
    notification_channels = Column(JSON, default=lambda: ["in_app"])
    email_recipients = Column(JSON, default=lambda: [])
    webhook_url = Column(String, nullable=True)
    slack_channel = Column(String, nullable=True)

    # Throttling
    cooldown_minutes = Column(Integer, default=60)  # Minimum time between alerts
    max_alerts_per_day = Column(Integer, default=10)

    # Stats
    triggered_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)

    # User/tenant
    created_by = Column(String, nullable=True)
    company_profile_id = Column(
        Integer, ForeignKey("company_profiles.id"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notifications = relationship("AlertNotification", back_populates="rule")
    company_profile = relationship("CompanyProfile")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "alert_type": self.alert_type.value if self.alert_type else None,
            "is_active": self.is_active,
            "priority": self.priority.value if self.priority else None,
            "criteria": self.criteria,
            "notification_channels": self.notification_channels,
            "email_recipients": self.email_recipients,
            "webhook_url": self.webhook_url,
            "slack_channel": self.slack_channel,
            "cooldown_minutes": self.cooldown_minutes,
            "max_alerts_per_day": self.max_alerts_per_day,
            "triggered_count": self.triggered_count,
            "last_triggered_at": (
                self.last_triggered_at.isoformat() if self.last_triggered_at else None
            ),
            "created_by": self.created_by,
            "company_profile_id": self.company_profile_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AlertNotification(Base):
    """Individual alert notifications generated from rules."""

    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), nullable=True)

    # Notification content
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Enum(AlertPriority), default=AlertPriority.MEDIUM)

    # Status
    is_read = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    is_actioned = Column(Boolean, default=False)
    action_taken = Column(String, nullable=True)

    # Delivery status per channel
    delivery_status = Column(JSON, default=lambda: {})
    # Example: {"in_app": "delivered", "email": "sent", "webhook": "failed"}

    # Context data
    context_data = Column(JSON, default=lambda: {})
    # Example: {"matched_keywords": ["cloud"], "score_value": 0.87}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)

    # Relationships
    rule = relationship("AlertRule", back_populates="notifications")
    rfp = relationship("RFPOpportunity")

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rfp_id": self.rfp_id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value if self.priority else None,
            "is_read": self.is_read,
            "is_dismissed": self.is_dismissed,
            "is_actioned": self.is_actioned,
            "action_taken": self.action_taken,
            "delivery_status": self.delivery_status,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "dismissed_at": (
                self.dismissed_at.isoformat() if self.dismissed_at else None
            ),
        }


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
    category_stats = Column(JSON, default=lambda: {})

    # Performance metrics
    performance_stats = Column(JSON, default=lambda: {})

    created_at = Column(DateTime, default=datetime.utcnow)


class SamEntity(Base):
    """Represents an entity from SAM.gov Public Entity Extracts."""

    __tablename__ = "sam_entities"

    id = Column(Integer, primary_key=True, index=True)
    uei = Column(
        String, unique=True, index=True, nullable=False
    )  # Unique Entity Identifier
    legal_business_name = Column(String, nullable=False)
    duns = Column(
        String, nullable=True
    )  # Old DUNS number, might still be present in some datasets

    # Address Information
    address_line1 = Column(String, nullable=True)
    address_line2 = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    address_country = Column(String, default="US")

    # Business Details
    entity_type = Column(
        String, nullable=True
    )  # e.g., For-Profit Organization, Non-Profit
    business_start_date = Column(DateTime, nullable=True)
    organization_structure = Column(String, nullable=True)

    # Codes and Classifications
    naics_codes = Column(JSON, default=lambda: [])  # List of NAICS codes
    psc_codes = Column(JSON, default=lambda: [])  # List of Product Service Codes

    # Certifications and Business Types (Socioeconomic)
    business_types = Column(
        JSON, default=lambda: []
    )  # List of certifications (e.g., SDB, WOSB, SDVOSB, HUBZone)

    # Capabilities and Keywords
    purpose_of_registration = Column(Text, nullable=True)
    capabilities_narrative = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # Comma-separated or similar

    # Contact Info
    primary_poc_name = Column(String, nullable=True)
    primary_poc_email = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Registration Dates
    registration_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "uei": self.uei,
            "legal_business_name": self.legal_business_name,
            "duns": self.duns,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "address_city": self.address_city,
            "address_state": self.address_state,
            "address_zip": self.address_zip,
            "address_country": self.address_country,
            "entity_type": self.entity_type,
            "business_start_date": (
                self.business_start_date.isoformat()
                if self.business_start_date
                else None
            ),
            "organization_structure": self.organization_structure,
            "naics_codes": self.naics_codes,
            "psc_codes": self.psc_codes,
            "business_types": self.business_types,
            "purpose_of_registration": self.purpose_of_registration,
            "capabilities_narrative": self.capabilities_narrative,
            "keywords": self.keywords,
            "primary_poc_name": self.primary_poc_name,
            "primary_poc_email": self.primary_poc_email,
            "website": self.website,
            "registration_date": (
                self.registration_date.isoformat() if self.registration_date else None
            ),
            "expiration_date": (
                self.expiration_date.isoformat() if self.expiration_date else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatSession(Base):
    """Chat session for RFP Q&A conversations."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id"), nullable=False)

    # Session metadata
    title = Column(String, nullable=True)  # Auto-generated from first message
    summary = Column(Text, nullable=True)  # AI-generated summary

    # Status
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)

    # Relationships
    rfp = relationship("RFPOpportunity")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "rfp_id": self.rfp_id,
            "title": self.title,
            "summary": self.summary,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": (
                self.last_message_at.isoformat() if self.last_message_at else None
            ),
        }


class ChatMessage(Base):
    """Individual chat message in a session."""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)

    # Message content
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)

    # RAG context (for assistant messages)
    citations = Column(JSON, default=lambda: [])
    confidence = Column(Float, nullable=True)
    rag_context = Column(JSON, nullable=True)  # Store retrieved context for debugging

    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "citations": self.citations,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
