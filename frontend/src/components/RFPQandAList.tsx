import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageSquare, Sparkles, Loader2, Tag, Lightbulb, BookOpen, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'

interface RFPQandA {
  id: number
  question_number: string | null
  question_text: string
  answer_text: string | null
  asked_date: string | null
  answered_date: string | null
  category: string | null
  key_insights: string[]
  is_new: boolean
}

interface RFPQandAListProps {
  rfpId: string
}

const getCategoryColor = (category: string | null): string => {
  const colors: Record<string, string> = {
    technical: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    pricing: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    scope: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    timeline: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    compliance: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    submission: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
    evaluation: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
    other: 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
  }
  return colors[category || 'other'] || colors.other
}

export function RFPQandAList({ rfpId }: RFPQandAListProps) {
  const [showNewOnly, setShowNewOnly] = useState(false)
  const queryClient = useQueryClient()

  const { data: qaItems, isLoading, error } = useQuery({
    queryKey: ['rfp-qa', rfpId, showNewOnly],
    queryFn: () => api.get<RFPQandA[]>(`/scraper/${rfpId}/qa${showNewOnly ? '?new_only=true' : ''}`),
  })

  const analyzeMutation = useMutation({
    mutationFn: () => api.post(`/scraper/${rfpId}/qa/analyze`, {}),
    onSuccess: (data: { analyzed_count: number }) => {
      toast.success(`Analyzed ${data.analyzed_count} Q&A items`)
      queryClient.invalidateQueries({ queryKey: ['rfp-qa', rfpId] })
    },
    onError: () => {
      toast.error('Failed to analyze Q&A')
    },
  })

  const newCount = qaItems?.filter(q => q.is_new).length || 0

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Questions & Answers
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Questions & Answers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">Failed to load Q&A</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Questions & Answers
              {newCount > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {newCount} new
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {qaItems?.length || 0} Q&A entries for this RFP
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {newCount > 0 && (
              <Button
                variant={showNewOnly ? 'default' : 'outline'}
                size="sm"
                onClick={() => setShowNewOnly(!showNewOnly)}
              >
                {showNewOnly ? 'Show All' : 'Show New Only'}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending || !qaItems?.length}
            >
              {analyzeMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 mr-2" />
              )}
              Analyze with AI
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!qaItems || qaItems.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="h-12 w-12 mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 dark:text-slate-400">
              No Q&A entries found
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {qaItems.map((qa) => (
              <div
                key={qa.id}
                className={`p-4 rounded-lg border ${
                  qa.is_new
                    ? 'border-blue-300 bg-blue-50/50 dark:border-blue-700 dark:bg-blue-900/20'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
              >
                {/* Question Header */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {qa.question_number && (
                      <Badge variant="outline" className="font-mono">
                        {qa.question_number}
                      </Badge>
                    )}
                    {qa.is_new && (
                      <Badge variant="destructive" className="text-xs">
                        New
                      </Badge>
                    )}
                    {qa.category && (
                      <Badge className={getCategoryColor(qa.category)}>
                        <Tag className="h-3 w-3 mr-1" />
                        {qa.category}
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Question */}
                <div className="mb-3">
                  <p className="font-medium text-slate-900 dark:text-white">
                    {qa.question_text}
                  </p>
                </div>

                {/* Answer */}
                {qa.answer_text ? (
                  <div className="pl-4 border-l-2 border-green-400">
                    <p className="text-slate-700 dark:text-slate-300">
                      {qa.answer_text}
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-sm">Awaiting response</span>
                  </div>
                )}

                {/* AI Insights */}
                {qa.key_insights && qa.key_insights.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      <Lightbulb className="h-4 w-4 text-amber-500" />
                      Key Insights
                    </div>
                    <ul className="space-y-1">
                      {qa.key_insights.map((insight, i) => (
                        <li
                          key={i}
                          className="text-sm text-slate-600 dark:text-slate-400 flex items-start gap-2"
                        >
                          <span className="text-amber-500 mt-0.5">•</span>
                          {insight}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
