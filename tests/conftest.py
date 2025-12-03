"""
Pytest configuration and shared fixtures for RFP ML tests.

Provides:
- Database fixtures with test isolation
- Mock fixtures for external services (LLM, RAG)
- Sample data factories
- API client fixtures for integration tests
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../api')))

from app.models.database import (
    AlertNotification,
    AlertPriority,
    AlertRule,
    AlertType,
    Base,
    CompanyProfile,
    PipelineStage,
    RFPOpportunity,
)
from src.pricing.pricing_engine import PricingEngine


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a test database session with automatic rollback."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency for FastAPI testing."""
    def _override():
        try:
            yield db_session
        finally:
            pass
    return _override


# =============================================================================
# Sample Data Factories
# =============================================================================

@pytest.fixture
def sample_rfp_data() -> dict[str, Any]:
    """Factory for sample RFP data."""
    return {
        "rfp_id": "RFP-2024-001",
        "solicitation_number": "SOL-12345",
        "title": "IT Infrastructure Support Services",
        "description": "Seeking qualified vendors for IT infrastructure support including cloud services, cybersecurity, and network management.",
        "agency": "Department of Defense",
        "office": "Defense Information Systems Agency",
        "naics_code": "541512",
        "category": "IT Services",
        "posted_date": datetime.now(timezone.utc) - timedelta(days=30),
        "response_deadline": datetime.now(timezone.utc) + timedelta(days=14),
        "estimated_value": 5000000.0,
        "current_stage": PipelineStage.DISCOVERED,
        "triage_score": 0.85,
        "overall_score": 0.78,
        "decision_recommendation": "GO",
        "source_platform": "sam.gov",
    }


@pytest.fixture
def sample_rfp(db_session, sample_rfp_data) -> RFPOpportunity:
    """Create and persist a sample RFP in the database."""
    rfp = RFPOpportunity(**sample_rfp_data)
    db_session.add(rfp)
    db_session.commit()
    db_session.refresh(rfp)
    return rfp


@pytest.fixture
def sample_rfp_list(db_session) -> list[RFPOpportunity]:
    """Create multiple sample RFPs for testing queries."""
    rfps = [
        RFPOpportunity(
            rfp_id=f"RFP-2024-{i:03d}",
            title=f"Sample RFP {i}",
            description=f"Description for RFP {i} with keywords cloud and cybersecurity",
            agency=["DoD", "NASA", "GSA", "DHS", "VA"][i % 5],
            naics_code=["541512", "541519", "518210"][i % 3],
            current_stage=[PipelineStage.DISCOVERED, PipelineStage.TRIAGED, PipelineStage.ANALYZING][i % 3],
            triage_score=0.5 + (i * 0.05),
            response_deadline=datetime.now(timezone.utc) + timedelta(days=i + 1),
        )
        for i in range(10)
    ]
    db_session.add_all(rfps)
    db_session.commit()
    return rfps


@pytest.fixture
def sample_company_profile(db_session) -> CompanyProfile:
    """Create a sample company profile."""
    profile = CompanyProfile(
        name="IBYTE Enterprises",
        legal_name="IBYTE Enterprises LLC",
        is_default=True,
        uei="ABC123XYZ789",
        cage_code="1A2B3",
        headquarters="Washington, DC",
        website="https://ibyte.com",
        established_year=2010,
        employee_count="50-100",
        certifications=["8(a)", "HUBZone", "ISO 9001:2015"],
        naics_codes=["541512", "541519", "518210"],
        core_competencies=["Cloud Computing", "Cybersecurity", "AI/ML"],
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


@pytest.fixture
def sample_alert_rule(db_session) -> AlertRule:
    """Create a sample alert rule."""
    rule = AlertRule(
        name="High-Value IT Contracts",
        description="Alert for IT contracts with high scores",
        alert_type=AlertType.KEYWORD_MATCH,
        priority=AlertPriority.HIGH,
        criteria={
            "keywords": ["cybersecurity", "cloud", "IT"],
            "match_title": True,
            "match_description": True,
        },
        notification_channels=["in_app"],
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


@pytest.fixture
def sample_notification(db_session, sample_alert_rule, sample_rfp) -> AlertNotification:
    """Create a sample notification."""
    notification = AlertNotification(
        rule_id=sample_alert_rule.id,
        rfp_id=sample_rfp.id,
        title="New matching RFP found",
        message="A new RFP matching your criteria has been discovered.",
        priority=AlertPriority.HIGH,
        is_read=False,
        delivery_status={"in_app": "delivered"},
        context_data={"matched_keywords": ["cloud", "cybersecurity"]},
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM to avoid API calls during tests."""
    mock = MagicMock()
    mock.generate.return_value = "Mocked LLM response"
    mock.generate_text.return_value = "This is a professionally written executive summary demonstrating our experience and qualifications."
    mock.get_status.return_value = {"current_backend": "mock", "available": True}
    return mock


@pytest.fixture
def mock_llm_manager(mock_llm):
    """Mock the EnhancedBidLLMManager."""
    mock_manager = MagicMock()
    mock_manager.llm_manager = mock_llm
    mock_manager.refine_content.return_value = "Refined content with improvements."
    mock_manager.generate_bid_section.return_value = {
        "section_type": "executive_summary",
        "content": "Generated proposal content.",
        "word_count": 150,
        "confidence_score": 0.85,
        "generation_method": "llm",
        "status": "generated",
    }
    return mock_manager


@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine for testing without vector database."""
    mock_rag = MagicMock()
    mock_rag.is_built = True

    # Mock retrieved document
    mock_doc = MagicMock()
    mock_doc.content = "Sample document content about IT services and cloud computing."
    mock_doc.document_id = "doc-001"
    mock_doc.source_dataset = "RFP Documents"
    mock_doc.similarity_score = 0.92

    # Mock context result
    mock_context = MagicMock()
    mock_context.retrieved_documents = [mock_doc]
    mock_context.context_text = "Relevant context from documents..."

    mock_rag.generate_context.return_value = mock_context
    mock_rag.build_index.return_value = None

    return mock_rag


@pytest.fixture
def mock_llm_interface(mock_llm):
    """Mock the LLM interface created by create_llm_interface."""
    mock_interface = MagicMock()
    mock_interface.generate_text.return_value = {
        "content": "AI-generated response based on the provided context.",
        "text": "AI-generated response based on the provided context.",
    }
    mock_interface.get_status.return_value = {"current_backend": "openai", "available": True}
    return mock_interface


# =============================================================================
# Pricing Engine Fixture
# =============================================================================

@pytest.fixture
def pricing_engine():
    """Fixture for the PricingEngine."""
    engine = PricingEngine()
    return engine


# =============================================================================
# FastAPI Test Client Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Create FastAPI test application."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app, override_get_db):
    """Create test client with database override."""
    from fastapi.testclient import TestClient
    from app.core.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Async Test Support
# =============================================================================

@pytest.fixture
def anyio_backend():
    """Backend for anyio pytest plugin."""
    return "asyncio"


# =============================================================================
# Test Data Helpers
# =============================================================================

class ChatMessageFactory:
    """Factory for creating chat message test data."""

    @staticmethod
    def user_message(content: str = "What are the key requirements?") -> dict:
        return {
            "role": "user",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def assistant_message(content: str = "Based on the RFP...") -> dict:
        return {
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def conversation_history(turns: int = 3) -> list[dict]:
        history = []
        for i in range(turns):
            history.append(ChatMessageFactory.user_message(f"Question {i+1}"))
            history.append(ChatMessageFactory.assistant_message(f"Answer {i+1}"))
        return history


class AlertRuleFactory:
    """Factory for creating alert rule test data."""

    @staticmethod
    def keyword_match(keywords: list[str] = None) -> dict:
        return {
            "name": "Keyword Alert",
            "alert_type": "keyword_match",
            "priority": "medium",
            "criteria": {
                "keywords": keywords or ["cloud", "cybersecurity"],
                "match_title": True,
                "match_description": True
            },
            "notification_channels": ["in_app"]
        }

    @staticmethod
    def deadline_approaching(days: int = 7) -> dict:
        return {
            "name": "Deadline Alert",
            "alert_type": "deadline_approaching",
            "priority": "high",
            "criteria": {"days_before": days},
            "notification_channels": ["in_app", "email"]
        }

    @staticmethod
    def score_threshold(min_score: float = 0.75) -> dict:
        return {
            "name": "High Score Alert",
            "alert_type": "score_threshold",
            "priority": "urgent",
            "criteria": {
                "min_score": min_score,
                "score_type": "triage"
            },
            "notification_channels": ["in_app"]
        }


@pytest.fixture
def chat_message_factory():
    """Fixture providing ChatMessageFactory."""
    return ChatMessageFactory


@pytest.fixture
def alert_rule_factory():
    """Fixture providing AlertRuleFactory."""
    return AlertRuleFactory
