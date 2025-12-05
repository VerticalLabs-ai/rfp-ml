import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, Calendar, AlertTriangle } from 'lucide-react';
import { api } from '@/services/api';
import { formatDistanceToNow } from 'date-fns';

interface AmendmentHistoryProps {
  noticeId: string;
  daysBack?: number;
}

export function AmendmentHistory({ noticeId, daysBack = 365 }: AmendmentHistoryProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['sam-gov-amendments', noticeId],
    queryFn: () => api.getSamGovAmendments(noticeId, daysBack),
    enabled: !!noticeId,
  });

  if (error) {
    return (
      <Card>
        <CardContent className="py-4 text-center text-muted-foreground">
          Failed to load amendments
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Amendment History
          {data && <Badge variant="secondary">{data.amendment_count}</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : data?.amendments?.length > 0 ? (
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {data.amendments.map((amendment: any, index: number) => (
                <div key={index} className="p-3 rounded border bg-muted/30">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-sm">{amendment.title || `Amendment ${index + 1}`}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {amendment.notice_id}
                      </p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {amendment.type || 'Modification'}
                    </Badge>
                  </div>
                  {amendment.posted_date && (
                    <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                      <Calendar className="h-3 w-3" />
                      {formatDistanceToNow(new Date(amendment.posted_date), { addSuffix: true })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <div className="text-center py-4 text-muted-foreground">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No amendments found</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
