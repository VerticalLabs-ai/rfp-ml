# Fix Key Dates Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Key Dates section on the RFP Detail page so that posted_date, response_deadline, award_date, and qa_deadline are displayed when data exists.

**Architecture:** The issue is twofold: (1) The `RFPResponse` Pydantic model in the backend only includes `response_deadline` from `RFPBase`, missing `posted_date`, `award_date`, and other fields that exist in the database model. (2) The database has NULL values for dates because the scraper may not be capturing them. We will fix the API schema first, then add fallback UI.

**Tech Stack:** FastAPI (Python), React (TypeScript), Pydantic, SQLAlchemy

---

## Root Cause Analysis

### What's happening:
1. **Backend API Response Missing Fields**: The `RFPResponse` schema in `api/app/routes/rfps.py:232-243` inherits from `RFPBase` which only includes `response_deadline`. The database model has `posted_date`, `response_deadline`, and `award_date` fields.

2. **Database Has NULL Values**: Current RFPs in the database have `posted_date`, `response_deadline`, and `award_date` all as `None`. The scraper does save these fields (lines 153-154 in scraper.py), but the AI extraction may not be finding them on the page.

3. **Frontend Expects Fields**: The frontend (`RFPDetail.tsx:845-870`) checks for `rfp.posted_date`, `rfp.response_deadline`, `rfp.rfp_metadata?.qa_deadline`, and `rfp.award_date`. All conditional renders fail because these fields are either not in the API response or are null.

### Files Involved:
- `api/app/routes/rfps.py` - RFPResponse Pydantic schema needs `posted_date`, `award_date`, `source_url`, `source_platform`, `last_scraped_at`, `estimated_value`, `award_amount`, `rfp_metadata`
- `frontend/src/pages/RFPDetail.tsx` - Already has correct rendering logic
- `api/app/models/database.py` - Has the correct columns (no changes needed)

---

### Task 1: Add Missing Fields to RFPResponse Schema

**Files:**
- Modify: `api/app/routes/rfps.py:217-244`

**Step 1: Read the current RFPBase and RFPResponse classes**

Verify the current state of the schemas.

Run: Read `api/app/routes/rfps.py` lines 217-244

**Step 2: Add missing fields to RFPResponse**

Update the `RFPResponse` class to include all the fields the frontend needs:

```python
class RFPResponse(RFPBase):
    id: int
    rfp_id: str
    current_stage: PipelineStage
    triage_score: float | None = None
    overall_score: float | None = None
    decision_recommendation: str | None = None
    confidence_level: float | None = None
    discovered_at: datetime
    updated_at: datetime
    # Additional fields needed by frontend
    posted_date: datetime | None = None
    award_date: datetime | None = None
    award_amount: float | None = None
    estimated_value: float | None = None
    source_url: str | None = None
    source_platform: str | None = None
    last_scraped_at: datetime | None = None
    rfp_metadata: dict | None = None
    company_profile_id: int | None = None

    class Config:
        from_attributes = True
```

**Step 3: Restart backend to apply changes**

Run: `docker-compose restart backend` (or the backend will auto-reload)

**Step 4: Verify the API response includes new fields**

Run: `curl -s "http://localhost:8000/api/v1/rfps/recent?limit=1" | jq '.[0] | keys'`

Expected: Response includes `posted_date`, `award_date`, `award_amount`, `estimated_value`, `source_url`, `source_platform`, `last_scraped_at`, `rfp_metadata`, `company_profile_id`

**Step 5: Commit**

```bash
git add api/app/routes/rfps.py
git commit -m "fix(api): add missing date and metadata fields to RFPResponse schema"
```

---

### Task 2: Add Empty State to Key Dates Card

**Files:**
- Modify: `frontend/src/pages/RFPDetail.tsx:836-872`

**Step 1: Read the current Key Dates card**

Verify the current implementation.

Run: Read `frontend/src/pages/RFPDetail.tsx` lines 836-875

**Step 2: Add an empty state when no dates are available**

Update the Key Dates card to show a helpful message when no dates exist:

```tsx
{/* Timeline Card */}
<Card>
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      <CalendarDays className="h-5 w-5" />
      Key Dates
    </CardTitle>
  </CardHeader>
  <CardContent className="space-y-3">
    {rfp.posted_date && (
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Posted</span>
        <span className="text-sm font-medium">{format(new Date(rfp.posted_date), 'PPP')}</span>
      </div>
    )}
    {rfp.rfp_metadata?.qa_deadline && (
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Q&A Deadline</span>
        <span className="text-sm font-medium">{format(new Date(rfp.rfp_metadata.qa_deadline), 'PPP')}</span>
      </div>
    )}
    {rfp.response_deadline && (
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Response Due</span>
        <span className={`text-sm font-medium ${isDeadlinePast ? 'text-red-500' : deadlineUrgent ? 'text-orange-500' : ''}`}>
          {format(new Date(rfp.response_deadline), 'PPP')}
        </span>
      </div>
    )}
    {rfp.award_date && (
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">Expected Award</span>
        <span className="text-sm font-medium">{format(new Date(rfp.award_date), 'PPP')}</span>
      </div>
    )}
    {/* Empty state when no dates available */}
    {!rfp.posted_date && !rfp.response_deadline && !rfp.award_date && !rfp.rfp_metadata?.qa_deadline && (
      <div className="text-center py-4 text-muted-foreground">
        <CalendarDays className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No dates available</p>
        <p className="text-xs mt-1">Key dates will appear here when extracted from the RFP</p>
      </div>
    )}
  </CardContent>
</Card>
```

**Step 3: Test the UI**

Run: Open browser to `http://localhost:3000/rfps/{id}` and verify the Key Dates card shows the empty state

**Step 4: Commit**

```bash
git add frontend/src/pages/RFPDetail.tsx
git commit -m "fix(ui): add empty state to Key Dates card when no dates available"
```

---

### Task 3: Add Test Data to Verify Date Display (Optional Verification)

**Files:**
- None (database operation)

**Step 1: Insert a test RFP with dates via API**

Run this curl command to add an RFP with dates:

```bash
curl -X POST "http://localhost:8000/api/v1/rfps/process" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test RFP with Dates",
    "agency": "Test Agency",
    "description": "A test RFP to verify date display",
    "response_deadline": "2025-01-15T17:00:00Z",
    "category": "IT Services"
  }'
```

**Step 2: Verify the date displays in the UI**

Navigate to the newly created RFP detail page and verify:
- Response Due date shows "January 15, 2025"
- Deadline banner appears at the top

**Step 3: Update existing RFP via database (alternative)**

If the scraper isn't capturing dates, manually update one RFP:

```bash
docker exec rfp_backend python -c "
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.models.database import RFPOpportunity
db = next(get_db())
rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == 4).first()
if rfp:
    rfp.posted_date = datetime.now(timezone.utc) - timedelta(days=7)
    rfp.response_deadline = datetime.now(timezone.utc) + timedelta(days=30)
    rfp.award_date = datetime.now(timezone.utc) + timedelta(days=60)
    db.commit()
    print('Updated RFP dates successfully')
"
```

---

### Task 4: Update BeaconBid Scraper Extraction Prompt (Future Enhancement)

**Files:**
- Modify: `src/agents/scrapers/beaconbid_scraper.py:277-291`

**Note:** This task addresses why dates aren't being extracted. The AI extraction prompt may need to be more specific about date formats.

**Step 1: Review the current extraction prompt**

Run: Read `src/agents/scrapers/beaconbid_scraper.py` lines 270-300

**Step 2: Enhance the extraction instruction**

Update the extraction instruction to be more specific about finding dates:

```python
instruction="""Extract the RFP (Request for Proposal) information from this page.
Find and extract:
- title: The main title/name of the solicitation
- solicitation_number: The official solicitation or RFP number
- agency: The government agency or organization posting this RFP
- office: The specific office or department (if shown)
- description: A summary or description of what the RFP is for
- posted_date: When the RFP was posted/published (look for "Posted", "Published", "Issue Date" labels)
- response_deadline: The deadline for submitting proposals/bids (look for "Due Date", "Deadline", "Closing Date", "Response Due" labels). Include the full date and time if available.
- award_amount: Any mentioned contract value or estimated amount
- naics_code: Any NAICS code mentioned
- category: The category or type of work (e.g., IT Services, Construction)

IMPORTANT: For dates, look for:
- Posted/Issue dates near the top of the page
- Due dates/deadlines often highlighted or in red
- Date formats like MM/DD/YYYY, Month DD, YYYY, or ISO format
""",
```

**Step 3: Test with a new scrape**

After updating, scrape a new RFP URL to verify dates are captured.

**Step 4: Commit**

```bash
git add src/agents/scrapers/beaconbid_scraper.py
git commit -m "fix(scraper): improve date extraction prompt for BeaconBid scraper"
```

---

## Summary of Changes

| Task | File | Change |
|------|------|--------|
| 1 | `api/app/routes/rfps.py` | Add `posted_date`, `award_date`, `award_amount`, `estimated_value`, `source_url`, `source_platform`, `last_scraped_at`, `rfp_metadata`, `company_profile_id` to `RFPResponse` |
| 2 | `frontend/src/pages/RFPDetail.tsx` | Add empty state UI when no dates available |
| 3 | Database | Test verification (optional) |
| 4 | `src/agents/scrapers/beaconbid_scraper.py` | Improve extraction prompt (future enhancement) |

## Verification Checklist

- [ ] API returns `posted_date`, `award_date`, and `rfp_metadata` fields
- [ ] Key Dates card shows empty state when no dates exist
- [ ] Key Dates card displays dates when they exist
- [ ] Deadline banner appears when `response_deadline` is set
- [ ] No console errors in browser
- [ ] Backend logs show no errors
