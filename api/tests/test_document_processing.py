"""Integration tests for document processing endpoints."""
import io
import os
import pytest
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
# Import all models to ensure Base.metadata has them for create_all
from app.models import database as models  # noqa: F401
from app.models.database import Base, RFPOpportunity, RFPDocument
from app.core.database import get_db
from app.routes.documents import router as documents_router


# Use file-based SQLite for test
TEST_DB_PATH = "/tmp/test_documents.db"


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
def test_app(test_db):
    """Create test FastAPI app with documents router."""
    engine, TestingSessionLocal = test_db

    app = FastAPI()
    app.include_router(documents_router, prefix="/api/v1/documents")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_rfp(test_db):
    """Create a sample RFP for testing."""
    engine, TestingSessionLocal = test_db
    db = TestingSessionLocal()

    rfp = RFPOpportunity(
        rfp_id="test-rfp-001",
        solicitation_number="TEST-2025-001",
        title="Test RFP for Document Upload",
        description="A test RFP opportunity",
        agency="Test Agency",
        posted_date=datetime.now(timezone.utc),
        response_deadline=datetime.now(timezone.utc),
    )
    db.add(rfp)
    db.commit()
    db.refresh(rfp)

    yield rfp

    db.close()


def test_upload_document_pdf(client, sample_rfp):
    """Test uploading a PDF document."""
    # Create a mock PDF file
    file_content = b"%PDF-1.4\nTest PDF content\n%%EOF"
    files = {"file": ("test_document.pdf", io.BytesIO(file_content), "application/pdf")}

    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["filename"] == "test_document.pdf"
    assert data["file_type"] == "pdf"
    assert data["file_size"] == len(file_content)
    assert data["status"] == "processing"
    assert "uploaded_at" in data


def test_upload_document_txt(client, sample_rfp):
    """Test uploading a text document."""
    file_content = b"This is a test text document with some content."
    files = {"file": ("test_document.txt", io.BytesIO(file_content), "text/plain")}

    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_document.txt"
    assert data["file_type"] == "txt"
    assert data["file_size"] == len(file_content)


def test_upload_document_invalid_extension(client, sample_rfp):
    """Test uploading a document with invalid extension."""
    file_content = b"Invalid file type"
    files = {"file": ("test_document.exe", io.BytesIO(file_content), "application/octet-stream")}

    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"].lower()


def test_upload_empty_file(client, sample_rfp):
    """Test uploading an empty file."""
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}

    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_large_file(client, sample_rfp):
    """Test uploading a file that exceeds size limit."""
    # Create a file larger than 50MB
    large_content = b"x" * (51 * 1024 * 1024)
    files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}

    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_list_uploaded_documents(client, sample_rfp, test_db):
    """Test listing uploaded documents."""
    engine, TestingSessionLocal = test_db
    db = TestingSessionLocal()

    # Upload two documents
    file1 = b"Test content 1"
    files1 = {"file": ("doc1.txt", io.BytesIO(file1), "text/plain")}
    response1 = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files1,
    )
    assert response1.status_code == 200

    file2 = b"Test content 2"
    files2 = {"file": ("doc2.pdf", io.BytesIO(file2), "application/pdf")}
    response2 = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files2,
    )
    assert response2.status_code == 200

    # List documents
    response = client.get(f"/api/v1/documents/{sample_rfp.rfp_id}/uploads")
    assert response.status_code == 200

    data = response.json()
    assert "documents" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["documents"]) == 2

    # Check document details
    filenames = [doc["filename"] for doc in data["documents"]]
    assert "doc1.txt" in filenames
    assert "doc2.pdf" in filenames

    db.close()


def test_get_document_content_txt(client, sample_rfp):
    """Test retrieving text content from uploaded document."""
    file_content = b"This is test content that should be extracted."
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

    # Upload
    upload_response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    # Get content
    content_response = client.get(
        f"/api/v1/documents/{sample_rfp.rfp_id}/uploads/{document_id}/content"
    )
    assert content_response.status_code == 200

    content_data = content_response.json()
    assert "content" in content_data
    assert "char_count" in content_data
    assert "word_count" in content_data
    assert file_content.decode("utf-8") in content_data["content"]


def test_download_document(client, sample_rfp):
    """Test downloading an uploaded document."""
    file_content = b"Download test content"
    files = {"file": ("download_test.txt", io.BytesIO(file_content), "text/plain")}

    # Upload
    upload_response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    # Download
    download_response = client.get(
        f"/api/v1/documents/{sample_rfp.rfp_id}/uploads/{document_id}/download"
    )
    assert download_response.status_code == 200
    assert download_response.content == file_content


def test_delete_document(client, sample_rfp, test_db):
    """Test deleting an uploaded document."""
    engine, TestingSessionLocal = test_db
    db = TestingSessionLocal()

    # Upload
    file_content = b"Content to be deleted"
    files = {"file": ("delete_test.txt", io.BytesIO(file_content), "text/plain")}
    upload_response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    # Verify document exists in database
    doc_count_before = db.query(RFPDocument).filter(RFPDocument.rfp_id == sample_rfp.id).count()
    assert doc_count_before == 1

    # Delete
    delete_response = client.delete(
        f"/api/v1/documents/{sample_rfp.rfp_id}/uploads/{document_id}"
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    # Verify document removed from database
    db.expire_all()  # Refresh session
    doc_count_after = db.query(RFPDocument).filter(RFPDocument.rfp_id == sample_rfp.id).count()
    assert doc_count_after == 0

    # Verify file removed from filesystem
    list_response = client.get(f"/api/v1/documents/{sample_rfp.rfp_id}/uploads")
    assert list_response.json()["total"] == 0

    db.close()


def test_delete_nonexistent_document(client, sample_rfp):
    """Test deleting a document that doesn't exist."""
    response = client.delete(
        f"/api/v1/documents/{sample_rfp.rfp_id}/uploads/nonexistent-doc-123"
    )
    assert response.status_code == 404


def test_get_processing_status(client, sample_rfp):
    """Test getting processing status of an uploaded document."""
    file_content = b"Status test content"
    files = {"file": ("status_test.txt", io.BytesIO(file_content), "text/plain")}

    # Upload
    upload_response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )
    assert upload_response.status_code == 200
    document_id = upload_response.json()["id"]

    # Get status
    status_response = client.get(
        f"/api/v1/documents/{sample_rfp.rfp_id}/uploads/{document_id}/status"
    )
    assert status_response.status_code == 200

    status_data = status_response.json()
    assert "document_id" in status_data
    assert "status" in status_data
    assert status_data["status"] in ["pending", "processing", "completed", "failed"]


def test_upload_document_persistence(client, sample_rfp, test_db):
    """Test that uploaded documents persist in database."""
    engine, TestingSessionLocal = test_db
    db = TestingSessionLocal()

    # Upload document
    file_content = b"Persistence test content"
    files = {"file": ("persist_test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post(
        f"/api/v1/documents/{sample_rfp.rfp_id}/upload",
        files=files,
    )
    assert response.status_code == 200

    # Query database directly
    db_doc = db.query(RFPDocument).filter(RFPDocument.rfp_id == sample_rfp.id).first()
    assert db_doc is not None
    assert db_doc.filename == "persist_test.txt"
    assert db_doc.file_type == "txt"
    assert db_doc.file_size == len(file_content)
    assert db_doc.document_type == "uploaded"
    assert db_doc.file_path is not None
    assert Path(db_doc.file_path).exists()

    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
