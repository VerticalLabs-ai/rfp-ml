# Implementation Plan: Import from URL

**Date**: 2025-12-04
**Feature**: Universal URL Import for RFPs from Any Government Contracting Website

## Overview

Extend the existing scraper infrastructure to support importing RFPs from ANY government contracting website URL, not just BeaconBid. The system will:
1. Detect the source type (SAM.gov, state portals, generic)
2. Use platform-specific parsers when available
3. Fall back to AI-powered extraction for unknown sites
4. Provide preview/edit functionality before saving
5. Include duplicate detection

## Current Architecture Analysis

### Existing Infrastructure (Reuse)
- **Base scraper**: `src/agents/scrapers/base_scraper.py` - Abstract class with `ScrapedRFP`, `ScrapedDocument`, `ScrapedQA` dataclasses
- **BeaconBid scraper**: `src/agents/scrapers/beaconbid_scraper.py` - Stagehand/Browserbase AI-powered extraction (proven pattern)
- **Scraper routes**: `api/app/routes/scraper.py` - `/scrape`, `/refresh`, `/documents`, `/qa` endpoints
- **Import dialog**: `frontend/src/components/ImportRFPDialog.tsx` - Dialog with URL input, company profile selection, progress states
- **Database models**: `RFPOpportunity`, `RFPDocument`, `RFPQandA` in `api/app/models/database.py`

### Key Design Decision
The existing BeaconBid scraper uses **Stagehand + Browserbase** for AI-powered extraction. This pattern works for ANY website since it uses LLM-based content understanding rather than CSS selectors. We will:
1. Create a **GenericWebScraper** that uses the same Stagehand pattern
2. Add **platform-specific scrapers** (SAM.gov) that can use structured APIs when available
3. Extend the frontend to support **preview before save** and **field editing**

---

## Implementation Tasks

### Phase 1: Backend - Generic Web Scraper

#### Task 1.1: Create GenericWebScraper Class
**File**: `src/agents/scrapers/generic_web_scraper.py` (NEW)

Create a generic scraper that uses Stagehand AI extraction for any website:

```python
"""
Generic web scraper for importing RFPs from any government website.
Uses Stagehand's AI-powered extraction to handle unknown page structures.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .base_scraper import (
    BaseScraper,
    ScrapedDocument,
    ScrapedQA,
    ScrapedRFP,
    ScraperError,
    ScraperParseError,
)

logger = logging.getLogger(__name__)


class GenericWebScraper(BaseScraper):
    """
    Generic scraper for any government RFP website.

    Uses Stagehand with Browserbase for AI-powered extraction.
    Works with unknown page layouts by using LLM understanding.
    """

    PLATFORM_NAME = "generic"
    SUPPORTED_DOMAINS: list[str] = []  # Accepts any domain as fallback

    def __init__(
        self,
        document_storage_path: str = "data/rfp_documents",
        browserbase_project_id: str | None = None,
        browserbase_api_key: str | None = None,
        model_api_key: str | None = None,
    ):
        """Initialize with same config as BeaconBidScraper."""
        super().__init__(document_storage_path)
        # ... (same env var loading as BeaconBidScraper)

    def is_valid_url(self, url: str) -> bool:
        """Accept any HTTP/HTTPS URL as fallback scraper."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    async def scrape(self, url: str) -> ScrapedRFP:
        """Scrape RFP using AI extraction."""
        # Use same Stagehand pattern as BeaconBidScraper
        # Enhanced prompts for generic government RFP extraction

    async def download_documents(self, rfp: ScrapedRFP, rfp_id: str) -> list[ScrapedDocument]:
        """Download documents - try direct HTTP first, fall back to browser."""
        # Simpler than BeaconBid - most gov sites allow direct downloads

    async def refresh(self, url: str, existing_checksum: str | None = None) -> dict[str, Any]:
        """Check for updates."""
        # Same pattern as BeaconBidScraper
```

**Extraction prompts to include**:
- Government-specific field detection (solicitation number, NAICS, PSC, set-aside type)
- Multiple date format handling (response deadline, posted date, award date)
- Document attachment detection (PDFs, DOCx, XLSx in tables/links)
- Q&A section detection (if present)

---

#### Task 1.2: Create SAM.gov Scraper (Structured API)
**File**: `src/agents/scrapers/sam_gov_scraper.py` (NEW)

SAM.gov has a public API - use it when available:

```python
"""
SAM.gov scraper using the public API for structured data extraction.
Falls back to Stagehand for pages without API support.
"""

import aiohttp
from .base_scraper import BaseScraper, ScrapedRFP, ScrapedDocument


class SAMGovScraper(BaseScraper):
    """
    Scraper for SAM.gov (beta.sam.gov) opportunities.

    Uses SAM.gov public API for structured data when possible,
    with Stagehand fallback for complex pages.
    """

    PLATFORM_NAME = "sam.gov"
    SUPPORTED_DOMAINS = ["sam.gov", "beta.sam.gov", "www.sam.gov"]

    SAM_API_BASE = "https://api.sam.gov/opportunities/v2"

    async def scrape(self, url: str) -> ScrapedRFP:
        """
        Extract opportunity ID from URL and fetch via API.

        URL patterns:
        - https://sam.gov/opp/{opportunity_id}/view
        - https://beta.sam.gov/opp/{opportunity_id}/view
        """
        opp_id = self._extract_opportunity_id(url)
        if opp_id:
            try:
                return await self._scrape_via_api(opp_id)
            except Exception:
                pass  # Fall through to Stagehand

        # Fallback to Stagehand extraction
        return await self._scrape_via_stagehand(url)

    def _extract_opportunity_id(self, url: str) -> str | None:
        """Extract opportunity ID from SAM.gov URL."""
        # Pattern: /opp/{id}/view
        import re
        match = re.search(r'/opp/([a-f0-9-]+)/view', url)
        return match.group(1) if match else None

    async def _scrape_via_api(self, opp_id: str) -> ScrapedRFP:
        """Fetch opportunity data from SAM.gov API."""
        # API call with proper authentication
        # Returns structured JSON data
```

---

#### Task 1.3: Update Scraper Registry
**File**: `api/app/routes/scraper.py` (MODIFY lines 88-98)

Update `get_scraper()` to support multiple scrapers with priority:

```python
def get_scraper(url: str):
    """
    Get the appropriate scraper for a URL.

    Priority order:
    1. Platform-specific scrapers (BeaconBid, SAM.gov)
    2. Generic web scraper (fallback for any URL)
    """
    from src.agents.scrapers import BeaconBidScraper, SAMGovScraper, GenericWebScraper

    # Platform-specific scrapers in priority order
    scrapers = [
        BeaconBidScraper(),
        SAMGovScraper(),
    ]

    for scraper in scrapers:
        if scraper.is_valid_url(url):
            return scraper

    # Fallback: GenericWebScraper accepts any HTTP(S) URL
    generic = GenericWebScraper()
    if generic.is_valid_url(url):
        return generic

    return None
```

---

#### Task 1.4: Update Scraper Package Exports
**File**: `src/agents/scrapers/__init__.py` (MODIFY)

```python
"""RFP Scrapers package for extracting RFP data from various portals."""
from .base_scraper import BaseScraper, ScrapedDocument, ScrapedQA, ScrapedRFP
from .beaconbid_scraper import BeaconBidScraper
from .sam_gov_scraper import SAMGovScraper
from .generic_web_scraper import GenericWebScraper

__all__ = [
    "BaseScraper",
    "ScrapedRFP",
    "ScrapedDocument",
    "ScrapedQA",
    "BeaconBidScraper",
    "SAMGovScraper",
    "GenericWebScraper",
]
```

---

### Phase 2: Backend - Preview & Confirm Flow

#### Task 2.1: Add Preview Endpoint
**File**: `api/app/routes/scraper.py` (ADD new endpoint)

Add endpoint that extracts data WITHOUT saving to database:

```python
class PreviewRequest(BaseModel):
    url: str

class PreviewResponse(BaseModel):
    """Preview of extracted RFP data before saving."""
    source_url: str
    source_platform: str
    detected_fields: dict[str, Any]  # All extracted fields
    documents: list[dict]  # Document info (not downloaded yet)
    qa_items: list[dict]  # Q&A items
    duplicate_check: dict | None  # Existing RFP if URL already imported


@router.post("/preview", response_model=PreviewResponse)
async def preview_rfp(request: PreviewRequest, db: DBDep):
    """
    Extract RFP data from URL without saving.

    Returns extracted data for user review/editing before confirming import.
    """
    url = request.url

    # Check for duplicates first
    existing = db.query(RFPOpportunity).filter(
        RFPOpportunity.source_url == url
    ).first()

    duplicate_check = None
    if existing:
        duplicate_check = {
            "rfp_id": existing.rfp_id,
            "title": existing.title,
            "imported_at": existing.discovered_at.isoformat() if existing.discovered_at else None,
        }

    # Get appropriate scraper
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(status_code=400, detail="URL not supported")

    # Scrape without saving
    scraped = await scraper.scrape(url)

    return PreviewResponse(
        source_url=url,
        source_platform=scraped.source_platform,
        detected_fields={
            "title": scraped.title,
            "solicitation_number": scraped.solicitation_number,
            "agency": scraped.agency,
            "office": scraped.office,
            "description": scraped.description,
            "posted_date": scraped.posted_date.isoformat() if scraped.posted_date else None,
            "response_deadline": scraped.response_deadline.isoformat() if scraped.response_deadline else None,
            "naics_code": scraped.naics_code,
            "category": scraped.category,
            "estimated_value": scraped.estimated_value,
        },
        documents=[
            {"filename": d.filename, "source_url": d.source_url, "file_type": d.file_type}
            for d in scraped.documents
        ],
        qa_items=[
            {"question": q.question_text, "answer": q.answer_text, "number": q.question_number}
            for q in scraped.qa_items
        ],
        duplicate_check=duplicate_check,
    )
```

---

#### Task 2.2: Add Confirm Import Endpoint
**File**: `api/app/routes/scraper.py` (ADD new endpoint)

Allow saving with user-edited data:

```python
class ConfirmImportRequest(BaseModel):
    """Request to confirm and save a previewed RFP with optional edits."""
    source_url: str
    company_profile_id: int | None = None
    # User can override any field
    overrides: dict[str, Any] = {}  # {"title": "Edited Title", "naics_code": "541511"}


@router.post("/confirm", response_model=ScrapeResponse)
async def confirm_import(
    request: ConfirmImportRequest,
    background_tasks: BackgroundTasks,
    db: DBDep,
):
    """
    Confirm import of a previewed RFP with optional field overrides.

    User can edit extracted fields before saving.
    """
    url = request.source_url

    # Check for duplicates
    existing = db.query(RFPOpportunity).filter(
        RFPOpportunity.source_url == url
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"RFP already exists: {existing.rfp_id}. Use refresh to update.",
        )

    # Re-scrape (or use cached preview - enhancement for later)
    scraper = get_scraper(url)
    scraped = await scraper.scrape(url)

    # Apply user overrides
    if request.overrides:
        if "title" in request.overrides:
            scraped.title = request.overrides["title"]
        if "solicitation_number" in request.overrides:
            scraped.solicitation_number = request.overrides["solicitation_number"]
        # ... handle all overridable fields
        scraped.compute_checksum()  # Recompute after changes

    # Save to database (same logic as existing /scrape endpoint)
    # ... create RFPOpportunity, save Q&A, trigger background document download
```

---

### Phase 3: Frontend - Enhanced Import Dialog

#### Task 3.1: Create Preview State Types
**File**: `frontend/src/types/import.ts` (NEW)

```typescript
export interface PreviewData {
  source_url: string
  source_platform: string
  detected_fields: {
    title: string | null
    solicitation_number: string | null
    agency: string | null
    office: string | null
    description: string | null
    posted_date: string | null
    response_deadline: string | null
    naics_code: string | null
    category: string | null
    estimated_value: number | null
  }
  documents: Array<{
    filename: string
    source_url: string
    file_type: string | null
  }>
  qa_items: Array<{
    question: string
    answer: string | null
    number: string | null
  }>
  duplicate_check: {
    rfp_id: string
    title: string
    imported_at: string | null
  } | null
}

export interface EditableFields {
  title: string
  solicitation_number: string
  agency: string
  office: string
  description: string
  naics_code: string
  category: string
}
```

---

#### Task 3.2: Update ImportRFPDialog Component
**File**: `frontend/src/components/ImportRFPDialog.tsx` (MODIFY)

Extend the existing dialog with a 3-step flow:

```typescript
// Step 1: URL Input
// Step 2: Preview & Edit (NEW)
// Step 3: Confirm & Import

export function ImportRFPDialog({ trigger, onSuccess }: ImportRFPDialogProps) {
  const [step, setStep] = useState<'url' | 'preview' | 'importing'>('url')
  const [url, setUrl] = useState('')
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [editedFields, setEditedFields] = useState<EditableFields | null>(null)

  // Preview mutation - extract without saving
  const previewMutation = useMutation({
    mutationFn: (url: string) => api.post<PreviewData>('/scraper/preview', { url }),
    onSuccess: (data) => {
      setPreviewData(data)
      setEditedFields({
        title: data.detected_fields.title || '',
        solicitation_number: data.detected_fields.solicitation_number || '',
        agency: data.detected_fields.agency || '',
        office: data.detected_fields.office || '',
        description: data.detected_fields.description || '',
        naics_code: data.detected_fields.naics_code || '',
        category: data.detected_fields.category || '',
      })
      setStep('preview')
    },
  })

  // Confirm mutation - save with edits
  const confirmMutation = useMutation({
    mutationFn: (data: { source_url: string; company_profile_id?: number; overrides: object }) =>
      api.post<ScrapeResponse>('/scraper/confirm', data),
    onSuccess: (data) => {
      toast.success(`RFP imported: ${data.title}`)
      onSuccess?.(data.rfp_id)
    },
  })

  return (
    <Dialog>
      {step === 'url' && (
        // Existing URL input UI
        // Remove beaconbid.com validation - accept any URL
        // Add "Preview" button instead of direct "Import"
      )}

      {step === 'preview' && previewData && (
        // NEW: Preview & Edit step
        <div className="space-y-4">
          {/* Duplicate warning if exists */}
          {previewData.duplicate_check && (
            <Alert variant="warning">
              This URL was already imported as {previewData.duplicate_check.rfp_id}
            </Alert>
          )}

          {/* Platform badge */}
          <Badge>{previewData.source_platform}</Badge>

          {/* Editable fields */}
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Title"
              value={editedFields?.title}
              onChange={(e) => setEditedFields({...editedFields, title: e.target.value})}
            />
            <Input
              label="Solicitation Number"
              value={editedFields?.solicitation_number}
              onChange={...}
            />
            {/* More fields... */}
          </div>

          {/* Documents preview (read-only) */}
          <div>
            <h4>Documents ({previewData.documents.length})</h4>
            {previewData.documents.map(doc => (
              <div key={doc.filename}>{doc.filename}</div>
            ))}
          </div>

          {/* Q&A preview (read-only) */}
          <div>
            <h4>Q&A ({previewData.qa_items.length})</h4>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setStep('url')}>Back</Button>
            <Button
              onClick={() => confirmMutation.mutate({
                source_url: url,
                company_profile_id: selectedProfileId,
                overrides: editedFields,
              })}
              disabled={!!previewData.duplicate_check}
            >
              Import RFP
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  )
}
```

---

#### Task 3.3: Update URL Validation
**File**: `frontend/src/components/ImportRFPDialog.tsx` (MODIFY)

Remove BeaconBid-only validation:

```typescript
// OLD:
const isValidUrl = (urlString: string) => {
  try {
    const parsed = new URL(urlString)
    return parsed.hostname.includes('beaconbid.com')  // REMOVE THIS
  } catch {
    return false
  }
}

// NEW:
const isValidUrl = (urlString: string) => {
  try {
    const parsed = new URL(urlString)
    return ['http:', 'https:'].includes(parsed.protocol)
  } catch {
    return false
  }
}
```

Also update the placeholder and description text:
- OLD: "Paste a BeaconBid URL to automatically import..."
- NEW: "Paste any government contracting URL to automatically import the RFP..."

---

### Phase 4: API Client Updates

#### Task 4.1: Add New API Methods
**File**: `frontend/src/lib/api.ts` or `frontend/src/services/api.ts` (MODIFY)

```typescript
export const api = {
  // ... existing methods

  // Scraper endpoints
  previewRfp: (url: string) =>
    apiClient.post<PreviewData>('/scraper/preview', { url }),

  confirmImport: (data: {
    source_url: string
    company_profile_id?: number
    overrides?: Record<string, unknown>
  }) =>
    apiClient.post<ScrapeResponse>('/scraper/confirm', data),
}
```

---

### Phase 5: Testing & Validation

#### Task 5.1: Test GenericWebScraper
**File**: `tests/test_generic_scraper.py` (NEW)

```python
"""Tests for GenericWebScraper."""
import pytest
from src.agents.scrapers import GenericWebScraper


@pytest.fixture
def scraper():
    return GenericWebScraper()


class TestGenericWebScraper:
    def test_accepts_any_https_url(self, scraper):
        assert scraper.is_valid_url("https://example.gov/rfp/123")
        assert scraper.is_valid_url("https://procurement.state.gov/bid")
        assert not scraper.is_valid_url("ftp://example.com")
        assert not scraper.is_valid_url("not-a-url")

    @pytest.mark.asyncio
    async def test_scrape_extracts_title(self, scraper):
        # Test with a known public RFP page
        # (Use a stable test URL or mock)
        pass
```

#### Task 5.2: Test SAMGovScraper
**File**: `tests/test_sam_gov_scraper.py` (NEW)

```python
"""Tests for SAMGovScraper."""
import pytest
from src.agents.scrapers import SAMGovScraper


class TestSAMGovScraper:
    def test_extracts_opportunity_id(self):
        scraper = SAMGovScraper()
        assert scraper._extract_opportunity_id(
            "https://sam.gov/opp/abc123-def456/view"
        ) == "abc123-def456"

    def test_supported_domains(self):
        scraper = SAMGovScraper()
        assert scraper.is_valid_url("https://sam.gov/opp/123/view")
        assert scraper.is_valid_url("https://beta.sam.gov/opp/123/view")
        assert not scraper.is_valid_url("https://beaconbid.com/rfp/123")
```

#### Task 5.3: Test Preview/Confirm Flow
**File**: `tests/test_import_flow.py` (NEW)

```python
"""Integration tests for import preview/confirm flow."""
import pytest
from fastapi.testclient import TestClient


class TestImportFlow:
    def test_preview_returns_extracted_data(self, client: TestClient):
        response = client.post("/api/v1/scraper/preview", json={
            "url": "https://test-rfp-site.gov/opportunity/123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "detected_fields" in data
        assert "documents" in data

    def test_confirm_saves_with_overrides(self, client: TestClient, db):
        response = client.post("/api/v1/scraper/confirm", json={
            "source_url": "https://test-rfp-site.gov/opportunity/123",
            "overrides": {"title": "Custom Title"}
        })
        assert response.status_code == 200
        # Verify RFP saved with custom title
```

---

## File Summary

### New Files
| File | Purpose |
|------|---------|
| `src/agents/scrapers/generic_web_scraper.py` | Universal scraper using Stagehand AI extraction |
| `src/agents/scrapers/sam_gov_scraper.py` | SAM.gov-specific scraper with API support |
| `frontend/src/types/import.ts` | TypeScript types for import preview/edit flow |
| `tests/test_generic_scraper.py` | Unit tests for GenericWebScraper |
| `tests/test_sam_gov_scraper.py` | Unit tests for SAMGovScraper |
| `tests/test_import_flow.py` | Integration tests for preview/confirm flow |

### Modified Files
| File | Changes |
|------|---------|
| `src/agents/scrapers/__init__.py` | Export new scrapers |
| `api/app/routes/scraper.py` | Add `/preview`, `/confirm` endpoints; update `get_scraper()` |
| `frontend/src/components/ImportRFPDialog.tsx` | Add preview/edit step, remove BeaconBid-only validation |
| `frontend/src/lib/api.ts` | Add `previewRfp()`, `confirmImport()` methods |

---

## Execution Order

1. **Task 1.1**: Create GenericWebScraper (foundation for any URL)
2. **Task 1.4**: Update scraper package exports
3. **Task 1.3**: Update `get_scraper()` to use GenericWebScraper as fallback
4. **Task 2.1**: Add `/preview` endpoint
5. **Task 2.2**: Add `/confirm` endpoint
6. **Task 3.1**: Create TypeScript types
7. **Task 3.2**: Update ImportRFPDialog with preview/edit step
8. **Task 3.3**: Remove BeaconBid-only URL validation
9. **Task 4.1**: Add API client methods
10. **Task 1.2**: Add SAMGovScraper (enhancement after core works)
11. **Task 5.1-5.3**: Add tests

---

## Future Enhancements (Not in Scope)

These were mentioned in the requirements but should be separate follow-up tasks:

- **Bulk import from search results page**: Parse search result lists and batch import
- **Scheduled re-check for updates**: Celery task to periodically refresh imported RFPs
- **Browser extension**: Chrome extension for one-click import from any page
- **State government portal scrapers**: Add specific scrapers for major state procurement sites

---

## Verification Checklist

After implementation:
- [ ] Any HTTP(S) URL is accepted in the import dialog
- [ ] Preview shows extracted data before saving
- [ ] User can edit fields before confirming import
- [ ] Duplicate URLs show warning
- [ ] BeaconBid URLs still work as before
- [ ] SAM.gov URLs are recognized and scraped
- [ ] Unknown URLs use GenericWebScraper with AI extraction
- [ ] Documents are downloaded in background
- [ ] Q&A is extracted when present
- [ ] All existing tests pass
- [ ] New scrapers have test coverage
