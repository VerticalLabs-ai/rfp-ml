/**
 * Skeleton loaders for Pipeline Monitor page.
 * Shows the expected Kanban layout during data loading.
 */

const stages = [
  { key: 'discovered', label: 'Discovered', color: 'blue' },
  { key: 'triaged', label: 'Triaged', color: 'purple' },
  { key: 'analyzing', label: 'Analyzing', color: 'yellow' },
  { key: 'pricing', label: 'Pricing', color: 'orange' },
  { key: 'approved', label: 'Approved', color: 'green' },
  { key: 'submitted', label: 'Submitted', color: 'teal' },
]

function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded p-3 shadow-sm animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
    </div>
  )
}

function SkeletonColumn({ label, cardCount = 2 }: { label: string; cardCount?: number }) {
  return (
    <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-sm">{label}</h3>
        <span className="px-2 py-1 rounded-full text-xs bg-gray-200 dark:bg-gray-700 animate-pulse w-6 h-5" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: cardCount }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  )
}

export function PipelineKanbanSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {stages.map((stage, index) => (
        <SkeletonColumn
          key={stage.key}
          label={stage.label}
          cardCount={index < 3 ? 3 : 2} // More cards in earlier stages
        />
      ))}
    </div>
  )
}

export function PipelineHeaderSkeleton() {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-2 animate-pulse" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-64 animate-pulse" />
      </div>
      <div className="flex items-center gap-4">
        <div className="h-9 bg-gray-200 dark:bg-gray-700 rounded w-24 animate-pulse" />
        <div className="h-9 bg-gray-200 dark:bg-gray-700 rounded w-32 animate-pulse" />
      </div>
    </div>
  )
}

export function PipelineStatsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {stages.map((stage) => (
        <div key={stage.key} className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm">
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16 mb-2 animate-pulse" />
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-12 animate-pulse" />
        </div>
      ))}
    </div>
  )
}

export function PipelineFullSkeleton() {
  return (
    <div className="space-y-6">
      <PipelineHeaderSkeleton />
      <PipelineStatsSkeleton />
      <PipelineKanbanSkeleton />
    </div>
  )
}
