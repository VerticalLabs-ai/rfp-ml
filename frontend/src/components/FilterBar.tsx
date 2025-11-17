import React from 'react';

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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Search</label>
          <input
            type="text"
            placeholder="Search RFPs..."
            value={filters.search || ''}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Stage</label>
          <select
            value={filters.stage || ''}
            onChange={(e) => onFilterChange({ ...filters, stage: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
          >
            <option value="">All Stages</option>
            <option value="discovered">Discovered</option>
            <option value="triaged">Triaged</option>
            <option value="analyzing">Analyzing</option>
            <option value="approved">Approved</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Sort By</label>
          <select
            value={filters.sortBy || 'score'}
            onChange={(e) => onFilterChange({ ...filters, sortBy: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700"
          >
            <option value="score">Score (High to Low)</option>
            <option value="deadline">Deadline (Nearest)</option>
            <option value="recent">Most Recent</option>
          </select>
        </div>
      </div>
    </div>
  );
}
