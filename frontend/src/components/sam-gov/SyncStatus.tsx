import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, CheckCircle2, XCircle, AlertTriangle, Clock, Loader2 } from 'lucide-react';
import { api, type SamGovStatus } from '@/services/api';
import { formatDistanceToNow } from 'date-fns';

export function SamGovSyncStatus() {
  const queryClient = useQueryClient();

  const { data: status, isLoading } = useQuery<SamGovStatus>({
    queryKey: ['sam-gov-status'],
    queryFn: () => api.getSamGovStatus(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const syncMutation = useMutation({
    mutationFn: (params: { days_back?: number; limit?: number }) =>
      api.triggerSamGovSync(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sam-gov-status'] });
    },
  });

  const getStatusIcon = () => {
    if (!status) return <Clock className="h-5 w-5 text-muted-foreground" />;
    switch (status.status) {
      case 'idle': return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'syncing': return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'error': return <XCircle className="h-5 w-5 text-red-500" />;
      default: return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusBadge = () => {
    if (!status?.api_key_configured) {
      return <Badge variant="destructive">Not Configured</Badge>;
    }
    if (!status?.is_connected) {
      return <Badge variant="outline">Disconnected</Badge>;
    }
    switch (status.status) {
      case 'idle': return <Badge variant="secondary">Connected</Badge>;
      case 'syncing': return <Badge className="bg-blue-500">Syncing...</Badge>;
      case 'error': return <Badge variant="destructive">Error</Badge>;
      default: return <Badge variant="outline">{status.status}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4 flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">Loading SAM.gov status...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="py-3 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <CardTitle className="text-base">SAM.gov Integration</CardTitle>
          {getStatusBadge()}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => syncMutation.mutate({ days_back: 7, limit: 100 })}
          disabled={syncMutation.isPending || status?.status === 'syncing'}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
          Sync Now
        </Button>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Last Sync</p>
            <p className="font-medium">
              {status?.last_sync
                ? formatDistanceToNow(new Date(status.last_sync), { addSuffix: true })
                : 'Never'}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Opportunities Synced</p>
            <p className="font-medium">{status?.opportunities_synced ?? 0}</p>
          </div>
        </div>

        {status?.last_error && (
          <div className="mt-3 p-2 bg-red-50 rounded text-sm text-red-700">
            {status.last_error}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
