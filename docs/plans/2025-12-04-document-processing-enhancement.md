# Document Processing Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance existing document processing to include uploaded documents in compliance requirement extraction, add OCR support, and improve requirement traceability.

**Architecture:** Uploaded documents are already processed and indexed in ChromaDB. This plan connects that indexed content to the compliance extraction pipeline, adds OCR fallback for scanned PDFs, and improves source tracking.

**Tech Stack:** FastAPI, Python, ChromaDB, PyPDF2, pdfplumber, python-docx, pytesseract (OCR), React, TypeScript

---

## Current State Assessment

| Component | Status | Location |
|-----------|--------|----------|
| RFPDocument model | ✅ Complete | `api/app/models/database.py:527-572` |
| Document upload route | ✅ Complete | `api/app/routes/documents.py` |
| Text extraction | ✅ Partial | `src/utils/document_reader.py` |
| ChromaDB RAG | ✅ Complete | `src/rag/chroma_rag_engine.py` |
| Compliance extraction | ⚠️ Needs enhancement | `api/app/routes/compliance.py:221-336` |
| Frontend Documents tab | ✅ Complete | `frontend/src/pages/RFPDetail.tsx:942-1069` |
| OCR support | ❌ Missing | - |
| Document content endpoint | ❌ Missing | - |

**Gap Analysis:** Compliance extraction currently only uses RFP description + Q&A. Uploaded document content is indexed in ChromaDB but not passed to requirement extraction.

---

### Task 1: Add Document Content to Compliance Extraction

**Files:**
- Modify: `api/app/routes/compliance.py`

**Step 1: Read current extract_requirements endpoint**

Run: `grep -n "extract-requirements" api/app/routes/compliance.py`

Review how requirements are currently extracted.

**Step 2: Update extract_requirements to include document content**

Find the `extract_requirements` function and add document content retrieval:

```python
# Add import at top
from app.routes.documents import get_uploaded_documents, extract_text_from_file, DOCUMENT_STORAGE

# In extract_requirements function, after getting RFP data:

# Get uploaded document content
uploaded_docs = []
try:
    upload_dir = get_document_upload_dir(str(rfp.id))
    if upload_dir.exists():
        for doc_file in upload_dir.iterdir():
            if doc_file.is_file():
                try:
                    text = extract_text_from_file(doc_file)
                    if text:
                        uploaded_docs.append({
                            "filename": doc_file.name,
                            "content": text[:20000]  # Limit per doc
                        })
                except Exception:
                    pass
except Exception:
    pass

# Get scraped document content
scraped_docs = []
for doc in rfp.documents:
    if doc.file_path and Path(doc.file_path).exists():
        try:
            text = extract_text_from_file(Path(doc.file_path))
            if text:
                scraped_docs.append({
                    "filename": doc.filename,
                    "content": text[:20000]
                })
        except Exception:
            pass

# Combine all content for extraction
document_content = ""
for doc in uploaded_docs + scraped_docs:
    document_content += f"\n\n=== Document: {doc['filename']} ===\n{doc['content']}"

# Update the context passed to LLM extraction
full_context = f"""
RFP Title: {rfp.title}
Agency: {rfp.agency or 'Unknown'}
Description: {rfp.description or 'No description'}

Q&A Responses:
{qa_content}

Attached Documents:
{document_content[:50000]}  # Total limit
"""
```

**Step 3: Test import**

Run: `cd api && python -c "from app.routes import compliance; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add api/app/routes/compliance.py
git commit -m "feat(compliance): include document content in requirement extraction"
```

---

### Task 2: Add OCR Support for Scanned PDFs

**Files:**
- Modify: `api/app/routes/documents.py`
- Modify: `requirements_api.txt`

**Step 1: Add OCR dependencies**

Add to `requirements_api.txt`:

```
pytesseract>=0.3.10
pdf2image>=1.16.3
Pillow>=10.0.0
```

**Step 2: Update extract_text_from_file with OCR fallback**

In `api/app/routes/documents.py`, enhance the PDF extraction:

```python
def extract_text_from_file(filepath: Path) -> str:
    """Extract text from various file formats with OCR fallback for PDFs."""
    suffix = filepath.suffix.lower()
    text = ""

    if suffix == ".pdf":
        # Try text extraction first
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(filepath))
            for page in doc:
                page_text = page.get_text()
                text += page_text + "\n"
            doc.close()
        except ImportError:
            try:
                import pdfplumber
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        text += page_text + "\n"
            except ImportError:
                pass

        # If very little text extracted, try OCR
        if len(text.strip()) < 100:
            try:
                from pdf2image import convert_from_path
                import pytesseract

                images = convert_from_path(str(filepath), dpi=200, first_page=1, last_page=20)
                ocr_text = ""
                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(image)
                    ocr_text += f"\n[Page {i+1}]\n{page_text}"

                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
            except ImportError:
                logger.warning("OCR libraries not available for scanned PDF")
            except Exception as e:
                logger.warning(f"OCR failed: {e}")

    # ... rest of existing code for docx, xlsx, txt ...

    return text.strip()
```

**Step 3: Test import**

Run: `cd api && python -c "from app.routes import documents; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add api/app/routes/documents.py requirements_api.txt
git commit -m "feat(documents): add OCR fallback for scanned PDFs"
```

---

### Task 3: Add Document Content Retrieval Endpoint

**Files:**
- Modify: `api/app/routes/documents.py`

**Step 1: Add get_document_content endpoint**

```python
@router.get("/{rfp_id}/uploads/{document_id}/content")
async def get_document_content(
    rfp: RFPDep,
    document_id: str,
):
    """Get extracted text content from an uploaded document."""
    upload_dir = get_document_upload_dir(str(rfp.id))

    # Find the document file
    matching_files = list(upload_dir.glob(f"{document_id}.*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = matching_files[0]

    try:
        text = extract_text_from_file(filepath)
        return {
            "document_id": document_id,
            "filename": filepath.name,
            "content": text,
            "char_count": len(text),
            "word_count": len(text.split()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract content: {str(e)}")
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import documents; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/documents.py
git commit -m "feat(documents): add content retrieval endpoint"
```

---

### Task 4: Add Document Download Endpoint

**Files:**
- Modify: `api/app/routes/documents.py`

**Step 1: Add download endpoint**

```python
from fastapi.responses import FileResponse

@router.get("/{rfp_id}/uploads/{document_id}/download")
async def download_document(
    rfp: RFPDep,
    document_id: str,
):
    """Download an uploaded document."""
    upload_dir = get_document_upload_dir(str(rfp.id))

    # Find the document file
    matching_files = list(upload_dir.glob(f"{document_id}.*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = matching_files[0]

    # Get original filename from storage if available
    doc_info = DOCUMENT_STORAGE.get(document_id, {})
    original_filename = doc_info.get("filename", filepath.name)

    return FileResponse(
        path=str(filepath),
        filename=original_filename,
        media_type="application/octet-stream"
    )
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import documents; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/documents.py
git commit -m "feat(documents): add download endpoint for uploaded files"
```

---

### Task 5: Update Frontend API Client

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add new API methods**

```typescript
// Document content and download methods
getDocumentContent: (rfpId: string, documentId: string) =>
  apiClient.get(`/documents/${rfpId}/uploads/${documentId}/content`)
    .then(res => res.data),

downloadUploadedDocument: (rfpId: string, documentId: string) =>
  apiClient.get(`/documents/${rfpId}/uploads/${documentId}/download`, {
    responseType: 'blob'
  }).then(res => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    // Get filename from content-disposition header if available
    const disposition = res.headers['content-disposition']
    let filename = `document-${documentId}`
    if (disposition) {
      const match = disposition.match(/filename="?([^"]+)"?/)
      if (match) filename = match[1]
    }
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }),
```

**Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add document content and download methods"
```

---

### Task 6: Add Download Button to Documents Tab

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx`

**Step 1: Find the uploaded documents section**

Run: `grep -n "uploaded_documents" frontend/src/pages/RFPDetail.tsx | head -10`

**Step 2: Add download button next to delete button**

Find the document list item and add a download button:

```typescript
<Button
  variant="ghost"
  size="icon"
  onClick={() => api.downloadUploadedDocument(rfpId, doc.document_id)}
  title="Download"
>
  <Download className="h-4 w-4" />
</Button>
```

**Step 3: Add Download import if missing**

```typescript
import { Download } from 'lucide-react'
```

**Step 4: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx
git commit -m "feat(ui): add download button for uploaded documents"
```

---

### Task 7: Enhance Requirement Source Tracking

**Files:**
- Modify: `api/app/routes/compliance.py`

**Step 1: Update extraction to include document source**

When extracting requirements, include source document info in metadata:

```python
# In the LLM prompt for requirement extraction, add:
"""
For each requirement, identify:
- source_document: filename where requirement was found
- source_section: section name or heading
- source_page: approximate page number if known

Format each requirement with this metadata.
"""

# Parse LLM response to extract source information
for req in extracted_requirements:
    req.source_document = req.get("source_document", "RFP Description")
    req.source_section = req.get("source_section", "")
    req.source_page = req.get("source_page")
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import compliance; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add api/app/routes/compliance.py
git commit -m "feat(compliance): enhance requirement source tracking"
```

---

### Task 8: Add Document Processing Status Persistence

**Files:**
- Modify: `api/app/models/database.py`
- Modify: `api/app/routes/documents.py`

**Step 1: Add UploadedDocument model (if not using RFPDocument)**

Check if we should use RFPDocument or create a new model. Since RFPDocument already has all needed fields, we'll enhance its usage:

```python
# In documents.py, update to persist to database instead of in-memory dict:

from app.models.database import RFPDocument

# In upload_document endpoint, after saving file:
db_doc = RFPDocument(
    rfp_id=rfp.id,
    filename=file.filename,
    file_path=str(filepath),
    file_type=file_ext.lstrip('.'),
    file_size=len(content),
    document_type="attachment",  # User uploaded
)
db.add(db_doc)
db.commit()
```

**Step 2: Update list endpoint to query database**

```python
@router.get("/{rfp_id}/uploads")
async def get_uploaded_documents(rfp: RFPDep, db: DBDep):
    """Get all uploaded documents for an RFP."""
    docs = db.query(RFPDocument).filter(
        RFPDocument.rfp_id == rfp.id,
        RFPDocument.document_type == "attachment"
    ).all()

    return [{
        "document_id": f"doc-{doc.id}",
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": "completed",  # Check actual status
        "uploaded_at": doc.created_at.isoformat(),
    } for doc in docs]
```

**Step 3: Test import**

Run: `cd api && python -c "from app.routes import documents; print('OK')"`

Expected: `OK`

**Step 4: Commit**

```bash
git add api/app/models/database.py api/app/routes/documents.py
git commit -m "feat(documents): persist uploaded documents to database"
```

---

### Task 9: Integration Testing

**Files:**
- Create: `api/tests/test_document_processing.py`

**Step 1: Create test file**

```python
"""Tests for document processing enhancements."""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile

from app.main import app

client = TestClient(app)


def test_document_upload():
    """Test document upload endpoint."""
    # Get an RFP
    response = client.get("/api/v1/rfps/discovered")
    if not response.json():
        pytest.skip("No RFPs available")

    rfp_id = response.json()[0]["id"]

    # Create a test file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Test document content with requirements.\n")
        f.write(b"The contractor SHALL provide monthly reports.\n")
        test_file = f.name

    # Upload
    with open(test_file, "rb") as f:
        response = client.post(
            f"/api/v1/documents/{rfp_id}/upload",
            files={"file": ("test.txt", f, "text/plain")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data

    # Cleanup
    Path(test_file).unlink()


def test_list_uploaded_documents():
    """Test listing uploaded documents."""
    response = client.get("/api/v1/rfps/discovered")
    if not response.json():
        pytest.skip("No RFPs available")

    rfp_id = response.json()[0]["id"]

    response = client.get(f"/api/v1/documents/{rfp_id}/uploads")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: Run tests**

Run: `cd api && python -m pytest tests/test_document_processing.py -v 2>&1 | head -30`

Expected: Tests pass or skip gracefully

**Step 3: Commit**

```bash
git add api/tests/test_document_processing.py
git commit -m "test(documents): add document processing integration tests"
```

---

### Task 10: Final Verification

**Step 1: Rebuild containers**

Run: `docker-compose build backend && docker-compose up -d backend`

**Step 2: Verify backend logs**

Run: `docker-compose logs backend --tail=20`

Expected: No errors, server started successfully

**Step 3: Rebuild frontend**

Run: `docker-compose build frontend && docker-compose up -d frontend`

**Step 4: Manual testing checklist**

- [ ] Navigate to RFP detail page
- [ ] Go to Documents tab
- [ ] Upload a test PDF/DOCX file
- [ ] Verify upload progress shows
- [ ] Verify file appears in list when complete
- [ ] Test download button works
- [ ] Go to Compliance tab
- [ ] Click "Extract Requirements"
- [ ] Verify requirements include document content
- [ ] Check source_document field in extracted requirements

**Step 5: Final commit**

```bash
git add .
git commit -m "feat(documents): complete document processing enhancement"
```

---

## Summary

This plan enhances existing document infrastructure:

1. **Backend** (Tasks 1-4, 7-8): Include document content in compliance extraction, add OCR, add content/download endpoints, persist to database
2. **Frontend** (Tasks 5-6): Add API methods and download button
3. **Testing** (Tasks 9-10): Integration tests and verification

**Total Tasks:** 10
**Risk Level:** Low (building on existing solid foundation)
**Key Enhancement:** Documents now flow into compliance requirement extraction
