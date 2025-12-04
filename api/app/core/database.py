"""
Database session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models to ensure relationships are configured
    from app.models.database import (  # noqa: F401
        Base,
        RFPOpportunity,
        RFPDocument,
        RFPQandA,
        CompanyProfile,
        BidDocument,
        BidDocumentVersion,
        PipelineEvent,
        PostAwardChecklist,
        Submission,
        SubmissionAuditLog,
        AlertRule,
        AlertNotification,
        ChatSession,
        ChatMessage,
        ComplianceMatrix,
        ComplianceRequirement,
        PricingResult,
        SavedRfp,
    )
    from sqlalchemy.orm import configure_mappers
    configure_mappers()  # Ensure all relationships are resolved
    Base.metadata.create_all(bind=engine)
