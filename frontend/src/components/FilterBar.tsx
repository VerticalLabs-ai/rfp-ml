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

interface FilterBarProps {
  onFilterChange: (filters: any) => void;
  filters: {
    stage?: string;
    search?: string;
    sortBy?: string;
  };
}

export default function FilterBar({ onFilterChange, filters }: FilterBarProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="search">Search</Label>
            <Input
              id="search"
              type="text"
              placeholder="Search RFPs..."
              value={filters.search || ''}
              onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="stage">Stage</Label>
            <Select
              value={filters.stage || ''}
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
