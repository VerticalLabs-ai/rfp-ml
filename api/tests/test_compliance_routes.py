"""Tests for compliance API routes."""
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, RFPOpportunity
from app.core.database import get_db
from app.routes.compliance import router as compliance_router


# Use file-based SQLite for test - in-memory doesn't share connections well
TEST_DB_PATH = "/tmp/test_compliance.db"


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    # Remove old test db if exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    engine = create_engine(
        f"sqlite:///{TEST_DB_PATH}",
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield engine, TestingSessionLocal

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def client(test_db):
    """Create test client with db dependency override."""
    engine, TestingSessionLocal = test_db

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Create minimal test app
    test_app = FastAPI()
    test_app.include_router(compliance_router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = override_get_db

    return TestClient(test_app)


@pytest.fixture
def sample_rfp(test_db):
    """Create sample RFP in the test database."""
    engine, TestingSessionLocal = test_db
    db = TestingSessionLocal()
    rfp = RFPOpportunity(
        rfp_id="TEST-RFP-001",
        title="Test RFP for Compliance",
        description="Test Description",
        agency="Test Agency",
    )
    db.add(rfp)
    db.commit()
    db.refresh(rfp)
    rfp_id = rfp.id
    db.close()
    return rfp_id


def test_list_requirements_empty(client, sample_rfp):
    """Test listing requirements when none exist."""
    response = client.get(f"/api/v1/compliance/rfps/{sample_rfp}/requirements")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["requirements"] == []


def test_create_requirement(client, sample_rfp):
    """Test creating a new requirement."""
    payload = {
        "requirement_id": "L.1.1",
        "requirement_text": "The contractor shall provide monthly reports.",
        "requirement_type": "mandatory",
        "source_document": "SOW.pdf",
        "source_section": "4.1",
    }
    response = client.post(
        f"/api/v1/compliance/rfps/{sample_rfp}/requirements", json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["requirement_id"] == "L.1.1"
    assert data["status"] == "not_started"


def test_update_requirement_status(client, sample_rfp):
    """Test updating requirement status."""
    # First create a requirement
    payload = {
        "requirement_id": "M.1.1",
        "requirement_text": "Must have certification.",
        "requirement_type": "evaluation",
    }
    create_response = client.post(
        f"/api/v1/compliance/rfps/{sample_rfp}/requirements", json=payload
    )
    req_id = create_response.json()["id"]

    # Update status
    update_payload = {
        "status": "complete",
        "response_text": "We have the required certification.",
        "compliance_indicator": "compliant",
    }
    response = client.put(
        f"/api/v1/compliance/requirements/{req_id}", json=update_payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["compliance_indicator"] == "compliant"


def test_bulk_status_update(client, sample_rfp):
    """Test bulk status update."""
    # Create multiple requirements
    for i in range(3):
        client.post(
            f"/api/v1/compliance/rfps/{sample_rfp}/requirements",
            json={
                "requirement_id": f"B.{i}.1",
                "requirement_text": f"Bulk test requirement {i}",
                "requirement_type": "mandatory",
            },
        )

    # Get all requirement IDs
    list_response = client.get(f"/api/v1/compliance/rfps/{sample_rfp}/requirements")
    req_ids = [r["id"] for r in list_response.json()["requirements"]]

    # Bulk update
    response = client.put(
        f"/api/v1/compliance/rfps/{sample_rfp}/requirements/bulk-status",
        json={"requirement_ids": req_ids, "status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 3
