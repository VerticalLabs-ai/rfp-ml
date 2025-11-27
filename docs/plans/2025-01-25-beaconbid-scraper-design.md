# BeaconBid RFP Scraper & Company Profiles Design

**Date:** 2025-01-25
**Status:** Approved
**Author:** Claude (AI Assistant)

## Overview

This feature enables users to import RFPs from BeaconBid by providing a URL. The system scrapes all metadata, documents, and Q&A using Stagehand/Browserbase, stores documents locally, and provides AI-powered Q&A analysis. Multi-tenant company profiles allow generating proposals for different clients.

## Requirements

### Functional
- Scrape RFP details from BeaconBid URLs (metadata, documents, Q&A)
- Download and store documents locally
- Track Q&A with AI categorization and insights
- Manual refresh to detect updates
- Multiple company profiles for proposal generation
- Generate proposals using selected company profile

### Non-Functional
- Resilient scraping using Stagehand's AI-powered extraction
- Local document storage for offline access and RAG indexing
- Extensible architecture for future portal support

## Architecture

### High-Level Flow
```
User enters BeaconBid URL
       ↓
Stagehand scrapes page (metadata, docs, Q&A)
       ↓
Documents downloaded to local storage
       ↓
RFP saved to database with all details
       ↓
User selects company profile → Generate proposal
       ↓
User can "Refresh" to check for updates
```

### New Components
- `src/agents/scrapers/base_scraper.py` - Abstract base class
- `src/agents/scrapers/beaconbid_scraper.py` - Stagehand-based scraper
- Database models: `CompanyProfile`, `RFPDocument`, `RFPQandA`
- API routes for scraping, profiles, documents, Q&A
- Frontend components for import, profiles, document/Q&A display

## Database Models

### CompanyProfile
```python
CompanyProfile:
├── id (primary key)
├── name (string, unique) - Display name
├── legal_name (string) - Full legal business name
├── is_default (boolean) - Default profile for new RFPs
├── # Identifiers
├── uei (string) - Unique Entity Identifier
├── cage_code (string)
├── duns_number (string)
├── # Contact
├── headquarters (string)
├── website (string)
├── primary_contact_name (string)
├── primary_contact_email (string)
├── primary_contact_phone (string)
├── # Business Info
├── established_year (integer)
├── employee_count (string) - "50-100", "150+"
├── certifications (JSON) - ["8(a)", "HUBZone", "ISO 9001"]
├── naics_codes (JSON) - ["541512", "541519"]
├── core_competencies (JSON) - List of capabilities
├── past_performance (JSON) - List of past contracts
├── # Timestamps
├── created_at, updated_at
```

### RFPDocument
```python
RFPDocument:
├── id (primary key)
├── rfp_id (foreign key → RFPOpportunity)
├── filename (string) - Original filename
├── file_path (string) - Local path
├── file_type (string) - "pdf", "docx", "xlsx"
├── file_size (integer) - Bytes
├── document_type (string) - "solicitation", "amendment", "attachment", "qa_response"
├── source_url (string) - Original download URL
├── downloaded_at (datetime)
├── checksum (string) - For change detection
```

### RFPQandA
```python
RFPQandA:
├── id (primary key)
├── rfp_id (foreign key → RFPOpportunity)
├── question_number (string) - "Q1", "Q2"
├── question_text (text)
├── answer_text (text)
├── asked_date (datetime, nullable)
├── answered_date (datetime, nullable)
├── # AI Analysis
├── category (string) - "technical", "pricing", "scope", "timeline", "compliance"
├── key_insights (JSON) - AI-extracted insights
├── related_sections (JSON) - Proposal sections affected
├── # Tracking
├── created_at (datetime)
├── is_new (boolean) - Flag for newly detected Q&A
```

### RFPOpportunity Updates
```python
# Add fields:
├── source_url (string) - BeaconBid URL
├── source_platform (string) - "beaconbid", "sam.gov", "manual"
├── company_profile_id (foreign key → CompanyProfile, nullable)
├── last_scraped_at (datetime)
├── scrape_checksum (string) - Detect page changes
```

## API Endpoints

### RFP Scraping
```
POST /api/v1/rfps/scrape
Body: { "url": "https://www.beaconbid.com/..." }
Returns: { "rfp_id": "...", "status": "success", "documents_count": 5, "qa_count": 12 }

POST /api/v1/rfps/{rfp_id}/refresh
Returns: { "changes": { "new_qa": 3, "new_documents": 1, "metadata_changed": true } }
```

### Company Profiles
```
GET    /api/v1/profiles              - List all profiles
POST   /api/v1/profiles              - Create profile
GET    /api/v1/profiles/{id}         - Get profile details
PUT    /api/v1/profiles/{id}         - Update profile
DELETE /api/v1/profiles/{id}         - Delete profile
POST   /api/v1/profiles/{id}/default - Set as default
```

### RFP Documents
```
GET  /api/v1/rfps/{rfp_id}/documents           - List documents
GET  /api/v1/rfps/{rfp_id}/documents/{doc_id}  - Download document
```

### Q&A
```
GET  /api/v1/rfps/{rfp_id}/qa                  - List Q&A with insights
POST /api/v1/rfps/{rfp_id}/qa/analyze          - Re-run AI analysis
```

### Proposal Generation
```
POST /api/v1/rfps/{rfp_id}/generate
Body: { "profile_id": "..." }
Returns: Generated proposal using selected company profile
```

## Scraper Design

### Stagehand Integration
- Uses Browserbase cloud browsers (project: `80ee6cd7-7ffd-4409-97ca-20d5a466bfdb`)
- AI-powered extraction for resilience to UI changes
- Document download with checksum tracking

### BeaconBid Extraction
| Field | Strategy |
|-------|----------|
| Title | Page heading extraction |
| Agency | "Posted by" field |
| Solicitation # | Labeled field or URL |
| Deadlines | Date fields |
| Documents | Attachment links |
| Q&A | Q&A section table/list |

## Frontend Components

### New Pages
- **Import RFP** - URL input, progress, preview
- **Company Profiles** - CRUD interface

### Enhanced Pages
- **RFP Detail** - Documents tab, Q&A tab, Refresh button
- **Settings** - Browserbase credentials

### New Components
- `ImportRFPDialog.tsx`
- `RFPDocumentsList.tsx`
- `RFPQandAList.tsx`
- `CompanyProfileForm.tsx`
- `ProfileSelector.tsx`

## Implementation Phases

### Phase 1: Foundation
1. Database models
2. Migrations
3. Company Profile API
4. Document storage utilities

### Phase 2: Scraper Core
5. Base scraper class
6. Stagehand integration
7. BeaconBid scraper
8. Document download
9. Scrape endpoint

### Phase 3: Q&A & Refresh
10. Q&A extraction
11. AI analysis
12. Refresh endpoint
13. Q&A endpoints

### Phase 4: Frontend
14. Company Profiles page
15. Import RFP dialog
16. RFP Detail enhancements
17. Profile selector

### Phase 5: Polish
18. Error handling
19. Loading states
20. Testing

## Configuration

### Environment Variables
```
BROWSERBASE_PROJECT_ID=80ee6cd7-7ffd-4409-97ca-20d5a466bfdb
BROWSERBASE_API_KEY=bb_live_nQuqR6-f4V3HW_Ydwq4lD-YD9VA
```

### File Storage
```
data/
└── rfp_documents/
    └── {rfp_id}/
        ├── solicitation.pdf
        ├── amendment_1.pdf
        └── attachment_specs.xlsx
```

## Security Considerations
- Browserbase credentials stored in environment variables
- Document checksums for integrity verification
- Input validation on URLs (BeaconBid domain check)
