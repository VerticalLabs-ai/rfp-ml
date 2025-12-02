import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, Search, X } from 'lucide-react';
import { forwardRef } from 'react';

interface FilterBarProps {
  onFilterChange: (filters: any) => void;
  filters: {
    stage?: string;
    search?: string;
    sortBy?: string;
  };
  searchInputRef?: React.RefObject<HTMLInputElement>;
  onClearSearch?: () => void;
  isSearching?: boolean;
}

const FilterBar = forwardRef<HTMLInputElement, FilterBarProps>(
  ({ onFilterChange, filters, searchInputRef, onClearSearch, isSearching }, ref) => {
    const hasSearch = filters.search && filters.search.length > 0;

    const handleClear = () => {
      onFilterChange({ ...filters, search: '' });
      onClearSearch?.();
    };

    return (
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="search" className="flex items-center justify-between">
                <span>Search</span>
                <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
                  <span className="text-xs">⌘</span>K
                </kbd>
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  ref={searchInputRef || ref}
                  id="search"
                  type="text"
                  placeholder="Search title, agency, NAICS..."
                  value={filters.search || ''}
                  onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
                  className="pl-9 pr-9"
                />
                {isSearching ? (
                  <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
                ) : hasSearch ? (
                  <button
                    onClick={handleClear}
                    className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground hover:text-foreground transition-colors"
                    aria-label="Clear search"
                  >
                    <X className="h-4 w-4" />
                  </button>
                ) : null}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="stage">Stage</Label>
              <Select
                value={filters.stage || 'all'}
                onValueChange={(value) => onFilterChange({ ...filters, stage: value })}
              >
                <SelectTrigger id="stage">
                  <SelectValue placeholder="All Stages" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stages</SelectItem>
                  <SelectItem value="discovered">Discovered</SelectItem>
                  <SelectItem value="triaged">Triaged</SelectItem>
                  <SelectItem value="analyzing">Analyzing</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="sortBy">Sort By</Label>
              <Select
                value={filters.sortBy || 'score'}
                onValueChange={(value) => onFilterChange({ ...filters, sortBy: value })}
              >
                <SelectTrigger id="sortBy">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score">Score (High to Low)</SelectItem>
                  <SelectItem value="deadline">Deadline (Nearest)</SelectItem>
                  <SelectItem value="recent">Most Recent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }
);

FilterBar.displayName = 'FilterBar';

export default FilterBar;
