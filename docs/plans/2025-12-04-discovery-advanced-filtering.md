# RFP Discovery Advanced Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive filtering capabilities to the RFP Discovery page with collapsible filter sidebar, multi-select dropdowns, saved filter presets, and facet counts.

**Architecture:** FilterSidebar component with collapsible sections connects to enhanced backend endpoints. Filters persist to URL params and can be saved as presets. Backend returns facet counts for each filter option.

**Tech Stack:** React + TypeScript, FastAPI, SQLAlchemy, shadcn/ui (Select, Checkbox, Slider, Command), Zustand for filter state

---

## Current State Assessment

| Component | Status | Location |
|-----------|--------|----------|
| RFPDiscovery page | ✅ Exists | `frontend/src/pages/RFPDiscovery.tsx` |
| FilterBar component | ✅ Basic | `frontend/src/components/FilterBar.tsx` |
| Discovery routes | ✅ Basic | `api/app/routes/discovery.py`, `api/app/routes/rfps.py` |
| RFPOpportunity model | ✅ Has fields | `api/app/models/database.py` |
| Filterable fields | ⚠️ Underutilized | agency, naics_code, rfp_metadata.set_asides, etc. |

**Current Filters:** search, stage, sortBy only
**Target Filters:** Notice type, Set-aside, NAICS, Agency, Location, Value range, Date range, Status + saved presets

---

### Task 1: Create FilterSidebar Component Structure

**Files:**
- Create: `frontend/src/components/FilterSidebar.tsx`

**Step 1: Create the component file**

```typescript
import { useState } from 'react'
import { ChevronDown, ChevronRight, Filter, X, Save, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'

export interface FilterState {
  noticeTypes: string[]
  setAsides: string[]
  naicsCodes: string[]
  agencies: string[]
  locations: string[]
  valueMin: number | null
  valueMax: number | null
  postedAfter: string | null
  postedBefore: string | null
  deadlineAfter: string | null
  deadlineBefore: string | null
  status: string[]
}

interface FilterSidebarProps {
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  facets?: FilterFacets
  onSavePreset?: () => void
  onClearAll?: () => void
}

interface FilterFacets {
  noticeTypes: { value: string; count: number }[]
  setAsides: { value: string; count: number }[]
  agencies: { value: string; count: number }[]
  naicsCodes: { value: string; count: number }[]
  locations: { value: string; count: number }[]
}

export function FilterSidebar({
  filters,
  onFilterChange,
  facets,
  onSavePreset,
  onClearAll,
}: FilterSidebarProps) {
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    noticeType: true,
    setAside: true,
    naics: false,
    agency: false,
    location: false,
    value: false,
    date: false,
    status: true,
  })

  const activeFilterCount = Object.values(filters).filter(v =>
    Array.isArray(v) ? v.length > 0 : v !== null
  ).length

  const toggleSection = (section: string) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  return (
    <div className="w-64 border-r bg-background flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4" />
          <span className="font-medium">Filters</span>
          {activeFilterCount > 0 && (
            <Badge variant="secondary" className="text-xs">
              {activeFilterCount}
            </Badge>
          )}
        </div>
        <div className="flex gap-1">
          {onSavePreset && (
            <Button variant="ghost" size="icon" onClick={onSavePreset} title="Save filters">
              <Save className="h-4 w-4" />
            </Button>
          )}
          {onClearAll && activeFilterCount > 0 && (
            <Button variant="ghost" size="icon" onClick={onClearAll} title="Clear all">
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Filter Sections */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {/* Notice Type Section */}
          <FilterSection
            title="Notice Type"
            isOpen={openSections.noticeType}
            onToggle={() => toggleSection('noticeType')}
            activeCount={filters.noticeTypes.length}
          >
            {/* Content added in Task 2 */}
          </FilterSection>

          {/* Set-Aside Section */}
          <FilterSection
            title="Set-Aside"
            isOpen={openSections.setAside}
            onToggle={() => toggleSection('setAside')}
            activeCount={filters.setAsides.length}
          >
            {/* Content added in Task 2 */}
          </FilterSection>

          {/* More sections added in subsequent tasks */}
        </div>
      </ScrollArea>
    </div>
  )
}

interface FilterSectionProps {
  title: string
  isOpen: boolean
  onToggle: () => void
  activeCount: number
  children: React.ReactNode
}

function FilterSection({ title, isOpen, onToggle, activeCount, children }: FilterSectionProps) {
  return (
    <Collapsible open={isOpen} onOpenChange={onToggle}>
      <CollapsibleTrigger className="flex items-center justify-between w-full py-2 text-sm font-medium hover:bg-muted/50 rounded px-2 -mx-2">
        <span>{title}</span>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <Badge variant="secondary" className="text-xs h-5 px-1.5">
              {activeCount}
            </Badge>
          )}
          {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-2 space-y-2">
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}
```

**Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/components/FilterSidebar.tsx
git commit -m "feat(ui): create FilterSidebar component structure"
```

---

### Task 2: Add Notice Type and Set-Aside Filters

**Files:**
- Modify: `frontend/src/components/FilterSidebar.tsx`

**Step 1: Add checkbox filter component**

```typescript
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

const NOTICE_TYPES = [
  { value: 'solicitation', label: 'Solicitation' },
  { value: 'presolicitation', label: 'Pre-Solicitation' },
  { value: 'sources_sought', label: 'Sources Sought' },
  { value: 'award', label: 'Award Notice' },
  { value: 'special_notice', label: 'Special Notice' },
  { value: 'combined', label: 'Combined Synopsis/Solicitation' },
]

const SET_ASIDES = [
  { value: 'small_business', label: 'Small Business' },
  { value: '8a', label: '8(a)' },
  { value: 'hubzone', label: 'HUBZone' },
  { value: 'wosb', label: 'WOSB' },
  { value: 'edwosb', label: 'EDWOSB' },
  { value: 'sdvosb', label: 'Service-Disabled VOSB' },
  { value: 'vosb', label: 'VOSB' },
  { value: 'total_small_business', label: 'Total Small Business' },
]

interface CheckboxFilterProps {
  options: { value: string; label: string }[]
  selected: string[]
  onChange: (selected: string[]) => void
  facets?: { value: string; count: number }[]
}

function CheckboxFilter({ options, selected, onChange, facets }: CheckboxFilterProps) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter(v => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const getCount = (value: string) => facets?.find(f => f.value === value)?.count

  return (
    <div className="space-y-2">
      {options.map(option => {
        const count = getCount(option.value)
        return (
          <div key={option.value} className="flex items-center space-x-2">
            <Checkbox
              id={option.value}
              checked={selected.includes(option.value)}
              onCheckedChange={() => toggle(option.value)}
            />
            <Label
              htmlFor={option.value}
              className="text-sm font-normal cursor-pointer flex-1"
            >
              {option.label}
            </Label>
            {count !== undefined && (
              <span className="text-xs text-muted-foreground">{count}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

**Step 2: Use in filter sections**

```typescript
{/* Notice Type Section */}
<FilterSection
  title="Notice Type"
  isOpen={openSections.noticeType}
  onToggle={() => toggleSection('noticeType')}
  activeCount={filters.noticeTypes.length}
>
  <CheckboxFilter
    options={NOTICE_TYPES}
    selected={filters.noticeTypes}
    onChange={(selected) => onFilterChange({ ...filters, noticeTypes: selected })}
    facets={facets?.noticeTypes}
  />
</FilterSection>

{/* Set-Aside Section */}
<FilterSection
  title="Set-Aside"
  isOpen={openSections.setAside}
  onToggle={() => toggleSection('setAside')}
  activeCount={filters.setAsides.length}
>
  <CheckboxFilter
    options={SET_ASIDES}
    selected={filters.setAsides}
    onChange={(selected) => onFilterChange({ ...filters, setAsides: selected })}
    facets={facets?.setAsides}
  />
</FilterSection>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 4: Commit**

```bash
git add frontend/src/components/FilterSidebar.tsx
git commit -m "feat(ui): add notice type and set-aside filter sections"
```

---

### Task 3: Add Searchable NAICS and Agency Filters

**Files:**
- Modify: `frontend/src/components/FilterSidebar.tsx`

**Step 1: Create SearchableCheckboxFilter component**

```typescript
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'

interface SearchableCheckboxFilterProps {
  options: { value: string; label: string }[]
  selected: string[]
  onChange: (selected: string[]) => void
  facets?: { value: string; count: number }[]
  placeholder?: string
  maxVisible?: number
}

function SearchableCheckboxFilter({
  options,
  selected,
  onChange,
  facets,
  placeholder = 'Search...',
  maxVisible = 10,
}: SearchableCheckboxFilterProps) {
  const [search, setSearch] = useState('')

  const filteredOptions = options.filter(opt =>
    opt.label.toLowerCase().includes(search.toLowerCase()) ||
    opt.value.toLowerCase().includes(search.toLowerCase())
  )

  const visibleOptions = filteredOptions.slice(0, maxVisible)
  const hasMore = filteredOptions.length > maxVisible

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter(v => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const getCount = (value: string) => facets?.find(f => f.value === value)?.count

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={placeholder}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8 h-9"
        />
      </div>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {visibleOptions.map(option => {
          const count = getCount(option.value)
          return (
            <div key={option.value} className="flex items-center space-x-2">
              <Checkbox
                id={`naics-${option.value}`}
                checked={selected.includes(option.value)}
                onCheckedChange={() => toggle(option.value)}
              />
              <Label
                htmlFor={`naics-${option.value}`}
                className="text-sm font-normal cursor-pointer flex-1 truncate"
                title={option.label}
              >
                {option.label}
              </Label>
              {count !== undefined && (
                <span className="text-xs text-muted-foreground">{count}</span>
              )}
            </div>
          )
        })}
        {hasMore && (
          <p className="text-xs text-muted-foreground text-center pt-2">
            {filteredOptions.length - maxVisible} more results...
          </p>
        )}
      </div>
    </div>
  )
}
```

**Step 2: Add NAICS and Agency sections**

```typescript
{/* NAICS Code Section */}
<FilterSection
  title="NAICS Code"
  isOpen={openSections.naics}
  onToggle={() => toggleSection('naics')}
  activeCount={filters.naicsCodes.length}
>
  <SearchableCheckboxFilter
    options={facets?.naicsCodes?.map(n => ({ value: n.value, label: n.value })) || []}
    selected={filters.naicsCodes}
    onChange={(selected) => onFilterChange({ ...filters, naicsCodes: selected })}
    facets={facets?.naicsCodes}
    placeholder="Search NAICS..."
  />
</FilterSection>

{/* Agency Section */}
<FilterSection
  title="Agency"
  isOpen={openSections.agency}
  onToggle={() => toggleSection('agency')}
  activeCount={filters.agencies.length}
>
  <SearchableCheckboxFilter
    options={facets?.agencies?.map(a => ({ value: a.value, label: a.value })) || []}
    selected={filters.agencies}
    onChange={(selected) => onFilterChange({ ...filters, agencies: selected })}
    facets={facets?.agencies}
    placeholder="Search agencies..."
  />
</FilterSection>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 4: Commit**

```bash
git add frontend/src/components/FilterSidebar.tsx
git commit -m "feat(ui): add searchable NAICS and agency filters"
```

---

### Task 4: Add Value Range and Date Range Filters

**Files:**
- Modify: `frontend/src/components/FilterSidebar.tsx`

**Step 1: Add range filter components**

```typescript
import { Input } from '@/components/ui/input'
import { DollarSign, Calendar } from 'lucide-react'

interface ValueRangeFilterProps {
  min: number | null
  max: number | null
  onChange: (min: number | null, max: number | null) => void
}

function ValueRangeFilter({ min, max, onChange }: ValueRangeFilterProps) {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs text-muted-foreground">Min ($)</Label>
          <div className="relative">
            <DollarSign className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="number"
              placeholder="0"
              value={min ?? ''}
              onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null, max)}
              className="pl-7 h-9"
            />
          </div>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">Max ($)</Label>
          <div className="relative">
            <DollarSign className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="number"
              placeholder="Any"
              value={max ?? ''}
              onChange={(e) => onChange(min, e.target.value ? Number(e.target.value) : null)}
              className="pl-7 h-9"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

interface DateRangeFilterProps {
  label: string
  after: string | null
  before: string | null
  onChange: (after: string | null, before: string | null) => void
}

function DateRangeFilter({ label, after, before, onChange }: DateRangeFilterProps) {
  return (
    <div className="space-y-2">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <Input
            type="date"
            value={after ?? ''}
            onChange={(e) => onChange(e.target.value || null, before)}
            className="h-9 text-xs"
          />
        </div>
        <div>
          <Input
            type="date"
            value={before ?? ''}
            onChange={(e) => onChange(after, e.target.value || null)}
            className="h-9 text-xs"
          />
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Add value and date sections**

```typescript
{/* Value Range Section */}
<FilterSection
  title="Contract Value"
  isOpen={openSections.value}
  onToggle={() => toggleSection('value')}
  activeCount={(filters.valueMin !== null ? 1 : 0) + (filters.valueMax !== null ? 1 : 0)}
>
  <ValueRangeFilter
    min={filters.valueMin}
    max={filters.valueMax}
    onChange={(min, max) => onFilterChange({ ...filters, valueMin: min, valueMax: max })}
  />
</FilterSection>

{/* Date Range Section */}
<FilterSection
  title="Dates"
  isOpen={openSections.date}
  onToggle={() => toggleSection('date')}
  activeCount={[filters.postedAfter, filters.postedBefore, filters.deadlineAfter, filters.deadlineBefore].filter(Boolean).length}
>
  <DateRangeFilter
    label="Posted Date"
    after={filters.postedAfter}
    before={filters.postedBefore}
    onChange={(after, before) => onFilterChange({ ...filters, postedAfter: after, postedBefore: before })}
  />
  <DateRangeFilter
    label="Response Deadline"
    after={filters.deadlineAfter}
    before={filters.deadlineBefore}
    onChange={(after, before) => onFilterChange({ ...filters, deadlineAfter: after, deadlineBefore: before })}
  />
</FilterSection>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 4: Commit**

```bash
git add frontend/src/components/FilterSidebar.tsx
git commit -m "feat(ui): add value range and date range filters"
```

---

### Task 5: Add Backend Filter Support

**Files:**
- Modify: `api/app/routes/rfps.py`
- Modify: `api/app/services/rfp_service.py`

**Step 1: Update get_discovered_rfps endpoint**

Add new query parameters:

```python
@router.get("/discovered", response_model=DiscoveredRFPsResponse)
async def get_discovered_rfps(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="score"),
    # New filter parameters
    notice_types: list[str] | None = Query(default=None),
    set_asides: list[str] | None = Query(default=None),
    naics_codes: list[str] | None = Query(default=None),
    agencies: list[str] | None = Query(default=None),
    locations: list[str] | None = Query(default=None),
    value_min: float | None = Query(default=None),
    value_max: float | None = Query(default=None),
    posted_after: str | None = Query(default=None),
    posted_before: str | None = Query(default=None),
    deadline_after: str | None = Query(default=None),
    deadline_before: str | None = Query(default=None),
    status: list[str] | None = Query(default=None),
    db: DBDep = ...,
):
    """Get discovered RFPs with comprehensive filtering."""

    filters = {
        'notice_types': notice_types,
        'set_asides': set_asides,
        'naics_codes': naics_codes,
        'agencies': agencies,
        'locations': locations,
        'value_min': value_min,
        'value_max': value_max,
        'posted_after': posted_after,
        'posted_before': posted_before,
        'deadline_after': deadline_after,
        'deadline_before': deadline_before,
        'status': status,
    }

    rfps = rfp_service.get_discovered_rfps(
        skip=skip,
        limit=limit,
        search=search,
        sort_by=sort_by,
        filters=filters,
    )

    return DiscoveredRFPsResponse(
        items=rfps,
        total=len(rfps),  # TODO: Add proper count
    )
```

**Step 2: Update service layer**

In `api/app/services/rfp_service.py`:

```python
def get_discovered_rfps(
    self,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    sort_by: str = "score",
    filters: dict | None = None,
) -> list[RFPOpportunity]:
    """Get discovered RFPs with comprehensive filtering."""

    query = self.db.query(RFPOpportunity)

    # Apply search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                RFPOpportunity.title.ilike(search_term),
                RFPOpportunity.description.ilike(search_term),
                RFPOpportunity.agency.ilike(search_term),
                RFPOpportunity.naics_code.ilike(search_term),
            )
        )

    if filters:
        # Notice types
        if filters.get('notice_types'):
            query = query.filter(
                RFPOpportunity.rfp_metadata['notice_type'].astext.in_(filters['notice_types'])
            )

        # Set-asides (JSON array contains any)
        if filters.get('set_asides'):
            conditions = []
            for sa in filters['set_asides']:
                conditions.append(
                    RFPOpportunity.rfp_metadata['set_asides'].contains([sa])
                )
            query = query.filter(or_(*conditions))

        # NAICS codes
        if filters.get('naics_codes'):
            query = query.filter(RFPOpportunity.naics_code.in_(filters['naics_codes']))

        # Agencies
        if filters.get('agencies'):
            query = query.filter(RFPOpportunity.agency.in_(filters['agencies']))

        # Value range
        if filters.get('value_min') is not None:
            query = query.filter(
                or_(
                    RFPOpportunity.award_amount >= filters['value_min'],
                    RFPOpportunity.estimated_value >= filters['value_min']
                )
            )
        if filters.get('value_max') is not None:
            query = query.filter(
                or_(
                    RFPOpportunity.award_amount <= filters['value_max'],
                    RFPOpportunity.estimated_value <= filters['value_max']
                )
            )

        # Date filters
        if filters.get('posted_after'):
            query = query.filter(RFPOpportunity.posted_date >= filters['posted_after'])
        if filters.get('posted_before'):
            query = query.filter(RFPOpportunity.posted_date <= filters['posted_before'])
        if filters.get('deadline_after'):
            query = query.filter(RFPOpportunity.response_deadline >= filters['deadline_after'])
        if filters.get('deadline_before'):
            query = query.filter(RFPOpportunity.response_deadline <= filters['deadline_before'])

        # Status
        if filters.get('status'):
            query = query.filter(RFPOpportunity.current_stage.in_(filters['status']))

    # Sorting
    if sort_by == "score":
        query = query.order_by(desc(RFPOpportunity.triage_score))
    elif sort_by == "deadline":
        query = query.order_by(asc(RFPOpportunity.response_deadline))
    elif sort_by == "recent":
        query = query.order_by(desc(RFPOpportunity.discovered_at))

    return query.offset(skip).limit(limit).all()
```

**Step 3: Test import**

Run: `cd api && python -c "from app.routes import rfps; print('OK')"`

**Step 4: Commit**

```bash
git add api/app/routes/rfps.py api/app/services/rfp_service.py
git commit -m "feat(api): add comprehensive filter support to discovery endpoint"
```

---

### Task 6: Add Facets Endpoint

**Files:**
- Modify: `api/app/routes/rfps.py`

**Step 1: Add facets endpoint**

```python
@router.get("/discovered/facets")
async def get_discovered_facets(
    search: str | None = Query(default=None),
    db: DBDep = ...,
):
    """Get facet counts for filter options."""

    base_query = db.query(RFPOpportunity)

    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            or_(
                RFPOpportunity.title.ilike(search_term),
                RFPOpportunity.description.ilike(search_term),
            )
        )

    # Agency facets
    agency_facets = (
        db.query(RFPOpportunity.agency, func.count(RFPOpportunity.id))
        .filter(RFPOpportunity.agency.isnot(None))
        .group_by(RFPOpportunity.agency)
        .order_by(func.count(RFPOpportunity.id).desc())
        .limit(50)
        .all()
    )

    # NAICS facets
    naics_facets = (
        db.query(RFPOpportunity.naics_code, func.count(RFPOpportunity.id))
        .filter(RFPOpportunity.naics_code.isnot(None))
        .group_by(RFPOpportunity.naics_code)
        .order_by(func.count(RFPOpportunity.id).desc())
        .limit(50)
        .all()
    )

    return {
        "agencies": [{"value": a[0], "count": a[1]} for a in agency_facets],
        "naicsCodes": [{"value": n[0], "count": n[1]} for n in naics_facets],
        "noticeTypes": [],  # TODO: Extract from rfp_metadata
        "setAsides": [],    # TODO: Extract from rfp_metadata
        "locations": [],    # TODO: Extract from rfp_metadata
    }
```

**Step 2: Test import**

Run: `cd api && python -c "from app.routes import rfps; print('OK')"`

**Step 3: Commit**

```bash
git add api/app/routes/rfps.py
git commit -m "feat(api): add facets endpoint for filter counts"
```

---

### Task 7: Integrate FilterSidebar into Discovery Page

**Files:**
- Modify: `frontend/src/pages/RFPDiscovery.tsx`

**Step 1: Import and use FilterSidebar**

```typescript
import { FilterSidebar, FilterState } from '@/components/FilterSidebar'

// Add filter state
const [advancedFilters, setAdvancedFilters] = useState<FilterState>({
  noticeTypes: [],
  setAsides: [],
  naicsCodes: [],
  agencies: [],
  locations: [],
  valueMin: null,
  valueMax: null,
  postedAfter: null,
  postedBefore: null,
  deadlineAfter: null,
  deadlineBefore: null,
  status: [],
})

// Fetch facets
const { data: facets } = useQuery({
  queryKey: ['rfp-facets', filters.search],
  queryFn: () => api.getDiscoveredFacets(filters.search),
})

// Update query to include filters
const { data: rfps, isLoading } = useQuery({
  queryKey: ['discovered-rfps', filters, advancedFilters],
  queryFn: () => api.getDiscoveredRFPs({
    ...filters,
    ...advancedFilters,
  }),
})

// Clear all filters
const handleClearAll = () => {
  setAdvancedFilters({
    noticeTypes: [],
    setAsides: [],
    naicsCodes: [],
    agencies: [],
    locations: [],
    valueMin: null,
    valueMax: null,
    postedAfter: null,
    postedBefore: null,
    deadlineAfter: null,
    deadlineBefore: null,
    status: [],
  })
}
```

**Step 2: Add sidebar to layout**

```typescript
return (
  <div className="flex h-full">
    {/* Filter Sidebar */}
    <FilterSidebar
      filters={advancedFilters}
      onFilterChange={setAdvancedFilters}
      facets={facets}
      onClearAll={handleClearAll}
    />

    {/* Main Content */}
    <div className="flex-1 p-6 overflow-y-auto">
      {/* Existing content */}
    </div>
  </div>
)
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 4: Commit**

```bash
git add frontend/src/pages/RFPDiscovery.tsx
git commit -m "feat(ui): integrate FilterSidebar into Discovery page"
```

---

### Task 8: Add Filter Preset Model and Endpoints

**Files:**
- Modify: `api/app/models/database.py`
- Modify: `api/app/routes/rfps.py`

**Step 1: Add FilterPreset model**

```python
class FilterPreset(Base):
    """Saved filter preset for RFP discovery."""

    __tablename__ = "filter_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    filters = Column(JSON, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Step 2: Add preset endpoints**

```python
@router.post("/filter-presets")
async def create_filter_preset(
    name: str,
    filters: dict,
    db: DBDep,
):
    """Save a filter preset."""
    preset = FilterPreset(name=name, filters=filters)
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return {"id": preset.id, "name": preset.name}

@router.get("/filter-presets")
async def list_filter_presets(db: DBDep):
    """List all filter presets."""
    presets = db.query(FilterPreset).order_by(FilterPreset.name).all()
    return [{"id": p.id, "name": p.name, "filters": p.filters} for p in presets]

@router.delete("/filter-presets/{preset_id}")
async def delete_filter_preset(preset_id: int, db: DBDep):
    """Delete a filter preset."""
    preset = db.query(FilterPreset).filter(FilterPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    db.delete(preset)
    db.commit()
    return {"status": "deleted"}
```

**Step 3: Test import**

Run: `cd api && python -c "from app.models.database import FilterPreset; print('OK')"`

**Step 4: Commit**

```bash
git add api/app/models/database.py api/app/routes/rfps.py
git commit -m "feat(api): add filter preset model and endpoints"
```

---

### Task 9: Add Export to CSV Feature

**Files:**
- Modify: `frontend/src/pages/RFPDiscovery.tsx`

**Step 1: Add export function**

```typescript
const exportToCSV = () => {
  if (!rfps?.items || rfps.items.length === 0) return

  const headers = ['Title', 'Agency', 'NAICS', 'Deadline', 'Value', 'Score', 'Status']
  const rows = rfps.items.map(rfp => [
    rfp.title,
    rfp.agency || '',
    rfp.naics_code || '',
    rfp.response_deadline ? new Date(rfp.response_deadline).toLocaleDateString() : '',
    rfp.award_amount || rfp.estimated_value || '',
    rfp.triage_score?.toFixed(1) || '',
    rfp.current_stage || '',
  ])

  const csv = [headers, ...rows]
    .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    .join('\n')

  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `rfp-discovery-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

**Step 2: Add export button**

```typescript
<Button variant="outline" onClick={exportToCSV} disabled={!rfps?.items?.length}>
  <Download className="h-4 w-4 mr-2" />
  Export CSV
</Button>
```

**Step 3: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 4: Commit**

```bash
git add frontend/src/pages/RFPDiscovery.tsx
git commit -m "feat(ui): add export to CSV for filtered RFPs"
```

---

### Task 10: Update Frontend API Client

**Files:**
- Modify: `frontend/src/services/api.ts`

**Step 1: Add new API methods**

```typescript
// Discovery filters
getDiscoveredRFPs: (params: {
  search?: string
  sortBy?: string
  noticeTypes?: string[]
  setAsides?: string[]
  naicsCodes?: string[]
  agencies?: string[]
  locations?: string[]
  valueMin?: number
  valueMax?: number
  postedAfter?: string
  postedBefore?: string
  deadlineAfter?: string
  deadlineBefore?: string
  status?: string[]
  skip?: number
  limit?: number
}) => {
  // Convert arrays to query params
  const queryParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach(v => queryParams.append(key, v))
      } else {
        queryParams.set(key, String(value))
      }
    }
  })
  return apiClient.get(`/rfps/discovered?${queryParams.toString()}`).then(res => res.data)
},

getDiscoveredFacets: (search?: string) =>
  apiClient.get('/rfps/discovered/facets', { params: { search } }).then(res => res.data),

// Filter presets
createFilterPreset: (name: string, filters: Record<string, unknown>) =>
  apiClient.post('/rfps/filter-presets', { name, filters }).then(res => res.data),

listFilterPresets: () =>
  apiClient.get('/rfps/filter-presets').then(res => res.data),

deleteFilterPreset: (id: number) =>
  apiClient.delete(`/rfps/filter-presets/${id}`).then(res => res.data),
```

**Step 2: Verify build**

Run: `cd frontend && npm run build 2>&1 | head -20`

**Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(api): add discovery filter and preset API methods"
```

---

### Task 11: Final Verification

**Step 1: Rebuild containers**

Run: `docker-compose build backend frontend && docker-compose up -d`

**Step 2: Verify backend logs**

Run: `docker-compose logs backend --tail=20`

**Step 3: Test frontend build**

Run: `cd frontend && npm run build`

**Step 4: Manual testing checklist**

- [ ] Navigate to Discovery page
- [ ] Verify filter sidebar appears
- [ ] Expand/collapse filter sections
- [ ] Select notice type filters
- [ ] Select set-aside filters
- [ ] Search and select NAICS codes
- [ ] Search and select agencies
- [ ] Set value range
- [ ] Set date ranges
- [ ] Verify RFP list updates with filters
- [ ] Verify facet counts update
- [ ] Clear all filters
- [ ] Export filtered results to CSV
- [ ] Save filter preset
- [ ] Load saved preset

**Step 5: Final commit**

```bash
git add .
git commit -m "feat(discovery): complete advanced filtering implementation"
```

---

## Summary

This plan implements comprehensive filtering for RFP Discovery:

1. **Frontend** (Tasks 1-4, 7, 9): FilterSidebar component with collapsible sections, checkbox filters, searchable dropdowns, value/date ranges, CSV export
2. **Backend** (Tasks 5-6, 8): Enhanced discovery endpoint with all filter params, facets endpoint, filter preset model/endpoints
3. **Integration** (Tasks 10-11): API client updates, verification

**Total Tasks:** 11
**Key Features:**
- Notice type, set-aside, NAICS, agency, location, value, date filters
- Facet counts for each filter option
- Saved filter presets
- Export filtered results to CSV
- Collapsible sidebar with active filter badges
