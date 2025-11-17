import React from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Building2, TrendingUp, ArrowRight } from 'lucide-react';
import { RFPOpportunity } from '../types/rfp';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface RecentRFPsProps {
  rfps?: RFPOpportunity[];
}

const stageColors: Record<string, string> = {
  discovered: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  triaged: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  analyzing: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  pricing: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  submitted: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

export default function RecentRFPs({ rfps = [] }: RecentRFPsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent RFPs</CardTitle>
        <CardDescription>
          Latest opportunities in your pipeline
        </CardDescription>
      </CardHeader>

      <CardContent className="divide-y divide-gray-200 dark:divide-gray-700 -mx-6 px-6">
        {rfps.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
              <Building2 className="w-8 h-8 text-gray-400 dark:text-gray-500" />
            </div>
            <p className="text-gray-500 dark:text-gray-400 font-medium">No RFPs found</p>
            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
              New opportunities will appear here
            </p>
          </div>
        ) : (
          rfps.map((rfp) => (
            <Link
              key={rfp.id}
              to={`/rfps/${rfp.rfp_id}`}
              className="block px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-3 mb-2">
                    <h4 className="font-semibold text-gray-900 dark:text-white truncate group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {rfp.title}
                    </h4>
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-all group-hover:translate-x-1" />
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                    {rfp.agency && (
                      <div className="flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5" />
                        <span>{rfp.agency}</span>
                      </div>
                    )}
                    {rfp.posted_date && (
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        <span>{new Date(rfp.posted_date).toLocaleDateString()}</span>
                      </div>
                    )}
                    {rfp.triage_score && (
                      <div className="flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5" />
                        <span className="font-medium">Score: {rfp.triage_score.toFixed(1)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex-shrink-0">
                  <Badge className={cn(stageColors[rfp.current_stage] || stageColors.discovered)}>
                    {rfp.current_stage.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  );
}
