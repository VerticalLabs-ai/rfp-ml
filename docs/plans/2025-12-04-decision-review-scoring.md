# Decision Review Scoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Decision Review page showing "N/A" for all scoring metrics by adding a "Run Analysis" endpoint and button that triggers Go/No-Go scoring for RFPs.

**Architecture:** Add a new API endpoint `POST /rfps/{rfp_id}/analyze` that runs the Go/No-Go engine and persists scores to the database. Update the DecisionCard component to include a "Run Analysis" button when scores are missing. The scoring will populate `overall_score`, `triage_score`, `decision_recommendation`, and `confidence_level` fields.

**Tech Stack:** FastAPI, React, SQLAlchemy, Go/No-Go Engine (`src/decision/go_nogo_engine.py`)

---

## Analysis Summary

**Root Cause:**
- RFPs are moved to `decision_pending` stage without having scores populated
- The Go/No-Go engine (`analyze_rfp_opportunity`) is only called during manual RFP submission via `/process` endpoint
- Scraped RFPs bypass the scoring pipeline entirely
- Database fields `overall_score`, `triage_score`, `decision_recommendation`, `confidence_level` are all NULL

**Current State:**
```
GET /api/v1/rfps/discovered?stage=decision_pending
→ Returns RFPs with null scores
```

**Solution:**
1. Add `POST /rfps/{rfp_id}/analyze` endpoint to run Go/No-Go scoring on demand
2. Add "Run Analysis" button to DecisionCard when scores are missing
3. Optionally: auto-trigger scoring when RFP enters `decision_pending` stage

---

### Task 1: Add Analyze Endpoint to RFPs Router

**Files:**
- Modify: `api/app/routes/rfps.py`

**Step 1: Add the analyze endpoint**

Add after the existing `/process` endpoint (around line 627):

```python
@router.post("/{rfp_id}/analyze")
async def analyze_rfp(rfp: RFPDep, db: DBDep):
    """
    Run Go/No-Go analysis on an RFP and persist scores.

    This endpoint triggers the scoring engine to calculate:
    - overall_score: Combined weighted score (0-100)
    - triage_score: Initial opportunity assessment
    - decision_recommendation: 'go', 'no-go', or 'review'
    - confidence_level: Model confidence (0-1)
    """
    from app.websockets.websocket_router import broadcast_rfp_update

    # Prepare RFP data for analysis
    rfp_data = {
        "title": rfp.title,
        "description": rfp.description,
        "agency": rfp.agency,
        "naics_code": rfp.naics_code,
        "category": rfp.category,
        "award_amount": rfp.award_amount or rfp.estimated_value,
        "response_deadline": rfp.response_deadline.isoformat() if rfp.response_deadline else None,
    }

    # Run analysis through processor
    result = await processor.process_single_rfp(rfp_data)

    # Update database with scores
    rfp.triage_score = result.get("triage_score")
    rfp.overall_score = result.get("triage_score")  # Use triage as overall for now
    rfp.decision_recommendation = result.get("decision_recommendation")
    rfp.confidence_level = result.get("confidence_level")
    rfp.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rfp)

    # Broadcast update via WebSocket
    try:
        await broadcast_rfp_update(rfp.rfp_id, {
            "event": "rfp_analyzed",
            "rfp_id": rfp.rfp_id,
            "overall_score": rfp.overall_score,
            "decision_recommendation": rfp.decision_recommendation,
        })
    except Exception:
        pass  # WebSocket errors shouldn't fail the request

    return {
        "rfp_id": rfp.rfp_id,
        "overall_score": rfp.overall_score,
        "triage_score": rfp.triage_score,
        "decision_recommendation": rfp.decision_recommendation,
        "confidence_level": rfp.confidence_level,
        "justification": result.get("justification"),
        "risk_factors": result.get("risk_factors", []),
        "strengths": result.get("strengths", []),
    }
```

**Step 2: Verify backend reloads without errors**

Run: `docker-compose logs --tail=5 backend`
Expected: No import errors, uvicorn running

**Step 3: Test the endpoint**

Run: `curl -X POST "http://localhost:8000/api/v1/rfps/TEST-RFP-001/analyze" | jq`
Expected: JSON response with scores populated

**Step 4: Commit**

```bash
git add api/app/routes/rfps.py
git commit -m "feat(rfps): add analyze endpoint for Go/No-Go scoring"
```

---

### Task 2: Add API Method for Analyze

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add analyzeRfp method**

Find the RFP-related methods (around line 220-230) and add:

```typescript
  analyzeRfp: (rfpId: string) =>
    apiClient.post(`/rfps/${rfpId}/analyze`).then(res => res.data),
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add analyzeRfp method"
```

---

### Task 3: Update DecisionCard Interface

**Files:**
- Modify: `frontend/src/components/DecisionCard.tsx`

**Step 1: Update the interface and add analyze callback**

Replace the current interface:
```typescript
interface DecisionCardProps {
  rfp: {
    id: number;
    rfp_id: string;
    title: string;
    agency: string;
    decision_recommendation?: string;
    confidence_level?: number;
    overall_score?: number;
    response_deadline?: string;
  };
  onApprove: (rfpId: string) => void;
  onReject: (rfpId: string) => void;
}
```

With:
```typescript
interface DecisionCardProps {
  rfp: {
    id: number;
    rfp_id: string;
    title: string;
    agency: string;
    decision_recommendation?: string;
    confidence_level?: number;
    overall_score?: number;
    triage_score?: number;
    response_deadline?: string;
  };
  onApprove: (rfpId: string) => void;
  onReject: (rfpId: string) => void;
  onAnalyze?: (rfpId: string) => void;
  isAnalyzing?: boolean;
}
```

**Step 2: Update the component to accept new props**

Update the function signature:
```typescript
export default function DecisionCard({ rfp, onApprove, onReject, onAnalyze, isAnalyzing }: DecisionCardProps) {
```

**Step 3: Add "Run Analysis" button when scores are missing**

Find the button section (around line 61-74) and replace with:

```typescript
      {/* Show analyze button if no scores */}
      {rfp.overall_score == null && onAnalyze && (
        <button
          onClick={() => onAnalyze(rfp.rfp_id)}
          disabled={isAnalyzing}
          className="w-full mb-3 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isAnalyzing ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </>
          ) : (
            'Run Analysis'
          )}
        </button>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => onApprove(rfp.rfp_id)}
          disabled={rfp.overall_score == null}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Approve
        </button>
        <button
          onClick={() => onReject(rfp.rfp_id)}
          disabled={rfp.overall_score == null}
          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Reject
        </button>
      </div>
```

**Step 4: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/components/DecisionCard.tsx
git commit -m "feat(DecisionCard): add Run Analysis button when scores missing"
```

---

### Task 4: Update DecisionReview Page to Handle Analysis

**Files:**
- Modify: `frontend/src/pages/DecisionReview.tsx`

**Step 1: Add analyze mutation and state**

Replace the current file contents with:

```typescript
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../services/api'
import { toast } from 'sonner'
import DecisionCard from '../components/DecisionCard'

export default function DecisionReview() {
  const queryClient = useQueryClient()
  const [analyzingRfpId, setAnalyzingRfpId] = useState<string | null>(null)

  const { data: pendingDecisions, isLoading } = useQuery({
    queryKey: ['pending-decisions'],
    queryFn: () => api.getPendingDecisions()
  })

  const analyzeMutation = useMutation({
    mutationFn: (rfpId: string) => {
      setAnalyzingRfpId(rfpId)
      return api.analyzeRfp(rfpId)
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success(`Analysis complete: ${data.decision_recommendation?.toUpperCase() || 'Review'} recommendation`)
      setAnalyzingRfpId(null)
    },
    onError: (error) => {
      toast.error('Analysis failed. Please try again.')
      setAnalyzingRfpId(null)
    }
  })

  const approveMutation = useMutation({
    mutationFn: (rfpId: string) => api.approveDecision(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success('Decision approved')
    }
  })

  const rejectMutation = useMutation({
    mutationFn: (rfpId: string) => api.rejectDecision(rfpId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-decisions'] })
      toast.success('Decision rejected')
    }
  })

  const needsAnalysis = pendingDecisions?.filter((rfp: any) => rfp.overall_score == null).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Decision Review</h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Review Go/No-Go recommendations and approve bids
          </p>
        </div>
        {needsAnalysis > 0 && (
          <span className="px-3 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 rounded-full text-sm">
            {needsAnalysis} need{needsAnalysis > 1 ? '' : 's'} analysis
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-12">Loading decisions...</div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {pendingDecisions?.map((rfp: any) => (
            <DecisionCard
              key={rfp.id}
              rfp={rfp}
              onApprove={() => approveMutation.mutate(rfp.rfp_id)}
              onReject={() => rejectMutation.mutate(rfp.rfp_id)}
              onAnalyze={() => analyzeMutation.mutate(rfp.rfp_id)}
              isAnalyzing={analyzingRfpId === rfp.rfp_id}
            />
          ))}
          {pendingDecisions?.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No pending decisions
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

**Step 2: Verify TypeScript compiles**

Run: `cd /Users/mgunnin/Developer/08_Clients/ibyte/rfp_ml/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/pages/DecisionReview.tsx
git commit -m "feat(DecisionReview): integrate analyze mutation and show needs-analysis count"
```

---

### Task 5: Test the Complete Flow

**Step 1: Test the analyze endpoint directly**

```bash
curl -X POST "http://localhost:8000/api/v1/rfps/TEST-RFP-001/analyze" | jq
```

Expected: JSON response with `overall_score`, `triage_score`, `decision_recommendation`, `confidence_level` populated

**Step 2: Verify database was updated**

```bash
curl -s "http://localhost:8000/api/v1/rfps/discovered?stage=decision_pending&limit=1" | jq '.[0] | {rfp_id, overall_score, decision_recommendation}'
```

Expected: `overall_score` and `decision_recommendation` are no longer null

**Step 3: Test in browser**

Open http://localhost/decisions in browser.
Expected:
- RFPs without scores show "Run Analysis" button
- Clicking "Run Analysis" shows loading spinner
- After analysis completes, scores appear and Approve/Reject buttons become enabled

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(decisions): complete Go/No-Go scoring integration"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `api/app/routes/rfps.py` | Added `POST /{rfp_id}/analyze` endpoint |
| `frontend/src/services/api.ts` | Added `analyzeRfp` method |
| `frontend/src/components/DecisionCard.tsx` | Added "Run Analysis" button, disabled Approve/Reject when no scores |
| `frontend/src/pages/DecisionReview.tsx` | Added analyze mutation, shows count of RFPs needing analysis |

## Benefits

1. **On-demand scoring** - Users can trigger analysis when ready
2. **Clear UX** - Shows which RFPs need analysis vs which are ready for decision
3. **Prevents invalid approvals** - Can't approve/reject without scores
4. **Real-time updates** - WebSocket broadcasts score updates
5. **Works with scraped RFPs** - Scoring no longer requires manual submission

## Future Enhancements (Optional)

- Add "Analyze All" button to batch-process multiple RFPs
- Auto-trigger analysis when RFP enters `decision_pending` stage
- Add score breakdown display (margin, complexity, duration scores)
