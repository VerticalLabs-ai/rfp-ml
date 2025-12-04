import { useState } from 'react'
import { ChevronDown, ChevronRight, DollarSign, Filter, RotateCcw, Save, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
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

export interface FilterFacets {
  noticeTypes: { value: string; count: number }[]
  setAsides: { value: string; count: number }[]
  agencies: { value: string; count: number }[]
  naicsCodes: { value: string; count: number }[]
  locations: { value: string; count: number }[]
}

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

const STATUS_OPTIONS = [
  { value: 'discovered', label: 'Discovered' },
  { value: 'triage', label: 'Triage' },
  { value: 'bid_decision', label: 'Bid Decision' },
  { value: 'proposal', label: 'Proposal' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'awarded', label: 'Awarded' },
  { value: 'rejected', label: 'Rejected' },
]

interface FilterSidebarProps {
  filters: FilterState
  onFilterChange: (filters: FilterState) => void
  facets?: FilterFacets
  onSavePreset?: () => void
  onClearAll?: () => void
}

export function FilterSidebar({
  filters,
  onFilterChange: _onFilterChange,
  facets: _facets,
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
            <CheckboxFilter
              options={NOTICE_TYPES}
              selected={filters.noticeTypes}
              onChange={(selected) => _onFilterChange({ ...filters, noticeTypes: selected })}
              facets={_facets?.noticeTypes}
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
              onChange={(selected) => _onFilterChange({ ...filters, setAsides: selected })}
              facets={_facets?.setAsides}
            />
          </FilterSection>

          {/* NAICS Code Section */}
          <FilterSection
            title="NAICS Code"
            isOpen={openSections.naics}
            onToggle={() => toggleSection('naics')}
            activeCount={filters.naicsCodes.length}
          >
            <SearchableCheckboxFilter
              options={_facets?.naicsCodes?.map(n => ({ value: n.value, label: n.value })) || []}
              selected={filters.naicsCodes}
              onChange={(selected) => _onFilterChange({ ...filters, naicsCodes: selected })}
              facets={_facets?.naicsCodes}
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
              options={_facets?.agencies?.map(a => ({ value: a.value, label: a.value })) || []}
              selected={filters.agencies}
              onChange={(selected) => _onFilterChange({ ...filters, agencies: selected })}
              facets={_facets?.agencies}
              placeholder="Search agencies..."
            />
          </FilterSection>

          {/* Location Section */}
          <FilterSection
            title="Location"
            isOpen={openSections.location}
            onToggle={() => toggleSection('location')}
            activeCount={filters.locations.length}
          >
            <SearchableCheckboxFilter
              options={_facets?.locations?.map(l => ({ value: l.value, label: l.value })) || []}
              selected={filters.locations}
              onChange={(selected) => _onFilterChange({ ...filters, locations: selected })}
              facets={_facets?.locations}
              placeholder="Search locations..."
            />
          </FilterSection>

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
              onChange={(min, max) => _onFilterChange({ ...filters, valueMin: min, valueMax: max })}
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
              onChange={(after, before) => _onFilterChange({ ...filters, postedAfter: after, postedBefore: before })}
            />
            <DateRangeFilter
              label="Response Deadline"
              after={filters.deadlineAfter}
              before={filters.deadlineBefore}
              onChange={(after, before) => _onFilterChange({ ...filters, deadlineAfter: after, deadlineBefore: before })}
            />
          </FilterSection>

          {/* Status Section */}
          <FilterSection
            title="Status"
            isOpen={openSections.status}
            onToggle={() => toggleSection('status')}
            activeCount={filters.status.length}
          >
            <CheckboxFilter
              options={STATUS_OPTIONS}
              selected={filters.status}
              onChange={(selected) => _onFilterChange({ ...filters, status: selected })}
            />
          </FilterSection>
        </div>
      </ScrollArea>
    </div>
  )
}

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
                id={`search-${option.value}`}
                checked={selected.includes(option.value)}
                onCheckedChange={() => toggle(option.value)}
              />
              <Label
                htmlFor={`search-${option.value}`}
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
        {filteredOptions.length === 0 && (
          <p className="text-xs text-muted-foreground text-center pt-2">
            No results found
          </p>
        )}
      </div>
    </div>
  )
}

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
