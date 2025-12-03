"""Tests for ComplianceRequirement model."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.models.database import Base, RFPOpportunity, ComplianceRequirement, RequirementType, RequirementStatus


@pytest.fixture
def db_session():
    """Create in-memory database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_rfp(db_session):
    """Create sample RFP for testing."""
    rfp = RFPOpportunity(
        rfp_id="TEST-001",
        title="Test RFP",
        description="Test Description",
        agency="Test Agency"
    )
    db_session.add(rfp)
    db_session.commit()
    return rfp


def test_create_compliance_requirement(db_session, sample_rfp):
    """Test creating a compliance requirement."""
    req = ComplianceRequirement(
        rfp_id=sample_rfp.id,
        requirement_id="L.1.1",
        requirement_text="The contractor shall provide weekly status reports.",
        source_document="SOW.pdf",
        source_section="Section 4.2",
        requirement_type=RequirementType.MANDATORY,
        status=RequirementStatus.NOT_STARTED,
        order_index=0
    )
    db_session.add(req)
    db_session.commit()

    assert req.id is not None
    assert req.requirement_id == "L.1.1"
    assert req.requirement_type == RequirementType.MANDATORY
    assert req.status == RequirementStatus.NOT_STARTED


def test_requirement_rfp_relationship(db_session, sample_rfp):
    """Test relationship between requirement and RFP."""
    req = ComplianceRequirement(
        rfp_id=sample_rfp.id,
        requirement_id="M.2.1",
        requirement_text="Must have ISO certification.",
        requirement_type=RequirementType.EVALUATION,
        status=RequirementStatus.NOT_STARTED,
        order_index=0
    )
    db_session.add(req)
    db_session.commit()

    assert req.rfp.rfp_id == "TEST-001"
    assert len(sample_rfp.compliance_requirements) == 1


def test_requirement_status_update(db_session, sample_rfp):
    """Test updating requirement status."""
    req = ComplianceRequirement(
        rfp_id=sample_rfp.id,
        requirement_id="P.1.1",
        requirement_text="Performance metric requirement.",
        requirement_type=RequirementType.PERFORMANCE,
        status=RequirementStatus.NOT_STARTED,
        order_index=0
    )
    db_session.add(req)
    db_session.commit()

    req.status = RequirementStatus.COMPLETE
    req.response_text = "We comply with this requirement."
    req.compliance_indicator = "compliant"
    db_session.commit()

    assert req.status == RequirementStatus.COMPLETE
    assert req.compliance_indicator == "compliant"
