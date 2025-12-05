# Fix Alerts and Saved Pages Blank Rendering

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the /alerts and /saved pages which show navigation header but no content by adding the missing route and fixing import paths.

**Architecture:** Two issues: (1) `/alerts` route is missing from App.tsx entirely, (2) Alerts.tsx imports from `@/lib/api` but should import from `@/services/api` for consistency with the rest of the codebase. The Layout navigation is also missing the Alerts link.

**Tech Stack:** React, TypeScript, React Router

---

## Root Cause Analysis

### Issue 1: `/alerts` Route Not Registered
**File:** `frontend/src/App.tsx`
- The `/saved` route exists (line 57), but there is NO `/alerts` route
- The Alerts component exists at `frontend/src/pages/Alerts.tsx`
- Without a route, React Router shows nothing for `/alerts`

### Issue 2: Wrong API Import in Alerts.tsx
**File:** `frontend/src/pages/Alerts.tsx:48`
- Imports: `import { api } from '@/lib/api'`
- Should be: `import { api } from '@/services/api'`
- The `@/lib/api.ts` file uses a different API pattern (raw fetch) vs `@/services/api.ts` (axios with typed methods)
- The Alerts component calls `api.get()`, `api.post()`, `api.delete()` which work with `@/lib/api` BUT the backend routes may not match

### Issue 3: Layout Navigation Missing Alerts Link
**File:** `frontend/src/components/Layout.tsx:13-23`
- The navigation array doesn't include an "Alerts" item
- Users can't navigate to `/alerts` from the UI

---

### Task 1: Add Alerts Route to App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Step 1: Read current App.tsx to verify route configuration**

Run: Read `frontend/src/App.tsx`

Verify the `/alerts` route is missing.

**Step 2: Add Alerts import and route**

At the top of the file (around line 20), add the import:

```typescript
import AlertsPage from './pages/Alerts'
```

Then add the route inside the `<Routes>` component (around line 57, after `/saved`):

```typescript
<Route path="/alerts" element={<AlertsPage />} />
```

**Step 3: Verify the route was added correctly**

Run: `grep -n "alerts" frontend/src/App.tsx`

Expected: Should show the import and route lines.

**Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "fix(routes): add missing /alerts route to App.tsx"
```

---

### Task 2: Fix API Import in Alerts.tsx

**Files:**
- Modify: `frontend/src/pages/Alerts.tsx:48`

**Step 1: Read the current import**

Run: `head -50 frontend/src/pages/Alerts.tsx | grep -n "import.*api"`

Expected: `import { api } from '@/lib/api'`

**Step 2: Change the import to use @/services/api**

Replace line 48:

```typescript
// OLD:
import { api } from '@/lib/api'

// NEW:
import { api } from '@/services/api'
```

**Step 3: Verify the Alerts API calls work with the new import**

The Alerts component uses these API patterns:
- `api.get<T>('/alerts/notifications?limit=50')`
- `api.post('/alerts/rules', data)`
- `api.delete('/alerts/rules/${ruleId}')`

The `@/services/api.ts` exports an `apiClient` axios instance with `.get()`, `.post()`, `.delete()` but NOT a generic `api.get()`.

We need to either:
1. Add the generic methods to `@/services/api.ts`, OR
2. Keep the `@/lib/api` import since it provides the generic HTTP methods

**Decision:** Keep `@/lib/api` import since it provides the generic HTTP methods the Alerts component needs. The blank page issue is NOT caused by the import - it's caused by the missing route.

**Step 3 (revised): No change needed to imports**

The `@/lib/api.ts` provides generic `api.get()`, `api.post()`, `api.delete()` methods that the Alerts component uses correctly.

**Step 4: Verify no TypeScript errors**

Run: `cd frontend && npx tsc --noEmit --skipLibCheck 2>&1 | head -20`

**Step 5: Commit (if any changes made)**

Skip this commit if no changes needed.

---

### Task 3: Add Alerts Link to Navigation

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

**Step 1: Read current navigation array**

Run: Read `frontend/src/components/Layout.tsx` lines 1-25

**Step 2: Add Bell icon import and Alerts navigation item**

First, add `Bell` to the Lucide imports (line 2):

```typescript
import { Bookmark, LayoutDashboard, Search, GitBranch, CheckSquare, Send, Zap, TrendingUp, Settings, Building2, Bell } from 'lucide-react'
```

Then add the Alerts item to the navigation array (around line 17, after Saved):

```typescript
const navigation = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'RFP Discovery', path: '/discovery', icon: Search },
  { name: 'Saved', path: '/saved', icon: Bookmark },
  { name: 'Alerts', path: '/alerts', icon: Bell },  // ADD THIS LINE
  { name: 'Forecasts', path: '/forecasts', icon: TrendingUp },
  { name: 'Pipeline', path: '/pipeline', icon: GitBranch },
  { name: 'Decisions', path: '/decisions', icon: CheckSquare },
  { name: 'Submissions', path: '/submissions', icon: Send },
  { name: 'Profiles', path: '/profiles', icon: Building2 },
  { name: 'Settings', path: '/settings', icon: Settings }
]
```

**Step 3: Verify the navigation item was added**

Run: `grep -n "alerts" frontend/src/components/Layout.tsx`

Expected: Should show the new navigation item.

**Step 4: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "fix(nav): add Alerts link to navigation menu"
```

---

### Task 4: Test Both Pages

**Step 1: Ensure frontend is running**

Run: `curl -s http://localhost:3000 | head -1`

Or check Docker: `docker ps | grep frontend`

**Step 2: Test /saved page loads**

Open browser: `http://localhost:3000/saved`

Expected: Should show "Saved Contracts" header with bookmark icon, filter section, and either saved RFPs or empty state.

**Step 3: Test /alerts page loads**

Open browser: `http://localhost:3000/alerts`

Expected: Should show "Smart Alerts" header with bell icon, priority summary cards (4 cards for urgent/high/medium/low), and tabs for Notifications and Alert Rules.

**Step 4: Verify navigation links work**

Click "Alerts" in the navigation bar - should navigate to /alerts
Click "Saved" in the navigation bar - should navigate to /saved

---

## Summary of Changes

| Task | File | Change |
|------|------|--------|
| 1 | `frontend/src/App.tsx` | Add `import AlertsPage` and `<Route path="/alerts">` |
| 2 | `frontend/src/pages/Alerts.tsx` | No change needed - `@/lib/api` import is correct |
| 3 | `frontend/src/components/Layout.tsx` | Add `Bell` import and `{ name: 'Alerts', path: '/alerts', icon: Bell }` |
| 4 | Manual test | Verify both pages render correctly |

## Verification Checklist

- [ ] `/alerts` route exists in App.tsx
- [ ] Alerts component is imported in App.tsx
- [ ] Navigation includes "Alerts" link with Bell icon
- [ ] `/saved` page renders SavedContracts component
- [ ] `/alerts` page renders AlertsPage component
- [ ] No console errors on either page
- [ ] API calls complete (may show empty state if no data)
