import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export function StatsCardSkeleton() {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gray-200 dark:bg-gray-700" />
      <CardContent className="px-6 py-5">
        <div className="flex items-center">
          <Skeleton className="h-12 w-12 rounded-lg" />
          <div className="ml-5 flex-1">
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-8 w-16" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function PipelineOverviewSkeleton() {
  return (
    <div>
      <Skeleton className="h-6 w-48 mb-4" />
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <StatsCardSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}

export function SubmissionStatsSkeleton() {
  return (
    <div>
      <Skeleton className="h-6 w-48 mb-4" />
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <StatsCardSkeleton key={i} />
        ))}
      </div>
    </div>
  )
}

export function RecentRFPsSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32 mb-2" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent className="divide-y divide-gray-200 dark:divide-gray-700 -mx-6 px-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="px-6 py-4">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0 pr-4">
                <Skeleton className="h-5 w-3/4 mb-3" />
                <div className="flex gap-4">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>
              <Skeleton className="h-6 w-20 rounded-full" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function DashboardHeaderSkeleton() {
  return (
    <div className="bg-gradient-to-r from-gray-300 to-gray-400 dark:from-gray-700 dark:to-gray-600 rounded-2xl shadow-xl p-8 animate-pulse">
      <Skeleton className="h-9 w-48 bg-white/20 mb-2" />
      <Skeleton className="h-6 w-80 bg-white/20" />
    </div>
  )
}

export function FullDashboardSkeleton() {
  return (
    <div className="space-y-8">
      <DashboardHeaderSkeleton />
      <PipelineOverviewSkeleton />
      <SubmissionStatsSkeleton />
      <RecentRFPsSkeleton />
    </div>
  )
}
