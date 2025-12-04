import { useState } from 'react'
import { ChevronDown, ChevronRight, Filter, Save, RotateCcw } from 'lucide-react'
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

export interface FilterFacets {
  noticeTypes: { value: string; count: number }[]
  setAsides: { value: string; count: number }[]
  agencies: { value: string; count: number }[]
  naicsCodes: { value: string; count: number }[]
  locations: { value: string; count: number }[]
}

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
            {/* Content added in Task 2 */}
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Set-Aside Section */}
          <FilterSection
            title="Set-Aside"
            isOpen={openSections.setAside}
            onToggle={() => toggleSection('setAside')}
            activeCount={filters.setAsides.length}
          >
            {/* Content added in Task 2 */}
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* NAICS Section */}
          <FilterSection
            title="NAICS Code"
            isOpen={openSections.naics}
            onToggle={() => toggleSection('naics')}
            activeCount={filters.naicsCodes.length}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Agency Section */}
          <FilterSection
            title="Agency"
            isOpen={openSections.agency}
            onToggle={() => toggleSection('agency')}
            activeCount={filters.agencies.length}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Location Section */}
          <FilterSection
            title="Location"
            isOpen={openSections.location}
            onToggle={() => toggleSection('location')}
            activeCount={filters.locations.length}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Value Section */}
          <FilterSection
            title="Contract Value"
            isOpen={openSections.value}
            onToggle={() => toggleSection('value')}
            activeCount={(filters.valueMin !== null ? 1 : 0) + (filters.valueMax !== null ? 1 : 0)}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Date Section */}
          <FilterSection
            title="Dates"
            isOpen={openSections.date}
            onToggle={() => toggleSection('date')}
            activeCount={[filters.postedAfter, filters.postedBefore, filters.deadlineAfter, filters.deadlineBefore].filter(Boolean).length}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>

          {/* Status Section */}
          <FilterSection
            title="Status"
            isOpen={openSections.status}
            onToggle={() => toggleSection('status')}
            activeCount={filters.status.length}
          >
            <div className="text-sm text-muted-foreground">Loading...</div>
          </FilterSection>
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
