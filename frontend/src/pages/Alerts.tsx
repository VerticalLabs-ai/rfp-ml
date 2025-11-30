import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Bell,
  BellRing,
  Plus,
  Settings,
  Trash2,
  Check,
  CheckCheck,
  AlertTriangle,
  Clock,
  FileText,
  Building2,
  Search,
  ToggleLeft,
  ToggleRight,
  ExternalLink,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

interface AlertRule {
  id: number
  name: string
  description: string | null
  alert_type: string
  is_active: boolean
  priority: string
  criteria: Record<string, unknown>
  notification_channels: string[]
  triggered_count: number
  last_triggered_at: string | null
  created_at: string
}

interface AlertNotification {
  id: number
  rule_id: number
  rfp_id: number | null
  title: string
  message: string
  priority: string
  is_read: boolean
  is_dismissed: boolean
  context_data: Record<string, unknown>
  created_at: string
}

interface NotificationCount {
  unread: number
  by_priority: {
    urgent: number
    high: number
    medium: number
    low: number
  }
}

const ALERT_TYPE_ICONS: Record<string, typeof Bell> = {
  new_rfp: FileText,
  deadline_approaching: Clock,
  keyword_match: Search,
  agency_match: Building2,
  score_threshold: AlertTriangle,
}

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-gray-400 text-white',
}

export default function AlertsPage() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('notifications')
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    alert_type: 'keyword_match',
    priority: 'medium',
    criteria: {} as Record<string, unknown>,
    notification_channels: ['in_app'],
  })

  // Fetch notifications
  const { data: notificationsData, isLoading: loadingNotifications } = useQuery({
    queryKey: ['alerts', 'notifications'],
    queryFn: () => api.get<{
      notifications: AlertNotification[]
      total: number
      unread_count: number
    }>('/alerts/notifications?limit=50'),
  })

  // Fetch notification count
  const { data: countData } = useQuery({
    queryKey: ['alerts', 'count'],
    queryFn: () => api.get<NotificationCount>('/alerts/notifications/count'),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch alert rules
  const { data: rulesData, isLoading: loadingRules } = useQuery({
    queryKey: ['alerts', 'rules'],
    queryFn: () => api.get<{ rules: AlertRule[]; total: number; active_count: number }>(
      '/alerts/rules'
    ),
  })

  // Fetch alert types info (used for form validation)
  useQuery({
    queryKey: ['alerts', 'types'],
    queryFn: () => api.get<{ alert_types: Record<string, unknown> }>('/alerts/types'),
  })

  // Create rule mutation
  const createRule = useMutation({
    mutationFn: (data: typeof newRule) => api.post('/alerts/rules', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', 'rules'] })
      setIsCreateDialogOpen(false)
      setNewRule({
        name: '',
        description: '',
        alert_type: 'keyword_match',
        priority: 'medium',
        criteria: {},
        notification_channels: ['in_app'],
      })
    },
  })

  // Toggle rule mutation
  const toggleRule = useMutation({
    mutationFn: (ruleId: number) => api.post(`/alerts/rules/${ruleId}/toggle`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', 'rules'] })
    },
  })

  // Delete rule mutation
  const deleteRule = useMutation({
    mutationFn: (ruleId: number) => api.delete(`/alerts/rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', 'rules'] })
    },
  })

  // Mark notification read
  const markRead = useMutation({
    mutationFn: (notificationId: number) =>
      api.post(`/alerts/notifications/${notificationId}/action`, {
        action: 'mark_read',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  // Mark all read
  const markAllRead = useMutation({
    mutationFn: () => api.post('/alerts/notifications/mark-all-read', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  // Dismiss notification
  const dismissNotification = useMutation({
    mutationFn: (notificationId: number) =>
      api.post(`/alerts/notifications/${notificationId}/action`, {
        action: 'dismiss',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  // Evaluate alerts
  const evaluateAlerts = useMutation({
    mutationFn: () => api.post('/alerts/evaluate', {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  const getAlertTypeIcon = (alertType: string) => {
    const Icon = ALERT_TYPE_ICONS[alertType] || Bell
    return <Icon className="h-4 w-4" />
  }

  const formatAlertType = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const handleCreateRule = () => {
    createRule.mutate(newRule)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BellRing className="h-8 w-8" />
            Smart Alerts
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure alerts and monitor RFP notifications
          </p>
        </div>

        <div className="flex items-center gap-2">
          {countData && countData.unread > 0 && (
            <Badge variant="destructive" className="text-sm">
              {countData.unread} unread
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => evaluateAlerts.mutate()}
            disabled={evaluateAlerts.isPending}
          >
            {evaluateAlerts.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Check Now
          </Button>
        </div>
      </div>

      {/* Priority Summary */}
      {countData && (
        <div className="grid grid-cols-4 gap-4">
          {[
            { key: 'urgent', label: 'Urgent', color: 'bg-red-100 border-red-300' },
            { key: 'high', label: 'High', color: 'bg-orange-100 border-orange-300' },
            { key: 'medium', label: 'Medium', color: 'bg-yellow-100 border-yellow-300' },
            { key: 'low', label: 'Low', color: 'bg-gray-100 border-gray-300' },
          ].map(({ key, label, color }) => (
            <Card key={key} className={cn('border-2', color)}>
              <CardContent className="pt-4">
                <div className="text-2xl font-bold">
                  {countData.by_priority[key as keyof typeof countData.by_priority]}
                </div>
                <div className="text-sm text-muted-foreground">{label} Priority</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
            {notificationsData && notificationsData.unread_count > 0 && (
              <Badge variant="secondary" className="ml-1">
                {notificationsData.unread_count}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="rules" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Alert Rules
            {rulesData && (
              <Badge variant="outline" className="ml-1">
                {rulesData.active_count}/{rulesData.total}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Recent Notifications</h2>
            {notificationsData && notificationsData.unread_count > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => markAllRead.mutate()}
                disabled={markAllRead.isPending}
              >
                <CheckCheck className="h-4 w-4 mr-2" />
                Mark All Read
              </Button>
            )}
          </div>

          {loadingNotifications ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : notificationsData?.notifications.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <Bell className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No notifications yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Create alert rules to start receiving notifications
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {notificationsData?.notifications.map((notification) => (
                <Card
                  key={notification.id}
                  className={cn(
                    'transition-colors',
                    !notification.is_read && 'border-l-4 border-l-primary bg-primary/5'
                  )}
                >
                  <CardContent className="py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 flex-1">
                        <Badge className={cn('mt-0.5', PRIORITY_COLORS[notification.priority])}>
                          {notification.priority}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium truncate">{notification.title}</h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            {notification.message}
                          </p>
                          <p className="text-xs text-muted-foreground mt-2">
                            {new Date(notification.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        {notification.rfp_id && (
                          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                            <a href={`/rfps/${notification.context_data.rfp_id || notification.rfp_id}`}>
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        {!notification.is_read && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => markRead.mutate(notification.id)}
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground"
                          onClick={() => dismissNotification.mutate(notification.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Rules Tab */}
        <TabsContent value="rules" className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Alert Rules</h2>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Rule
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Alert Rule</DialogTitle>
                  <DialogDescription>
                    Set up a new alert rule to monitor RFPs
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Rule Name</Label>
                    <Input
                      id="name"
                      value={newRule.name}
                      onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                      placeholder="e.g., High-value IT contracts"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={newRule.description}
                      onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                      placeholder="Optional description..."
                      rows={2}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="alert_type">Alert Type</Label>
                    <Select
                      value={newRule.alert_type}
                      onValueChange={(value) => setNewRule({ ...newRule, alert_type: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="keyword_match">Keyword Match</SelectItem>
                        <SelectItem value="agency_match">Agency Match</SelectItem>
                        <SelectItem value="naics_match">NAICS Match</SelectItem>
                        <SelectItem value="deadline_approaching">Deadline Approaching</SelectItem>
                        <SelectItem value="score_threshold">Score Threshold</SelectItem>
                        <SelectItem value="new_rfp">New RFP</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="priority">Priority</Label>
                    <Select
                      value={newRule.priority}
                      onValueChange={(value) => setNewRule({ ...newRule, priority: value })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="urgent">Urgent</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="low">Low</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Criteria based on alert type */}
                  {newRule.alert_type === 'keyword_match' && (
                    <div className="space-y-2">
                      <Label htmlFor="keywords">Keywords (comma-separated)</Label>
                      <Input
                        id="keywords"
                        placeholder="e.g., cybersecurity, cloud, IT services"
                        onChange={(e) =>
                          setNewRule({
                            ...newRule,
                            criteria: {
                              keywords: e.target.value.split(',').map((k) => k.trim()).filter(Boolean),
                              match_title: true,
                              match_description: true,
                            },
                          })
                        }
                      />
                    </div>
                  )}

                  {newRule.alert_type === 'deadline_approaching' && (
                    <div className="space-y-2">
                      <Label htmlFor="days">Days Before Deadline</Label>
                      <Input
                        id="days"
                        type="number"
                        defaultValue={7}
                        min={1}
                        max={30}
                        onChange={(e) =>
                          setNewRule({
                            ...newRule,
                            criteria: { days_before: parseInt(e.target.value) },
                          })
                        }
                      />
                    </div>
                  )}

                  {newRule.alert_type === 'score_threshold' && (
                    <div className="space-y-2">
                      <Label htmlFor="score">Minimum Score (%)</Label>
                      <Input
                        id="score"
                        type="number"
                        defaultValue={75}
                        min={1}
                        max={100}
                        onChange={(e) =>
                          setNewRule({
                            ...newRule,
                            criteria: {
                              min_score: parseInt(e.target.value) / 100,
                              score_type: 'triage',
                            },
                          })
                        }
                      />
                    </div>
                  )}
                </div>

                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateRule} disabled={!newRule.name || createRule.isPending}>
                    {createRule.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : null}
                    Create Rule
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loadingRules ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : rulesData?.rules.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <Settings className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No alert rules configured</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Create your first rule to start monitoring RFPs
                </p>
                <Button className="mt-4" onClick={() => setIsCreateDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Rule
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {rulesData?.rules.map((rule) => (
                <Card key={rule.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-muted">
                          {getAlertTypeIcon(rule.alert_type)}
                        </div>
                        <div>
                          <CardTitle className="text-lg">{rule.name}</CardTitle>
                          <CardDescription>{rule.description || formatAlertType(rule.alert_type)}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={rule.is_active ? 'default' : 'secondary'}>
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                        <Badge className={PRIORITY_COLORS[rule.priority]}>{rule.priority}</Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-6 text-sm text-muted-foreground">
                        <span>Triggered: {rule.triggered_count} times</span>
                        {rule.last_triggered_at && (
                          <span>
                            Last: {new Date(rule.last_triggered_at).toLocaleDateString()}
                          </span>
                        )}
                        <span>Channels: {rule.notification_channels.join(', ')}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => toggleRule.mutate(rule.id)}
                          title={rule.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {rule.is_active ? (
                            <ToggleRight className="h-5 w-5 text-green-500" />
                          ) : (
                            <ToggleLeft className="h-5 w-5 text-gray-400" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive"
                          onClick={() => {
                            if (confirm('Delete this alert rule?')) {
                              deleteRule.mutate(rule.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
