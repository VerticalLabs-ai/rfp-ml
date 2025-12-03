# Visual Compliance Matrix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive Visual Compliance Matrix interface (like GovGPT) for tracking RFP requirements with status indicators, inline editing, and AI-assisted response generation.

**Architecture:** Extend the existing ComplianceMatrix model with a new ComplianceRequirement model for granular requirement tracking. Create dedicated API endpoints for CRUD operations. Build a React component using shadcn/ui with drag-and-drop, filtering, and real-time updates.

**Tech Stack:** FastAPI (backend), SQLAlchemy (ORM), React + TypeScript + shadcn/ui + React Query (frontend), Claude LLM (AI extraction/responses), ChromaDB RAG (context retrieval)

---

## Phase 1: Database & Models

### Task 1: Create ComplianceRequirement Model

**Files:**
- Modify: `api/app/models/database.py`

**Step 1: Write the test file**

Create: `api/tests/test_compliance_requirement_model.py`

```python
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
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest api/tests/test_compliance_requirement_model.py -v`
Expected: FAIL with "cannot import name 'ComplianceRequirement'"

**Step 3: Add enums and model to database.py**

Add after existing imports in `api/app/models/database.py`:

```python
class RequirementType(str, enum.Enum):
    """Type of compliance requirement."""
    MANDATORY = "mandatory"
    EVALUATION = "evaluation"
    PERFORMANCE = "performance"
    TECHNICAL = "technical"
    ADMINISTRATIVE = "administrative"


class RequirementStatus(str, enum.Enum):
    """Status of requirement compliance."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"
```

Add the model class (after ComplianceMatrix model):

```python
class ComplianceRequirement(Base):
    """Individual compliance requirement extracted from RFP documents."""
    __tablename__ = "compliance_requirements"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True)

    # Requirement identification
    requirement_id = Column(String(50), nullable=False)  # e.g., "L.1.2", "M.3.1"
    requirement_text = Column(Text, nullable=False)

    # Source tracking
    source_document = Column(String(255), nullable=True)  # e.g., "SOW.pdf"
    source_section = Column(String(100), nullable=True)  # e.g., "Section 4.2"
    source_page = Column(Integer, nullable=True)

    # Classification
    requirement_type = Column(SQLAlchemyEnum(RequirementType), nullable=False, default=RequirementType.MANDATORY)
    is_mandatory = Column(Boolean, default=True)

    # Status tracking
    status = Column(SQLAlchemyEnum(RequirementStatus), nullable=False, default=RequirementStatus.NOT_STARTED)
    response_text = Column(Text, nullable=True)
    compliance_indicator = Column(String(20), nullable=True)  # "compliant", "partial", "non_compliant"
    confidence_score = Column(Float, nullable=True)

    # Organization
    order_index = Column(Integer, default=0)  # For drag-and-drop ordering
    assigned_to = Column(String(100), nullable=True)  # Future: team member assignment

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    rfp = relationship("RFPOpportunity", back_populates="compliance_requirements")

    def __repr__(self):
        return f"<ComplianceRequirement {self.requirement_id}: {self.requirement_text[:50]}...>"
```

**Step 4: Add relationship to RFPOpportunity model**

Find the RFPOpportunity class and add to relationships:

```python
    # In RFPOpportunity class, add:
    compliance_requirements = relationship(
        "ComplianceRequirement",
        back_populates="rfp",
        cascade="all, delete-orphan",
        order_by="ComplianceRequirement.order_index"
    )
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest api/tests/test_compliance_requirement_model.py -v`
Expected: PASS (all 3 tests)

**Step 6: Commit**

```bash
git add api/app/models/database.py api/tests/test_compliance_requirement_model.py
git commit -m "feat(compliance): add ComplianceRequirement model with status tracking"
```

---

### Task 2: Create Database Migration

**Files:**
- Create: Migration file via alembic

**Step 1: Generate migration**

Run: `cd api && alembic revision --autogenerate -m "add_compliance_requirements_table"`

**Step 2: Review and verify migration**

Check the generated migration file in `api/alembic/versions/`

**Step 3: Apply migration**

Run: `cd api && alembic upgrade head`

**Step 4: Verify table exists**

Run: `docker exec -it rfp_ml-db-1 psql -U postgres -d rfp_db -c "\d compliance_requirements"`

**Step 5: Commit**

```bash
git add api/alembic/versions/
git commit -m "chore(db): add migration for compliance_requirements table"
```

---

## Phase 2: Pydantic Schemas

### Task 3: Create Compliance Requirement Schemas

**Files:**
- Create: `api/app/schemas/compliance.py`

**Step 1: Create schema file**

```python
"""Pydantic schemas for compliance requirements."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from api.app.models.database import RequirementType, RequirementStatus


class ComplianceRequirementBase(BaseModel):
    """Base schema for compliance requirement."""
    requirement_id: str = Field(..., description="Requirement identifier (e.g., L.1.2)")
    requirement_text: str = Field(..., description="Full requirement text")
    source_document: Optional[str] = Field(None, description="Source document name")
    source_section: Optional[str] = Field(None, description="Section reference")
    source_page: Optional[int] = Field(None, description="Page number")
    requirement_type: RequirementType = Field(default=RequirementType.MANDATORY)
    is_mandatory: bool = Field(default=True)


class ComplianceRequirementCreate(ComplianceRequirementBase):
    """Schema for creating a compliance requirement."""
    pass


class ComplianceRequirementUpdate(BaseModel):
    """Schema for updating a compliance requirement."""
    requirement_text: Optional[str] = None
    source_document: Optional[str] = None
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    requirement_type: Optional[RequirementType] = None
    is_mandatory: Optional[bool] = None
    status: Optional[RequirementStatus] = None
    response_text: Optional[str] = None
    compliance_indicator: Optional[str] = None
    confidence_score: Optional[float] = None
    order_index: Optional[int] = None
    assigned_to: Optional[str] = None


class ComplianceRequirementResponse(ComplianceRequirementBase):
    """Schema for compliance requirement response."""
    id: int
    rfp_id: int
    status: RequirementStatus
    response_text: Optional[str]
    compliance_indicator: Optional[str]
    confidence_score: Optional[float]
    order_index: int
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceRequirementList(BaseModel):
    """Schema for list of compliance requirements with summary."""
    requirements: List[ComplianceRequirementResponse]
    total: int
    completed: int
    in_progress: int
    not_started: int
    compliance_rate: float = Field(..., description="Percentage of completed requirements")


class BulkStatusUpdate(BaseModel):
    """Schema for bulk status update."""
    requirement_ids: List[int]
    status: RequirementStatus


class ReorderRequirements(BaseModel):
    """Schema for reordering requirements."""
    requirement_ids: List[int] = Field(..., description="Ordered list of requirement IDs")


class AIResponseRequest(BaseModel):
    """Schema for AI response generation request."""
    requirement_id: int
    include_rag_context: bool = Field(default=True)


class AIResponseResult(BaseModel):
    """Schema for AI-generated response."""
    response_text: str
    confidence_score: float
    supporting_evidence: List[str]
```

**Step 2: Commit**

```bash
git add api/app/schemas/compliance.py
git commit -m "feat(schemas): add Pydantic schemas for compliance requirements"
```

---

## Phase 3: Backend API Endpoints

### Task 4: Create Compliance Routes

**Files:**
- Create: `api/app/routes/compliance.py`
- Modify: `api/app/main.py` (register router)

**Step 1: Write test file**

Create: `api/tests/test_compliance_routes.py`

```python
"""Tests for compliance API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.main import app
from api.app.models.database import Base, RFPOpportunity, ComplianceRequirement, RequirementType, RequirementStatus
from api.app.core.database import get_db


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_rfp():
    db = TestingSessionLocal()
    rfp = RFPOpportunity(
        rfp_id="TEST-RFP-001",
        title="Test RFP for Compliance",
        description="Test Description",
        agency="Test Agency"
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
        "source_section": "4.1"
    }
    response = client.post(f"/api/v1/compliance/rfps/{sample_rfp}/requirements", json=payload)
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
        "requirement_type": "evaluation"
    }
    create_response = client.post(f"/api/v1/compliance/rfps/{sample_rfp}/requirements", json=payload)
    req_id = create_response.json()["id"]

    # Update status
    update_payload = {
        "status": "complete",
        "response_text": "We have the required certification.",
        "compliance_indicator": "compliant"
    }
    response = client.put(f"/api/v1/compliance/requirements/{req_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["compliance_indicator"] == "compliant"


def test_bulk_status_update(client, sample_rfp):
    """Test bulk status update."""
    # Create multiple requirements
    for i in range(3):
        client.post(f"/api/v1/compliance/rfps/{sample_rfp}/requirements", json={
            "requirement_id": f"B.{i}.1",
            "requirement_text": f"Bulk test requirement {i}",
            "requirement_type": "mandatory"
        })

    # Get all requirement IDs
    list_response = client.get(f"/api/v1/compliance/rfps/{sample_rfp}/requirements")
    req_ids = [r["id"] for r in list_response.json()["requirements"]]

    # Bulk update
    response = client.put(
        f"/api/v1/compliance/rfps/{sample_rfp}/requirements/bulk-status",
        json={"requirement_ids": req_ids, "status": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 3
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python -m pytest api/tests/test_compliance_routes.py -v`
Expected: FAIL with route not found errors

**Step 3: Create compliance routes**

Create: `api/app/routes/compliance.py`

```python
"""Compliance matrix API routes."""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.app.core.database import get_db
from api.app.models.database import (
    RFPOpportunity,
    ComplianceRequirement,
    RequirementStatus,
    RequirementType
)
from api.app.schemas.compliance import (
    ComplianceRequirementCreate,
    ComplianceRequirementUpdate,
    ComplianceRequirementResponse,
    ComplianceRequirementList,
    BulkStatusUpdate,
    ReorderRequirements,
    AIResponseRequest,
    AIResponseResult
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
    req = db.query(ComplianceRequirement).filter(ComplianceRequirement.id == requirement_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Requirement with id {requirement_id} not found")
    return req


@router.get("/rfps/{rfp_id}/requirements", response_model=ComplianceRequirementList)
async def list_requirements(
    rfp_id: int,
    status_filter: RequirementStatus | None = None,
    type_filter: RequirementType | None = None,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    """List all requirements for an RFP with optional filtering."""
    get_rfp_or_404(rfp_id, db)

    query = db.query(ComplianceRequirement).filter(ComplianceRequirement.rfp_id == rfp_id)

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
    in_progress = sum(1 for r in requirements if r.status == RequirementStatus.IN_PROGRESS)
    not_started = sum(1 for r in requirements if r.status == RequirementStatus.NOT_STARTED)
    compliance_rate = (completed / total * 100) if total > 0 else 0.0

    return ComplianceRequirementList(
        requirements=requirements,
        total=total,
        completed=completed,
        in_progress=in_progress,
        not_started=not_started,
        compliance_rate=compliance_rate
    )


@router.post("/rfps/{rfp_id}/requirements", response_model=ComplianceRequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    rfp_id: int,
    requirement: ComplianceRequirementCreate,
    db: Session = Depends(get_db)
):
    """Manually add a requirement to an RFP."""
    get_rfp_or_404(rfp_id, db)

    # Get next order index
    max_order = db.query(func.max(ComplianceRequirement.order_index)).filter(
        ComplianceRequirement.rfp_id == rfp_id
    ).scalar() or -1

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
        order_index=max_order + 1
    )

    db.add(db_requirement)
    db.commit()
    db.refresh(db_requirement)

    logger.info(f"Created requirement {db_requirement.requirement_id} for RFP {rfp_id}")
    return db_requirement


@router.put("/requirements/{requirement_id}", response_model=ComplianceRequirementResponse)
async def update_requirement(
    requirement_id: int,
    update: ComplianceRequirementUpdate,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    """Bulk update status for multiple requirements."""
    get_rfp_or_404(rfp_id, db)

    updated = db.query(ComplianceRequirement).filter(
        ComplianceRequirement.id.in_(update.requirement_ids),
        ComplianceRequirement.rfp_id == rfp_id
    ).update({"status": update.status}, synchronize_session=False)

    db.commit()

    logger.info(f"Bulk updated {updated} requirements to status {update.status}")
    return {"updated_count": updated}


@router.put("/rfps/{rfp_id}/requirements/reorder")
async def reorder_requirements(
    rfp_id: int,
    reorder: ReorderRequirements,
    db: Session = Depends(get_db)
):
    """Reorder requirements (for drag-and-drop)."""
    get_rfp_or_404(rfp_id, db)

    for index, req_id in enumerate(reorder.requirement_ids):
        db.query(ComplianceRequirement).filter(
            ComplianceRequirement.id == req_id,
            ComplianceRequirement.rfp_id == rfp_id
        ).update({"order_index": index}, synchronize_session=False)

    db.commit()

    logger.info(f"Reordered {len(reorder.requirement_ids)} requirements for RFP {rfp_id}")
    return {"reordered_count": len(reorder.requirement_ids)}
```

**Step 4: Register router in main.py**

In `api/app/main.py`, add:

```python
from api.app.routes.compliance import router as compliance_router

# Add with other router includes:
app.include_router(compliance_router, prefix="/api/v1")
```

**Step 5: Run test to verify it passes**

Run: `PYTHONPATH=. python -m pytest api/tests/test_compliance_routes.py -v`
Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add api/app/routes/compliance.py api/app/main.py api/tests/test_compliance_routes.py
git commit -m "feat(api): add compliance requirements CRUD endpoints"
```

---

### Task 5: Add Requirement Extraction Endpoint

**Files:**
- Modify: `api/app/routes/compliance.py`
- Modify: `api/app/schemas/compliance.py`

**Step 1: Add extraction schema**

Add to `api/app/schemas/compliance.py`:

```python
class ExtractionRequest(BaseModel):
    """Schema for extraction request."""
    document_ids: Optional[List[int]] = Field(None, description="Specific document IDs to extract from")
    use_llm: bool = Field(default=True, description="Use LLM for enhanced extraction")


class ExtractionResult(BaseModel):
    """Schema for extraction result."""
    extracted_count: int
    requirements: List[ComplianceRequirementResponse]
    source_documents: List[str]
```

**Step 2: Add extraction endpoint**

Add to `api/app/routes/compliance.py`:

```python
from src.compliance.compliance_matrix import ComplianceMatrixGenerator
from src.rag.chroma_rag_engine import get_rag_engine
from api.app.models.database import RFPDocument

@router.post("/rfps/{rfp_id}/extract-requirements", response_model=ExtractionResult)
async def extract_requirements(
    rfp_id: int,
    request: ExtractionRequest | None = None,
    db: Session = Depends(get_db)
):
    """Extract requirements from RFP documents using LLM."""
    rfp = get_rfp_or_404(rfp_id, db)

    # Get documents to process
    doc_query = db.query(RFPDocument).filter(RFPDocument.rfp_id == rfp_id)
    if request and request.document_ids:
        doc_query = doc_query.filter(RFPDocument.id.in_(request.document_ids))
    documents = doc_query.all()

    if not documents:
        raise HTTPException(status_code=400, detail="No documents found for extraction")

    # Combine document content
    combined_text = "\n\n".join([
        f"[Document: {doc.original_filename}]\n{doc.extracted_text or ''}"
        for doc in documents if doc.extracted_text
    ])

    if not combined_text.strip():
        raise HTTPException(status_code=400, detail="No text content found in documents")

    # Initialize compliance generator
    try:
        rag_engine = get_rag_engine()
    except Exception:
        rag_engine = None

    generator = ComplianceMatrixGenerator(rag_engine=rag_engine)

    # Extract requirements
    use_llm = request.use_llm if request else True
    if use_llm:
        extracted = generator.extract_requirements_llm(combined_text)
    else:
        extracted = generator.extract_requirements_rule_based(combined_text)

    # Get current max order index
    max_order = db.query(func.max(ComplianceRequirement.order_index)).filter(
        ComplianceRequirement.rfp_id == rfp_id
    ).scalar() or -1

    # Create requirement records
    created_requirements = []
    source_docs = list(set(doc.original_filename for doc in documents))

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
        req_type = type_mapping.get(req_data.get("category", "").lower(), RequirementType.MANDATORY)

        db_req = ComplianceRequirement(
            rfp_id=rfp_id,
            requirement_id=req_data.get("requirement_id", f"EXT.{idx + 1}"),
            requirement_text=req_data.get("text", req_data.get("requirement_text", "")),
            source_document=", ".join(source_docs),
            requirement_type=req_type,
            is_mandatory=req_data.get("mandatory", True),
            status=RequirementStatus.NOT_STARTED,
            order_index=max_order + idx + 1
        )
        db.add(db_req)
        created_requirements.append(db_req)

    db.commit()

    # Refresh to get IDs
    for req in created_requirements:
        db.refresh(req)

    logger.info(f"Extracted {len(created_requirements)} requirements from {len(documents)} documents for RFP {rfp_id}")

    return ExtractionResult(
        extracted_count=len(created_requirements),
        requirements=created_requirements,
        source_documents=source_docs
    )
```

**Step 3: Commit**

```bash
git add api/app/routes/compliance.py api/app/schemas/compliance.py
git commit -m "feat(api): add requirement extraction endpoint with LLM support"
```

---

### Task 6: Add AI Response Generation Endpoint

**Files:**
- Modify: `api/app/routes/compliance.py`

**Step 1: Add AI response endpoint**

Add to `api/app/routes/compliance.py`:

```python
from api.app.services.streaming import StreamingService

@router.post("/requirements/{requirement_id}/ai-response", response_model=AIResponseResult)
async def generate_ai_response(
    requirement_id: int,
    request: AIResponseRequest | None = None,
    db: Session = Depends(get_db)
):
    """Generate an AI-assisted response for a requirement."""
    requirement = get_requirement_or_404(requirement_id, db)
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == requirement.rfp_id).first()

    # Get RAG context if requested
    supporting_evidence = []
    rag_context = ""

    include_rag = request.include_rag_context if request else True
    if include_rag:
        try:
            rag_engine = get_rag_engine()
            results = rag_engine.retrieve(requirement.requirement_text, top_k=3)
            supporting_evidence = [r.get("text", "")[:200] for r in results]
            rag_context = "\n".join([f"- {r.get('text', '')}" for r in results])
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
    streaming_service = StreamingService()

    try:
        response_text = ""
        async for chunk in streaming_service.stream_llm_response(
            prompt=prompt,
            system_message="You are an expert government proposal writer. Generate concise, compliant responses.",
            task_type="compliance_response",
            max_tokens=1000
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
        supporting_evidence=supporting_evidence
    )
```

**Step 2: Commit**

```bash
git add api/app/routes/compliance.py
git commit -m "feat(api): add AI response generation endpoint for requirements"
```

---

## Phase 4: Frontend Components

### Task 7: Create API Service Functions

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add compliance API functions**

Add to `frontend/src/services/api.ts`:

```typescript
// Types for compliance
export interface ComplianceRequirement {
  id: number
  rfp_id: number
  requirement_id: string
  requirement_text: string
  source_document: string | null
  source_section: string | null
  source_page: number | null
  requirement_type: 'mandatory' | 'evaluation' | 'performance' | 'technical' | 'administrative'
  is_mandatory: boolean
  status: 'not_started' | 'in_progress' | 'complete' | 'not_applicable'
  response_text: string | null
  compliance_indicator: 'compliant' | 'partial' | 'non_compliant' | null
  confidence_score: number | null
  order_index: number
  assigned_to: string | null
  created_at: string
  updated_at: string
}

export interface ComplianceRequirementList {
  requirements: ComplianceRequirement[]
  total: number
  completed: number
  in_progress: number
  not_started: number
  compliance_rate: number
}

export interface CreateRequirementPayload {
  requirement_id: string
  requirement_text: string
  requirement_type: ComplianceRequirement['requirement_type']
  source_document?: string
  source_section?: string
  is_mandatory?: boolean
}

export interface UpdateRequirementPayload {
  requirement_text?: string
  status?: ComplianceRequirement['status']
  response_text?: string
  compliance_indicator?: ComplianceRequirement['compliance_indicator']
  order_index?: number
}

export interface AIResponseResult {
  response_text: string
  confidence_score: number
  supporting_evidence: string[]
}

// Add to api object:
export const api = {
  // ... existing methods ...

  compliance: {
    listRequirements: (rfpId: number, params?: { status?: string; type?: string; search?: string }) =>
      apiClient.get<ComplianceRequirementList>(`/compliance/rfps/${rfpId}/requirements`, { params }),

    createRequirement: (rfpId: number, data: CreateRequirementPayload) =>
      apiClient.post<ComplianceRequirement>(`/compliance/rfps/${rfpId}/requirements`, data),

    updateRequirement: (requirementId: number, data: UpdateRequirementPayload) =>
      apiClient.put<ComplianceRequirement>(`/compliance/requirements/${requirementId}`, data),

    deleteRequirement: (requirementId: number) =>
      apiClient.delete(`/compliance/requirements/${requirementId}`),

    bulkUpdateStatus: (rfpId: number, requirementIds: number[], status: string) =>
      apiClient.put(`/compliance/rfps/${rfpId}/requirements/bulk-status`, { requirement_ids: requirementIds, status }),

    reorderRequirements: (rfpId: number, requirementIds: number[]) =>
      apiClient.put(`/compliance/rfps/${rfpId}/requirements/reorder`, { requirement_ids: requirementIds }),

    extractRequirements: (rfpId: number, useLlm: boolean = true) =>
      apiClient.post(`/compliance/rfps/${rfpId}/extract-requirements`, { use_llm: useLlm }),

    generateAIResponse: (requirementId: number) =>
      apiClient.post<AIResponseResult>(`/compliance/requirements/${requirementId}/ai-response`),
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(frontend): add compliance API service functions"
```

---

### Task 8: Create ComplianceMatrix Component

**Files:**
- Create: `frontend/src/components/ComplianceMatrix.tsx`

**Step 1: Create the component**

```typescript
'use client'

import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Check,
  X,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Search,
  Download,
  Plus,
  Sparkles,
  RefreshCw,
  Trash2,
  GripVertical,
} from 'lucide-react'
import { toast } from 'sonner'
import { api, ComplianceRequirement, ComplianceRequirementList } from '@/services/api'

interface ComplianceMatrixProps {
  rfpId: number
}

const statusOptions = [
  { value: 'not_started', label: 'Not Started', color: 'secondary' },
  { value: 'in_progress', label: 'In Progress', color: 'warning' },
  { value: 'complete', label: 'Complete', color: 'success' },
  { value: 'not_applicable', label: 'N/A', color: 'outline' },
] as const

const typeOptions = [
  { value: 'mandatory', label: 'Mandatory', color: 'destructive' },
  { value: 'evaluation', label: 'Evaluation', color: 'default' },
  { value: 'performance', label: 'Performance', color: 'secondary' },
  { value: 'technical', label: 'Technical', color: 'outline' },
  { value: 'administrative', label: 'Administrative', color: 'outline' },
] as const

const ComplianceIndicator = ({ indicator }: { indicator: string | null }) => {
  if (!indicator) return <span className="text-muted-foreground">-</span>

  const icons = {
    compliant: <Check className="h-4 w-4 text-green-500" />,
    partial: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    non_compliant: <X className="h-4 w-4 text-red-500" />,
  }

  return icons[indicator as keyof typeof icons] || <span>-</span>
}

const TypeBadge = ({ type }: { type: string }) => {
  const option = typeOptions.find(t => t.value === type)
  return (
    <Badge variant={option?.color as any || 'secondary'}>
      {option?.label || type}
    </Badge>
  )
}

export function ComplianceMatrix({ rfpId }: ComplianceMatrixProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const [editingResponse, setEditingResponse] = useState<number | null>(null)
  const [responseText, setResponseText] = useState('')
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [newRequirement, setNewRequirement] = useState({
    requirement_id: '',
    requirement_text: '',
    requirement_type: 'mandatory' as const,
    source_document: '',
    source_section: '',
  })

  // Fetch requirements
  const { data, isLoading, refetch } = useQuery<ComplianceRequirementList>({
    queryKey: ['compliance-requirements', rfpId, statusFilter, typeFilter, searchQuery],
    queryFn: async () => {
      const params: any = {}
      if (statusFilter) params.status = statusFilter
      if (typeFilter) params.type = typeFilter
      if (searchQuery) params.search = searchQuery
      const response = await api.compliance.listRequirements(rfpId, params)
      return response.data
    },
  })

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) =>
      api.compliance.updateRequirement(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement updated')
    },
    onError: () => toast.error('Failed to update requirement'),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.compliance.createRequirement(rfpId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement added')
      setIsAddDialogOpen(false)
      setNewRequirement({
        requirement_id: '',
        requirement_text: '',
        requirement_type: 'mandatory',
        source_document: '',
        source_section: '',
      })
    },
    onError: () => toast.error('Failed to add requirement'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.compliance.deleteRequirement(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success('Requirement deleted')
    },
    onError: () => toast.error('Failed to delete requirement'),
  })

  const bulkUpdateMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: string }) =>
      api.compliance.bulkUpdateStatus(rfpId, ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      setSelectedIds(new Set())
      toast.success('Requirements updated')
    },
    onError: () => toast.error('Failed to update requirements'),
  })

  const extractMutation = useMutation({
    mutationFn: () => api.compliance.extractRequirements(rfpId),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['compliance-requirements', rfpId] })
      toast.success(`Extracted ${response.data.extracted_count} requirements`)
    },
    onError: () => toast.error('Failed to extract requirements'),
  })

  const aiResponseMutation = useMutation({
    mutationFn: (requirementId: number) => api.compliance.generateAIResponse(requirementId),
    onSuccess: (response, requirementId) => {
      setResponseText(response.data.response_text)
      toast.success('AI response generated')
    },
    onError: () => toast.error('Failed to generate AI response'),
  })

  // Toggle selection
  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  // Toggle expand
  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  // Handle status change
  const handleStatusChange = (id: number, status: string) => {
    updateMutation.mutate({ id, data: { status } })
  }

  // Handle response save
  const handleResponseSave = (id: number) => {
    updateMutation.mutate({
      id,
      data: {
        response_text: responseText,
        compliance_indicator: responseText ? 'compliant' : null,
      },
    })
    setEditingResponse(null)
  }

  // Export to CSV
  const exportToCSV = () => {
    if (!data?.requirements) return

    const headers = ['Req ID', 'Requirement', 'Type', 'Status', 'Response', 'Source']
    const rows = data.requirements.map(r => [
      r.requirement_id,
      r.requirement_text.replace(/"/g, '""'),
      r.requirement_type,
      r.status,
      (r.response_text || '').replace(/"/g, '""'),
      r.source_document || '',
    ])

    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `compliance-matrix-${rfpId}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Exported to CSV')
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const requirements = data?.requirements || []
  const summary = data ? {
    total: data.total,
    completed: data.completed,
    inProgress: data.in_progress,
    notStarted: data.not_started,
    complianceRate: data.compliance_rate,
  } : { total: 0, completed: 0, inProgress: 0, notStarted: 0, complianceRate: 0 }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Compliance Matrix</CardTitle>
            <CardDescription>
              {summary.total} requirements | {summary.completed} complete | {summary.complianceRate.toFixed(0)}% compliance
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => extractMutation.mutate()}
              disabled={extractMutation.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${extractMutation.isPending ? 'animate-spin' : ''}`} />
              Extract
            </Button>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add Requirement</DialogTitle>
                  <DialogDescription>Manually add a compliance requirement</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <Input
                    placeholder="Requirement ID (e.g., L.1.2)"
                    value={newRequirement.requirement_id}
                    onChange={e => setNewRequirement({ ...newRequirement, requirement_id: e.target.value })}
                  />
                  <Textarea
                    placeholder="Requirement text"
                    value={newRequirement.requirement_text}
                    onChange={e => setNewRequirement({ ...newRequirement, requirement_text: e.target.value })}
                  />
                  <Select
                    value={newRequirement.requirement_type}
                    onValueChange={(v: any) => setNewRequirement({ ...newRequirement, requirement_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {typeOptions.map(t => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    placeholder="Source document"
                    value={newRequirement.source_document}
                    onChange={e => setNewRequirement({ ...newRequirement, source_document: e.target.value })}
                  />
                  <Button
                    className="w-full"
                    onClick={() => createMutation.mutate(newRequirement)}
                    disabled={createMutation.isPending || !newRequirement.requirement_id || !newRequirement.requirement_text}
                  >
                    Add Requirement
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="outline" size="sm" onClick={exportToCSV}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Progress bar */}
        <Progress value={summary.complianceRate} className="mt-4" />

        {/* Filters */}
        <div className="mt-4 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search requirements..."
              className="pl-8"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <Select value={statusFilter || 'all'} onValueChange={v => setStatusFilter(v === 'all' ? null : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              {statusOptions.map(s => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={typeFilter || 'all'} onValueChange={v => setTypeFilter(v === 'all' ? null : v)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              {typeOptions.map(t => (
                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Bulk actions */}
        {selectedIds.size > 0 && (
          <div className="mt-4 flex items-center gap-2 rounded-md bg-muted p-2">
            <span className="text-sm">{selectedIds.size} selected</span>
            <Select onValueChange={status => bulkUpdateMutation.mutate({ ids: Array.from(selectedIds), status })}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Set status..." />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map(s => (
                  <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={() => setSelectedIds(new Set())}>
              Clear
            </Button>
          </div>
        )}
      </CardHeader>

      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={selectedIds.size === requirements.length && requirements.length > 0}
                  onCheckedChange={checked => {
                    if (checked) {
                      setSelectedIds(new Set(requirements.map(r => r.id)))
                    } else {
                      setSelectedIds(new Set())
                    }
                  }}
                />
              </TableHead>
              <TableHead className="w-10"></TableHead>
              <TableHead className="w-24">Req ID</TableHead>
              <TableHead>Requirement</TableHead>
              <TableHead className="w-32">Source</TableHead>
              <TableHead className="w-28">Type</TableHead>
              <TableHead className="w-36">Status</TableHead>
              <TableHead className="w-16 text-center">Comply</TableHead>
              <TableHead className="w-24">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requirements.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                  No requirements found. Click "Extract" to extract from documents or "Add" to add manually.
                </TableCell>
              </TableRow>
            ) : (
              requirements.map(req => (
                <React.Fragment key={req.id}>
                  <TableRow className="group">
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.has(req.id)}
                        onCheckedChange={() => toggleSelect(req.id)}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0"
                        onClick={() => toggleExpand(req.id)}
                      >
                        {expandedIds.has(req.id) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{req.requirement_id}</TableCell>
                    <TableCell className="max-w-md">
                      <p className="line-clamp-2">{req.requirement_text}</p>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {req.source_document && (
                        <div>
                          <div className="truncate">{req.source_document}</div>
                          {req.source_section && <div>{req.source_section}</div>}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={req.requirement_type} />
                    </TableCell>
                    <TableCell>
                      <Select
                        value={req.status}
                        onValueChange={v => handleStatusChange(req.id, v)}
                      >
                        <SelectTrigger className="h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {statusOptions.map(s => (
                            <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-center">
                      <ComplianceIndicator indicator={req.compliance_indicator} />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={() => {
                            setEditingResponse(req.id)
                            setResponseText(req.response_text || '')
                            toggleExpand(req.id)
                          }}
                        >
                          <Sparkles className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-destructive"
                          onClick={() => {
                            if (confirm('Delete this requirement?')) {
                              deleteMutation.mutate(req.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>

                  {/* Expanded row for response */}
                  {expandedIds.has(req.id) && (
                    <TableRow>
                      <TableCell colSpan={9} className="bg-muted/50">
                        <div className="p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="font-medium">Response</span>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setEditingResponse(req.id)
                                aiResponseMutation.mutate(req.id)
                              }}
                              disabled={aiResponseMutation.isPending}
                            >
                              <Sparkles className={`mr-2 h-4 w-4 ${aiResponseMutation.isPending ? 'animate-pulse' : ''}`} />
                              Generate with AI
                            </Button>
                          </div>

                          {editingResponse === req.id ? (
                            <div className="space-y-2">
                              <Textarea
                                value={responseText}
                                onChange={e => setResponseText(e.target.value)}
                                placeholder="Enter compliance response..."
                                rows={4}
                              />
                              <div className="flex gap-2">
                                <Button size="sm" onClick={() => handleResponseSave(req.id)}>
                                  Save
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    setEditingResponse(null)
                                    setResponseText('')
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div
                              className="text-sm cursor-pointer hover:bg-muted p-2 rounded"
                              onClick={() => {
                                setEditingResponse(req.id)
                                setResponseText(req.response_text || '')
                              }}
                            >
                              {req.response_text || (
                                <span className="text-muted-foreground italic">
                                  Click to add response or use AI to generate
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ComplianceMatrix.tsx
git commit -m "feat(frontend): add interactive ComplianceMatrix component"
```

---

### Task 9: Integrate ComplianceMatrix into RFP Detail Page

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx`

**Step 1: Find the tabs section in RFPDetail.tsx**

Look for the existing tabs (Documents, Pricing, Chat, etc.)

**Step 2: Add compliance tab import**

Add at the top:

```typescript
import { ComplianceMatrix } from '@/components/ComplianceMatrix'
```

**Step 3: Add Compliance tab**

Find the TabsList and add a new tab trigger:

```typescript
<TabsTrigger value="compliance">Compliance</TabsTrigger>
```

**Step 4: Add Compliance tab content**

Find the TabsContent sections and add:

```typescript
<TabsContent value="compliance" className="space-y-4">
  <ComplianceMatrix rfpId={rfp.id} />
</TabsContent>
```

**Step 5: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx
git commit -m "feat(frontend): integrate ComplianceMatrix into RFP detail page"
```

---

## Phase 5: Testing & Verification

### Task 10: End-to-End Testing

**Step 1: Restart backend**

Run: `docker-compose restart backend`

**Step 2: Verify database migration**

Check: `docker exec -it rfp_ml-db-1 psql -U postgres -d rfp_db -c "SELECT * FROM compliance_requirements LIMIT 1;"`

**Step 3: Test API endpoints manually**

```bash
# List requirements (should be empty)
curl http://localhost:8000/api/v1/compliance/rfps/1/requirements

# Create a requirement
curl -X POST http://localhost:8000/api/v1/compliance/rfps/1/requirements \
  -H "Content-Type: application/json" \
  -d '{"requirement_id":"TEST.1","requirement_text":"Test requirement","requirement_type":"mandatory"}'

# Update requirement
curl -X PUT http://localhost:8000/api/v1/compliance/requirements/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress"}'

# Extract requirements
curl -X POST http://localhost:8000/api/v1/compliance/rfps/1/extract-requirements
```

**Step 4: Test frontend**

1. Navigate to an RFP detail page
2. Click on the "Compliance" tab
3. Test "Extract" button
4. Test "Add" button to add manual requirement
5. Test status dropdown changes
6. Test expand/collapse for response editing
7. Test "Generate with AI" button
8. Test bulk selection and status update
9. Test export to CSV
10. Test search and filters

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found during E2E testing"
```

---

### Task 11: Final Cleanup

**Step 1: Run linting**

```bash
cd frontend && npm run lint
cd ../api && ruff check .
```

**Step 2: Fix any linting issues**

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and linting fixes"
```

---

## Summary

**Total Tasks:** 11

**Files Created:**
- `api/tests/test_compliance_requirement_model.py`
- `api/tests/test_compliance_routes.py`
- `api/app/schemas/compliance.py`
- `api/app/routes/compliance.py`
- `frontend/src/components/ComplianceMatrix.tsx`
- Migration file in `api/alembic/versions/`

**Files Modified:**
- `api/app/models/database.py` (new model + enums)
- `api/app/main.py` (register router)
- `frontend/src/services/api.ts` (API functions)
- `frontend/src/pages/RFPDetail.tsx` (tab integration)

**Key Features Implemented:**
1. Database model for individual requirements with status tracking
2. Full CRUD API endpoints with filtering and search
3. Bulk status update and reordering
4. LLM-powered requirement extraction from documents
5. AI-assisted response generation with RAG context
6. Interactive React component with:
   - Progress tracking
   - Inline editing
   - Type/status badges
   - Filtering and search
   - CSV export
   - Expandable response editor
