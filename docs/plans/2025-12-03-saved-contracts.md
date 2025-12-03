# Saved Contracts Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a "Saved Contracts" feature allowing users to bookmark, tag, and organize interesting RFPs for later review and proposal generation.

**Architecture:** User-centric saved RFP management with tagging system, following existing patterns from ComplianceRequirement model and routes. Backend provides CRUD operations with filtering; frontend adds save buttons to RFP cards and a dedicated Saved Contracts page.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic (backend) | React, TanStack Query, Shadcn/ui, Tailwind CSS (frontend)

---

## Task 1: Create SavedRfp Database Model

**Files:**
- Modify: `api/app/models/database.py` (append new model)

**Step 1: Add SavedRfp model to database.py**

Add at end of file (after ChatMessage class ~line 994):

```python
class SavedRfp(Base):
    """User's saved/bookmarked RFPs for later review."""

    __tablename__ = "saved_rfps"

    id = Column(Integer, primary_key=True, index=True)
    rfp_id = Column(Integer, ForeignKey("rfp_opportunities.id", ondelete="CASCADE"), nullable=False, index=True)

    # User identification (simple string for now, can be FK to users table later)
    user_id = Column(String, nullable=False, default="default", index=True)

    # Organization
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # ["priority", "review-needed", "healthcare"]
    folder = Column(String, nullable=True)  # Optional folder/category

    # Timestamps
    saved_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rfp = relationship("RFPOpportunity", backref="saved_by_users")

    # Unique constraint: user can only save an RFP once
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    def to_dict(self):
        return {
            "id": self.id,
            "rfp_id": self.rfp_id,
            "user_id": self.user_id,
            "notes": self.notes,
            "tags": self.tags,
            "folder": self.folder,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

**Step 2: Verify model syntax**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && python -c "from api.app.models.database import SavedRfp; print('Model imported successfully')"`

Expected: `Model imported successfully`

**Step 3: Commit**

```bash
git add api/app/models/database.py
git commit -m "feat(models): add SavedRfp model for bookmarking RFPs"
```

---

## Task 2: Create Pydantic Schemas for SavedRfp

**Files:**
- Create: `api/app/schemas/saved_rfps.py`

**Step 1: Create schemas file**

```python
"""Pydantic schemas for saved RFPs."""
from datetime import datetime

from pydantic import BaseModel, Field


class SavedRfpBase(BaseModel):
    """Base schema for saved RFP."""

    notes: str | None = Field(None, description="User notes about this RFP")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    folder: str | None = Field(None, description="Folder/category for organization")


class SavedRfpCreate(SavedRfpBase):
    """Schema for saving an RFP."""

    rfp_id: int = Field(..., description="ID of the RFP to save")


class SavedRfpUpdate(BaseModel):
    """Schema for updating a saved RFP."""

    notes: str | None = None
    tags: list[str] | None = None
    folder: str | None = None


class SavedRfpResponse(SavedRfpBase):
    """Schema for saved RFP response."""

    id: int
    rfp_id: int
    user_id: str
    saved_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SavedRfpWithRfp(SavedRfpResponse):
    """Schema for saved RFP with full RFP details."""

    rfp_title: str
    rfp_agency: str | None
    rfp_deadline: datetime | None
    rfp_stage: str | None
    rfp_triage_score: float | None


class SavedRfpList(BaseModel):
    """Schema for list of saved RFPs with summary."""

    saved_rfps: list[SavedRfpWithRfp]
    total: int
    tags_summary: dict[str, int] = Field(default_factory=dict, description="Count per tag")
    folders_summary: dict[str, int] = Field(default_factory=dict, description="Count per folder")


class TagsList(BaseModel):
    """Schema for user's tags."""

    tags: list[str]
    counts: dict[str, int]


class BulkSaveRequest(BaseModel):
    """Schema for bulk saving multiple RFPs."""

    rfp_ids: list[int]
    tags: list[str] = Field(default_factory=list)
    folder: str | None = None


class BulkDeleteRequest(BaseModel):
    """Schema for bulk deleting saved RFPs."""

    saved_rfp_ids: list[int]
```

**Step 2: Verify schema syntax**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && python -c "from api.app.schemas.saved_rfps import SavedRfpCreate, SavedRfpResponse, SavedRfpList; print('Schemas imported successfully')"`

Expected: `Schemas imported successfully`

**Step 3: Commit**

```bash
git add api/app/schemas/saved_rfps.py
git commit -m "feat(schemas): add Pydantic schemas for saved RFPs"
```

---

## Task 3: Create SavedRfp API Routes

**Files:**
- Create: `api/app/routes/saved_rfps.py`

**Step 1: Create routes file**

```python
"""Saved RFPs API routes."""
import logging
from collections import Counter

from app.core.database import get_db
from app.models.database import RFPOpportunity, SavedRfp
from app.schemas.saved_rfps import (
    BulkDeleteRequest,
    BulkSaveRequest,
    SavedRfpCreate,
    SavedRfpList,
    SavedRfpResponse,
    SavedRfpUpdate,
    SavedRfpWithRfp,
    TagsList,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saved-rfps", tags=["saved-rfps"])

# Default user ID (will be replaced with auth later)
DEFAULT_USER_ID = "default"


def get_saved_rfp_or_404(saved_id: int, db: Session, user_id: str = DEFAULT_USER_ID) -> SavedRfp:
    """Get saved RFP by ID or raise 404."""
    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.id == saved_id, SavedRfp.user_id == user_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail=f"Saved RFP {saved_id} not found")
    return saved


def get_rfp_or_404(rfp_id: int, db: Session) -> RFPOpportunity:
    """Get RFP by ID or raise 404."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} not found")
    return rfp


@router.get("", response_model=SavedRfpList)
async def list_saved_rfps(
    tag: str | None = Query(None, description="Filter by tag"),
    folder: str | None = Query(None, description="Filter by folder"),
    search: str | None = Query(None, description="Search in notes"),
    sort_by: str = Query("saved_at", description="Sort field: saved_at, deadline, title"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all saved RFPs for the current user with optional filtering."""
    user_id = DEFAULT_USER_ID

    # Base query with join to RFP
    query = (
        db.query(SavedRfp, RFPOpportunity)
        .join(RFPOpportunity, SavedRfp.rfp_id == RFPOpportunity.id)
        .filter(SavedRfp.user_id == user_id)
    )

    # Apply filters
    if tag:
        # JSON array contains (SQLite compatible)
        query = query.filter(SavedRfp.tags.contains(f'"{tag}"'))
    if folder:
        query = query.filter(SavedRfp.folder == folder)
    if search:
        query = query.filter(SavedRfp.notes.ilike(f"%{search}%"))

    # Get total before pagination
    total = query.count()

    # Apply sorting
    if sort_by == "deadline":
        sort_col = RFPOpportunity.response_deadline
    elif sort_by == "title":
        sort_col = RFPOpportunity.title
    else:
        sort_col = SavedRfp.saved_at

    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Paginate
    results = query.offset(skip).limit(limit).all()

    # Build response with RFP details
    saved_rfps = []
    all_tags = []
    all_folders = []

    for saved, rfp in results:
        saved_rfps.append(SavedRfpWithRfp(
            id=saved.id,
            rfp_id=saved.rfp_id,
            user_id=saved.user_id,
            notes=saved.notes,
            tags=saved.tags or [],
            folder=saved.folder,
            saved_at=saved.saved_at,
            updated_at=saved.updated_at,
            rfp_title=rfp.title,
            rfp_agency=rfp.agency,
            rfp_deadline=rfp.response_deadline,
            rfp_stage=rfp.current_stage.value if rfp.current_stage else None,
            rfp_triage_score=rfp.triage_score,
        ))
        all_tags.extend(saved.tags or [])
        if saved.folder:
            all_folders.append(saved.folder)

    return SavedRfpList(
        saved_rfps=saved_rfps,
        total=total,
        tags_summary=dict(Counter(all_tags)),
        folders_summary=dict(Counter(all_folders)),
    )


@router.post("", response_model=SavedRfpResponse, status_code=status.HTTP_201_CREATED)
async def save_rfp(
    data: SavedRfpCreate,
    db: Session = Depends(get_db),
):
    """Save an RFP to the user's saved list."""
    user_id = DEFAULT_USER_ID

    # Verify RFP exists
    get_rfp_or_404(data.rfp_id, db)

    # Check if already saved
    existing = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == data.rfp_id, SavedRfp.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="RFP is already saved. Use PUT to update."
        )

    saved = SavedRfp(
        rfp_id=data.rfp_id,
        user_id=user_id,
        notes=data.notes,
        tags=data.tags,
        folder=data.folder,
    )

    db.add(saved)
    db.commit()
    db.refresh(saved)

    logger.info(f"User {user_id} saved RFP {data.rfp_id}")
    return saved


@router.get("/check/{rfp_id}")
async def check_if_saved(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    """Check if an RFP is saved by the current user."""
    user_id = DEFAULT_USER_ID

    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
        .first()
    )

    return {
        "is_saved": saved is not None,
        "saved_rfp_id": saved.id if saved else None,
    }


@router.get("/tags", response_model=TagsList)
async def list_tags(
    db: Session = Depends(get_db),
):
    """List all tags used by the current user."""
    user_id = DEFAULT_USER_ID

    saved_rfps = db.query(SavedRfp).filter(SavedRfp.user_id == user_id).all()

    all_tags = []
    for saved in saved_rfps:
        all_tags.extend(saved.tags or [])

    tag_counts = dict(Counter(all_tags))
    unique_tags = sorted(tag_counts.keys())

    return TagsList(tags=unique_tags, counts=tag_counts)


@router.get("/{saved_id}", response_model=SavedRfpResponse)
async def get_saved_rfp(
    saved_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific saved RFP."""
    return get_saved_rfp_or_404(saved_id, db)


@router.put("/{saved_id}", response_model=SavedRfpResponse)
async def update_saved_rfp(
    saved_id: int,
    data: SavedRfpUpdate,
    db: Session = Depends(get_db),
):
    """Update a saved RFP's notes, tags, or folder."""
    saved = get_saved_rfp_or_404(saved_id, db)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(saved, field, value)

    db.commit()
    db.refresh(saved)

    logger.info(f"Updated saved RFP {saved_id}: {list(update_data.keys())}")
    return saved


@router.delete("/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_rfp(
    saved_id: int,
    db: Session = Depends(get_db),
):
    """Remove an RFP from saved list."""
    saved = get_saved_rfp_or_404(saved_id, db)
    db.delete(saved)
    db.commit()
    logger.info(f"Unsaved RFP {saved.rfp_id}")


@router.delete("/by-rfp/{rfp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_rfp_by_rfp_id(
    rfp_id: int,
    db: Session = Depends(get_db),
):
    """Remove an RFP from saved list by RFP ID (convenience endpoint)."""
    user_id = DEFAULT_USER_ID

    saved = (
        db.query(SavedRfp)
        .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
        .first()
    )
    if not saved:
        raise HTTPException(status_code=404, detail=f"RFP {rfp_id} is not saved")

    db.delete(saved)
    db.commit()
    logger.info(f"Unsaved RFP {rfp_id}")


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_save_rfps(
    data: BulkSaveRequest,
    db: Session = Depends(get_db),
):
    """Save multiple RFPs at once."""
    user_id = DEFAULT_USER_ID

    saved_count = 0
    skipped_count = 0

    for rfp_id in data.rfp_ids:
        # Check if RFP exists
        rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
        if not rfp:
            skipped_count += 1
            continue

        # Check if already saved
        existing = (
            db.query(SavedRfp)
            .filter(SavedRfp.rfp_id == rfp_id, SavedRfp.user_id == user_id)
            .first()
        )
        if existing:
            skipped_count += 1
            continue

        saved = SavedRfp(
            rfp_id=rfp_id,
            user_id=user_id,
            tags=data.tags,
            folder=data.folder,
        )
        db.add(saved)
        saved_count += 1

    db.commit()
    logger.info(f"Bulk saved {saved_count} RFPs, skipped {skipped_count}")

    return {"saved_count": saved_count, "skipped_count": skipped_count}


@router.delete("/bulk")
async def bulk_unsave_rfps(
    data: BulkDeleteRequest,
    db: Session = Depends(get_db),
):
    """Remove multiple saved RFPs at once."""
    user_id = DEFAULT_USER_ID

    deleted = (
        db.query(SavedRfp)
        .filter(
            SavedRfp.id.in_(data.saved_rfp_ids),
            SavedRfp.user_id == user_id,
        )
        .delete(synchronize_session=False)
    )

    db.commit()
    logger.info(f"Bulk unsaved {deleted} RFPs")

    return {"deleted_count": deleted}
```

**Step 2: Verify routes syntax**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && python -c "from api.app.routes.saved_rfps import router; print(f'Router loaded with {len(router.routes)} routes')"`

Expected: `Router loaded with X routes` (should be ~10 routes)

**Step 3: Commit**

```bash
git add api/app/routes/saved_rfps.py
git commit -m "feat(routes): add saved RFPs API endpoints"
```

---

## Task 4: Register SavedRfp Routes in Main App

**Files:**
- Modify: `api/app/main.py`

**Step 1: Add import for saved_rfps routes**

Find line ~25 (after submissions import):
```python
    submissions,
)
```

Change to:
```python
    saved_rfps,
    submissions,
)
```

**Step 2: Add router registration**

Find line ~137 (after compliance router registration):
```python
app.include_router(compliance.router, prefix=settings.API_V1_STR)
```

Add after it:
```python
app.include_router(
    saved_rfps.router, prefix=settings.API_V1_STR, tags=["saved-rfps"]
)
```

**Step 3: Verify app starts**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && python -c "from api.app.main import app; print(f'App loaded with {len(app.routes)} routes')"`

Expected: App loads successfully with increased route count

**Step 4: Commit**

```bash
git add api/app/main.py
git commit -m "feat(main): register saved RFPs router"
```

---

## Task 5: Add Frontend API Service Functions

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add TypeScript interfaces**

Find line ~137 (after AIResponseResult interface), add:

```typescript
// Saved RFPs Types
export interface SavedRfp {
  id: number
  rfp_id: number
  user_id: string
  notes: string | null
  tags: string[]
  folder: string | null
  saved_at: string
  updated_at: string
}

export interface SavedRfpWithRfp extends SavedRfp {
  rfp_title: string
  rfp_agency: string | null
  rfp_deadline: string | null
  rfp_stage: string | null
  rfp_triage_score: number | null
}

export interface SavedRfpList {
  saved_rfps: SavedRfpWithRfp[]
  total: number
  tags_summary: Record<string, number>
  folders_summary: Record<string, number>
}

export interface SavedRfpCreate {
  rfp_id: number
  notes?: string
  tags?: string[]
  folder?: string
}

export interface SavedRfpUpdate {
  notes?: string
  tags?: string[]
  folder?: string
}

export interface TagsList {
  tags: string[]
  counts: Record<string, number>
}
```

**Step 2: Add API methods**

Find the `api` object (around line 139), add before the closing brace of `compliance: { ... }`:

```typescript
  // Saved RFPs endpoints
  savedRfps: {
    list: (params?: { tag?: string; folder?: string; search?: string; sort_by?: string; sort_order?: string; skip?: number; limit?: number }) =>
      apiClient.get<SavedRfpList>('/saved-rfps', { params }).then(res => res.data),

    save: (data: SavedRfpCreate) =>
      apiClient.post<SavedRfp>('/saved-rfps', data).then(res => res.data),

    checkIfSaved: (rfpId: number) =>
      apiClient.get<{ is_saved: boolean; saved_rfp_id: number | null }>(`/saved-rfps/check/${rfpId}`).then(res => res.data),

    getTags: () =>
      apiClient.get<TagsList>('/saved-rfps/tags').then(res => res.data),

    get: (savedId: number) =>
      apiClient.get<SavedRfp>(`/saved-rfps/${savedId}`).then(res => res.data),

    update: (savedId: number, data: SavedRfpUpdate) =>
      apiClient.put<SavedRfp>(`/saved-rfps/${savedId}`, data).then(res => res.data),

    unsave: (savedId: number) =>
      apiClient.delete(`/saved-rfps/${savedId}`).then(res => res.data),

    unsaveByRfpId: (rfpId: number) =>
      apiClient.delete(`/saved-rfps/by-rfp/${rfpId}`).then(res => res.data),

    bulkSave: (data: { rfp_ids: number[]; tags?: string[]; folder?: string }) =>
      apiClient.post<{ saved_count: number; skipped_count: number }>('/saved-rfps/bulk', data).then(res => res.data),

    bulkUnsave: (savedRfpIds: number[]) =>
      apiClient.delete<{ deleted_count: number }>('/saved-rfps/bulk', { data: { saved_rfp_ids: savedRfpIds } }).then(res => res.data),
  },
```

**Step 3: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add saved RFPs API service functions"
```

---

## Task 6: Create SaveBookmarkButton Component

**Files:**
- Create: `frontend/src/components/SaveBookmarkButton.tsx`

**Step 1: Create the component**

```tsx
import { Bookmark, BookmarkCheck, Loader2 } from 'lucide-react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface SaveBookmarkButtonProps {
  rfpId: number
  size?: 'sm' | 'default' | 'lg' | 'icon'
  variant?: 'ghost' | 'outline' | 'default'
  showLabel?: boolean
  className?: string
}

export function SaveBookmarkButton({
  rfpId,
  size = 'sm',
  variant = 'ghost',
  showLabel = false,
  className,
}: SaveBookmarkButtonProps) {
  const queryClient = useQueryClient()

  // Check if RFP is saved
  const { data: savedStatus, isLoading: isChecking } = useQuery({
    queryKey: ['saved-rfp-check', rfpId],
    queryFn: () => api.savedRfps.checkIfSaved(rfpId),
    staleTime: 30000, // Cache for 30 seconds
  })

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => api.savedRfps.save({ rfp_id: rfpId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfp-check', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP saved to your list')
    },
    onError: () => {
      toast.error('Failed to save RFP')
    },
  })

  // Unsave mutation
  const unsaveMutation = useMutation({
    mutationFn: () => api.savedRfps.unsaveByRfpId(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfp-check', rfpId] })
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP removed from saved list')
    },
    onError: () => {
      toast.error('Failed to unsave RFP')
    },
  })

  const isSaved = savedStatus?.is_saved ?? false
  const isLoading = isChecking || saveMutation.isPending || unsaveMutation.isPending

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click
    if (isSaved) {
      unsaveMutation.mutate()
    } else {
      saveMutation.mutate()
    }
  }

  return (
    <Button
      onClick={handleClick}
      size={size}
      variant={variant}
      disabled={isLoading}
      className={cn(
        isSaved && 'text-yellow-500 hover:text-yellow-600',
        className
      )}
      title={isSaved ? 'Remove from saved' : 'Save for later'}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isSaved ? (
        <BookmarkCheck className="h-4 w-4" />
      ) : (
        <Bookmark className="h-4 w-4" />
      )}
      {showLabel && (
        <span className="ml-1">{isSaved ? 'Saved' : 'Save'}</span>
      )}
    </Button>
  )
}
```

**Step 2: Verify component compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/components/SaveBookmarkButton.tsx
git commit -m "feat(components): add SaveBookmarkButton component"
```

---

## Task 7: Add SaveBookmarkButton to RFPCard

**Files:**
- Modify: `frontend/src/components/RFPCard.tsx`

**Step 1: Add import**

Find line 1 (imports), add after existing imports:

```tsx
import { SaveBookmarkButton } from './SaveBookmarkButton'
```

**Step 2: Add button to card actions**

Find line ~129 (the `<div className="flex items-center space-x-2">` with actions), add SaveBookmarkButton after GenerateBidButton:

```tsx
            <GenerateBidButton rfpId={rfp.rfp_id} rfpTitle={rfp.title} />
            <SaveBookmarkButton rfpId={rfp.id} />
```

Note: We use `rfp.id` (database ID) not `rfp.rfp_id` (string ID) because the SavedRfp model uses integer ForeignKey.

**Step 3: Verify component compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/RFPCard.tsx
git commit -m "feat(RFPCard): add save bookmark button"
```

---

## Task 8: Create SavedContracts Page

**Files:**
- Create: `frontend/src/pages/SavedContracts.tsx`

**Step 1: Create the page component**

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { formatDistance } from 'date-fns'
import { Bookmark, BookmarkX, ExternalLink, FileText, Filter, Search, Tag, Trash2, X } from 'lucide-react'
import { api, SavedRfpWithRfp } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import GenerateBidButton from '@/components/GenerateBidButton'

export default function SavedContracts() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Filters state
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTag, setSelectedTag] = useState<string>('')
  const [selectedFolder, setSelectedFolder] = useState<string>('')
  const [sortBy, setSortBy] = useState('saved_at')
  const [sortOrder, setSortOrder] = useState('desc')

  // Edit dialog state
  const [editingRfp, setEditingRfp] = useState<SavedRfpWithRfp | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [editTags, setEditTags] = useState('')
  const [editFolder, setEditFolder] = useState('')

  // Selected items for bulk operations
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  // Fetch saved RFPs
  const { data, isLoading, error } = useQuery({
    queryKey: ['saved-rfps', searchTerm, selectedTag, selectedFolder, sortBy, sortOrder],
    queryFn: () => api.savedRfps.list({
      search: searchTerm || undefined,
      tag: selectedTag || undefined,
      folder: selectedFolder || undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
    }),
  })

  // Fetch tags for filter dropdown
  const { data: tagsData } = useQuery({
    queryKey: ['saved-rfps-tags'],
    queryFn: () => api.savedRfps.getTags(),
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.savedRfps.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      setEditingRfp(null)
      toast.success('Saved RFP updated')
    },
    onError: () => toast.error('Failed to update'),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.savedRfps.unsave(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      toast.success('RFP removed from saved list')
    },
    onError: () => toast.error('Failed to remove'),
  })

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => api.savedRfps.bulkUnsave(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['saved-rfps'] })
      setSelectedIds(new Set())
      toast.success(`Removed ${result.deleted_count} RFPs from saved list`)
    },
    onError: () => toast.error('Failed to remove selected RFPs'),
  })

  const handleEdit = (rfp: SavedRfpWithRfp) => {
    setEditingRfp(rfp)
    setEditNotes(rfp.notes || '')
    setEditTags((rfp.tags || []).join(', '))
    setEditFolder(rfp.folder || '')
  }

  const handleSaveEdit = () => {
    if (!editingRfp) return

    const tags = editTags.split(',').map(t => t.trim()).filter(Boolean)
    updateMutation.mutate({
      id: editingRfp.id,
      data: {
        notes: editNotes || null,
        tags,
        folder: editFolder || null,
      },
    })
  }

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return
    if (confirm(`Remove ${selectedIds.size} RFPs from saved list?`)) {
      bulkDeleteMutation.mutate(Array.from(selectedIds))
    }
  }

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === data?.saved_rfps.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(data?.saved_rfps.map(r => r.id) || []))
    }
  }

  // Get unique folders from data
  const folders = data ? Object.keys(data.folders_summary) : []

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Failed to load saved RFPs</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bookmark className="w-6 h-6" />
            Saved Contracts
          </h1>
          <p className="text-gray-500 mt-1">
            {data?.total ?? 0} saved RFPs
          </p>
        </div>

        {selectedIds.size > 0 && (
          <Button
            variant="destructive"
            onClick={handleBulkDelete}
            disabled={bulkDeleteMutation.isPending}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Remove Selected ({selectedIds.size})
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search notes..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <Select value={selectedTag} onValueChange={setSelectedTag}>
              <SelectTrigger className="w-[180px]">
                <Tag className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by tag" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All tags</SelectItem>
                {tagsData?.tags.map(tag => (
                  <SelectItem key={tag} value={tag}>
                    {tag} ({tagsData.counts[tag]})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedFolder} onValueChange={setSelectedFolder}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by folder" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All folders</SelectItem>
                {folders.map(folder => (
                  <SelectItem key={folder} value={folder}>
                    {folder} ({data?.folders_summary[folder]})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="saved_at">Date Saved</SelectItem>
                <SelectItem value="deadline">Deadline</SelectItem>
                <SelectItem value="title">Title</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sortOrder} onValueChange={setSortOrder}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Newest</SelectItem>
                <SelectItem value="asc">Oldest</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tags summary */}
      {data && Object.keys(data.tags_summary).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(data.tags_summary).map(([tag, count]) => (
            <Badge
              key={tag}
              variant={selectedTag === tag ? 'default' : 'secondary'}
              className="cursor-pointer"
              onClick={() => setSelectedTag(selectedTag === tag ? '' : tag)}
            >
              {tag} ({count})
              {selectedTag === tag && <X className="w-3 h-3 ml-1" />}
            </Badge>
          ))}
        </div>
      )}

      {/* Saved RFPs List */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading saved RFPs...</p>
        </div>
      ) : data?.saved_rfps.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <BookmarkX className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No saved RFPs</h3>
            <p className="text-gray-500 mt-1">
              Save RFPs from the Discovery page to see them here
            </p>
            <Button
              className="mt-4"
              onClick={() => navigate('/discovery')}
            >
              Go to Discovery
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Select all checkbox */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedIds.size === data?.saved_rfps.length && data?.saved_rfps.length > 0}
              onChange={toggleSelectAll}
              className="rounded border-gray-300"
            />
            <span className="text-sm text-gray-500">Select all</span>
          </div>

          {data?.saved_rfps.map((saved) => (
            <Card key={saved.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  {/* Checkbox */}
                  <input
                    type="checkbox"
                    checked={selectedIds.has(saved.id)}
                    onChange={() => toggleSelect(saved.id)}
                    className="mt-1 rounded border-gray-300"
                  />

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3
                          className="text-lg font-medium text-gray-900 hover:text-blue-600 cursor-pointer"
                          onClick={() => navigate(`/rfps/${saved.rfp_id}`)}
                        >
                          {saved.rfp_title}
                        </h3>
                        <p className="text-sm text-gray-500">
                          {saved.rfp_agency || 'Unknown Agency'}
                          {saved.rfp_stage && (
                            <Badge variant="outline" className="ml-2">
                              {saved.rfp_stage}
                            </Badge>
                          )}
                        </p>
                      </div>

                      <div className="text-right">
                        {saved.rfp_triage_score && (
                          <span className="text-xl font-bold text-blue-600">
                            {saved.rfp_triage_score.toFixed(1)}
                          </span>
                        )}
                        {saved.rfp_deadline && (
                          <p className="text-xs text-gray-500">
                            Due {formatDistance(new Date(saved.rfp_deadline), new Date(), { addSuffix: true })}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Notes */}
                    {saved.notes && (
                      <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        {saved.notes}
                      </p>
                    )}

                    {/* Tags */}
                    {saved.tags && saved.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {saved.tags.map(tag => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {/* Folder */}
                    {saved.folder && (
                      <p className="mt-1 text-xs text-gray-400">
                        Folder: {saved.folder}
                      </p>
                    )}

                    {/* Meta info */}
                    <p className="mt-2 text-xs text-gray-400">
                      Saved {formatDistance(new Date(saved.saved_at), new Date(), { addSuffix: true })}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/rfps/${saved.rfp_id}`)}
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      View
                    </Button>
                    <GenerateBidButton
                      rfpId={String(saved.rfp_id)}
                      rfpTitle={saved.rfp_title}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEdit(saved)}
                    >
                      <FileText className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-500 hover:text-red-600"
                      onClick={() => {
                        if (confirm('Remove this RFP from saved list?')) {
                          deleteMutation.mutate(saved.id)
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4 mr-1" />
                      Remove
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingRfp} onOpenChange={() => setEditingRfp(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Saved RFP</DialogTitle>
            <DialogDescription>
              Update notes, tags, or folder for this saved RFP.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Add notes about this RFP..."
                rows={3}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Tags (comma-separated)</label>
              <Input
                value={editTags}
                onChange={(e) => setEditTags(e.target.value)}
                placeholder="priority, healthcare, review-needed"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Folder</label>
              <Input
                value={editFolder}
                onChange={(e) => setEditFolder(e.target.value)}
                placeholder="e.g., Q1 2025, Healthcare Bids"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingRfp(null)}>
              Cancel
            </Button>
            <Button onClick={handleSaveEdit} disabled={updateMutation.isPending}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
```

**Step 2: Verify page compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/pages/SavedContracts.tsx
git commit -m "feat(pages): add SavedContracts page"
```

---

## Task 9: Add Route and Navigation for SavedContracts

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

**Step 1: Add import to App.tsx**

Find line ~18 (after ProposalCopilot import):
```tsx
import ProposalCopilot from './pages/ProposalCopilot'
```

Add after:
```tsx
import SavedContracts from './pages/SavedContracts'
```

**Step 2: Add route to App.tsx**

Find line ~55 (after profiles route):
```tsx
            <Route path="/profiles" element={<CompanyProfiles />} />
```

Add after:
```tsx
            <Route path="/saved" element={<SavedContracts />} />
```

**Step 3: Add navigation item to Layout.tsx**

Find line ~11 (navigation array):
```tsx
const navigation = [
```

Add after `RFP Discovery` entry (around line 13):
```tsx
  { name: 'Saved', path: '/saved', icon: Bookmark },
```

**Step 4: Import Bookmark icon in Layout.tsx**

Find line ~2 (lucide-react import):
```tsx
import { LayoutDashboard, Search, GitBranch, CheckSquare, Send, Zap, TrendingUp, Settings, Building2 } from 'lucide-react'
```

Add `Bookmark` to the import:
```tsx
import { Bookmark, LayoutDashboard, Search, GitBranch, CheckSquare, Send, Zap, TrendingUp, Settings, Building2 } from 'lucide-react'
```

**Step 5: Verify frontend compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat(navigation): add Saved Contracts route and nav link"
```

---

## Task 10: Add Saved Count Badge to Navigation

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

**Step 1: Add query hook import**

Find line ~5 (imports), add:
```tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
```

**Step 2: Add saved count query inside Layout component**

Find line ~22 (inside `Layout` function, before `const location`):

Add after the component opens:
```tsx
  // Fetch saved RFPs count for badge
  const { data: savedData } = useQuery({
    queryKey: ['saved-rfps-count'],
    queryFn: () => api.savedRfps.list({ limit: 1 }),
    staleTime: 60000, // Cache for 1 minute
  })
  const savedCount = savedData?.total ?? 0
```

**Step 3: Update navigation item to include badge**

Find the navigation render section (around line ~82-100). Modify the navigation item render to show a badge for "Saved":

Replace:
```tsx
                <span>{item.name}</span>
```

With:
```tsx
                <span>{item.name}</span>
                {item.name === 'Saved' && savedCount > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-300 rounded-full">
                    {savedCount}
                  </span>
                )}
```

**Step 4: Verify frontend compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit`

Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(nav): add saved count badge to navigation"
```

---

## Task 11: Manual Integration Test

**Step 1: Start backend**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml && docker-compose up -d`

Expected: Backend starts successfully

**Step 2: Test API endpoints**

Run:
```bash
# Create a saved RFP (replace 1 with a valid RFP ID from your database)
curl -X POST http://localhost:8000/api/v1/saved-rfps \
  -H "Content-Type: application/json" \
  -d '{"rfp_id": 1, "tags": ["test", "priority"], "notes": "Test save"}'

# List saved RFPs
curl http://localhost:8000/api/v1/saved-rfps

# Check if saved
curl http://localhost:8000/api/v1/saved-rfps/check/1

# Get tags
curl http://localhost:8000/api/v1/saved-rfps/tags
```

Expected: All endpoints return 200/201 with appropriate JSON responses

**Step 3: Start frontend**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npm run dev`

Expected: Frontend starts successfully

**Step 4: Test UI**

1. Navigate to http://localhost:5173/discovery
2. Click the bookmark icon on an RFP card
3. Verify toast shows "RFP saved to your list"
4. Navigate to http://localhost:5173/saved
5. Verify the saved RFP appears
6. Click "Edit" and add notes/tags
7. Click "Remove" to unsave
8. Verify the badge in navigation updates

Expected: All UI interactions work as expected

**Step 5: Commit final state**

```bash
git add -A
git commit -m "feat: complete Saved Contracts feature implementation"
```

---

## Summary

This plan implements the complete Saved Contracts feature:

1. **Backend Model** (`SavedRfp`) - Database table for storing saved RFPs with notes, tags, folders
2. **Pydantic Schemas** - Request/response validation
3. **API Routes** - Full CRUD + bulk operations + tag management
4. **Frontend API Service** - TypeScript interfaces and API calls
5. **SaveBookmarkButton** - Reusable bookmark toggle component
6. **RFPCard Integration** - Bookmark button on every RFP card
7. **SavedContracts Page** - Full-featured management page with filters, sorting, bulk operations
8. **Navigation** - "Saved" link with count badge

All changes follow existing codebase patterns from ComplianceRequirement and other models.
