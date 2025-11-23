import { useQuery } from '@tanstack/react-query';
import { Search, Settings, FileText, Send, CheckCircle, Clock, XCircle } from 'lucide-react';
import { api } from '../services/api';
import StatsCard from '../components/StatsCard';
import RecentRFPs from '../components/RecentRFPs';
import { RFPStats, SubmissionStats, RFPOpportunity } from '../types/rfp';

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery<RFPStats>({
    queryKey: ['rfp-stats'],
    queryFn: () => api.getRFPStats()
  });

  const { data: submissionStats } = useQuery<SubmissionStats>({
    queryKey: ['submission-stats'],
    queryFn: () => api.getSubmissionStats()
  });

  const { data: recentRFPs } = useQuery<RFPOpportunity[]>({
    queryKey: ['recent-rfps'],
    queryFn: () => api.getRecentRFPs()
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-sm text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-xl p-8 text-white">
        <h1 className="text-3xl font-bold">RFP Dashboard</h1>
        <p className="mt-2 text-blue-100 text-lg">
          Overview of your RFP pipeline and submission status
        </p>
      </div>

      {/* Main Stats Grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          RFP Pipeline Overview
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Discovered"
            value={stats?.total_discovered || 0}
            icon={Search}
            color="blue"
            trend={{ value: '+12%', positive: true }}
          />
          <StatsCard
            title="In Pipeline"
            value={stats?.in_pipeline || 0}
            icon={Settings}
            color="purple"
            trend={{ value: '-5%', positive: false }}
          />
          <StatsCard
            title="Pending Review"
            value={stats?.pending_reviews || 0}
            icon={FileText}
            color="orange"
            highlight={(stats?.pending_reviews || 0) > 0}
          />
          <StatsCard
            title="Submitted"
            value={stats?.submitted_count || 0}
            icon={Send}
            color="green"
            trend={{ value: '+8%', positive: true }}
          />
        </div>
      </div>

      {/* Submission Stats */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Submission Performance
        </h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <StatsCard
            title="Success Rate"
            value={`${submissionStats?.success_rate?.toFixed(1) || 0}%`}
            icon={CheckCircle}
            color="green"
          />
          <StatsCard
            title="Queued"
            value={submissionStats?.queued || 0}
            icon={Clock}
            color="orange"
          />
          <StatsCard
            title="Failed"
            value={submissionStats?.failed || 0}
            icon={XCircle}
            color="red"
            highlight={(submissionStats?.failed || 0) > 0}
          />
        </div>
      </div>

      {/* Recent RFPs */}
      <RecentRFPs rfps={recentRFPs || []} />
    </div>
  )
}
