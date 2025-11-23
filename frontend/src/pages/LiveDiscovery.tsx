import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api } from '@/services/api'
import { Activity, Play, StopCircle, Terminal } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface LogEntry {
    timestamp: string
    message: string
    type: 'info' | 'success' | 'error' | 'warning'
}

export default function LiveDiscovery() {
    const [isRunning, setIsRunning] = useState(false)
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [stats, setStats] = useState({ found: 0, processed: 0, qualified: 0 })
    const [jobId, setJobId] = useState<string | null>(null)

    // Config
    const [limit, setLimit] = useState(50)
    const [daysBack, setDaysBack] = useState(30)

    const scrollRef = useRef<HTMLDivElement>(null)

    const addLog = (message: string, type: LogEntry['type'] = 'info') => {
        setLogs(prev => [...prev, {
            timestamp: new Date().toLocaleTimeString(),
            message,
            type
        }])
    }

    const startDiscovery = async () => {
        setIsRunning(true)
        setStats({ found: 0, processed: 0, qualified: 0 })
        setLogs([])
        addLog(`Starting discovery (Limit: ${limit}, Days: ${daysBack})...`, 'info')

        try {
            const response = await api.discoverRFPs({ limit, days_back: daysBack })
            setJobId(response.data.job_id)
            addLog(`Job started: ${response.data.job_id}`, 'success')
        } catch (error: any) {
            addLog(`Failed to start: ${error.message}`, 'error')
            setIsRunning(false)
        }
    }

    const stopDiscovery = () => {
        // In a real scenario, we'd call an API to cancel the job
        setIsRunning(false)
        setJobId(null)
        addLog('Discovery stopped by user', 'warning')
    }

    // Poll for updates
    useEffect(() => {
        if (!jobId || !isRunning) return

        const interval = setInterval(async () => {
            try {
                const status = await api.getDiscoveryStatus(jobId)

                // Update stats
                setStats({
                    found: status.discovered_count || 0,
                    processed: status.processed_count || 0,
                    qualified: 0 // Placeholder until we have this metric
                })

                // Simulate log stream based on status changes (in real app, use WebSocket)
                if (status.status === 'searching' && logs.length < 2) {
                    addLog('Searching SAM.gov API...', 'info')
                }
                if (status.status === 'processing' && logs.length < 3) {
                    addLog('Processing discovered RFPs through ML pipeline...', 'info')
                }
                if (status.status === 'completed') {
                    addLog(`Discovery complete! Found ${status.discovered_count} RFPs.`, 'success')
                    setIsRunning(false)
                    setJobId(null)
                }
                if (status.status === 'failed') {
                    addLog('Discovery failed.', 'error')
                    setIsRunning(false)
                    setJobId(null)
                }

            } catch (error) {
                console.error(error)
            }
        }, 2000)

        return () => clearInterval(interval)
    }, [jobId, isRunning, logs.length])

    // Auto-scroll logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [logs])

    return (
        <div className="h-full flex flex-col gap-6 p-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Live Discovery</h1>
                    <p className="text-muted-foreground">Real-time monitoring of RFP discovery and processing.</p>
                </div>
                <div className="flex gap-3 items-center bg-card p-2 rounded-lg border shadow-sm">
                    <div className="flex items-center gap-2 px-2">
                        <span className="text-sm font-medium">Limit:</span>
                        <Input
                            type="number"
                            className="w-20 h-8"
                            value={limit}
                            onChange={e => setLimit(Number(e.target.value))}
                        />
                    </div>
                    <div className="flex items-center gap-2 px-2 border-l">
                        <span className="text-sm font-medium">Days:</span>
                        <Input
                            type="number"
                            className="w-20 h-8"
                            value={daysBack}
                            onChange={e => setDaysBack(Number(e.target.value))}
                        />
                    </div>
                    <Button
                        onClick={isRunning ? stopDiscovery : startDiscovery}
                        variant={isRunning ? "destructive" : "default"}
                        className="ml-2"
                    >
                        {isRunning ? (
                            <><StopCircle className="mr-2 h-4 w-4" /> Stop</>
                        ) : (
                            <><Play className="mr-2 h-4 w-4" /> Start Discovery</>
                        )}
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Discovered</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.found}</div>
                        <p className="text-xs text-muted-foreground">RFPs found in current session</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Processed</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.processed}</div>
                        <p className="text-xs text-muted-foreground">Analyzed by ML pipeline</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Qualified</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">{stats.qualified}</div>
                        <p className="text-xs text-muted-foreground">Passed initial screening</p>
                    </CardContent>
                </Card>
            </div>

            <Card className="flex-1 flex flex-col min-h-0 bg-black text-green-400 font-mono border-slate-800">
                <CardHeader className="border-b border-slate-800 py-3">
                    <div className="flex items-center gap-2">
                        <Terminal className="h-4 w-4" />
                        <CardTitle className="text-sm font-normal">System Log</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="flex-1 p-0 min-h-0 relative">
                    <div className="absolute inset-0 overflow-auto p-4 space-y-1" ref={scrollRef}>
                        {logs.length === 0 && (
                            <div className="text-slate-600 italic">Ready to start...</div>
                        )}
                        {logs.map((log, i) => (
                            <div key={i} className="flex gap-3 text-sm">
                                <span className="text-slate-500 shrink-0">[{log.timestamp}]</span>
                                <span className={
                                    log.type === 'error' ? 'text-red-400' :
                                        log.type === 'success' ? 'text-green-400' :
                                            log.type === 'warning' ? 'text-yellow-400' :
                                                'text-slate-300'
                                }>
                                    {log.type === 'info' && '> '}
                                    {log.type === 'success' && '✓ '}
                                    {log.type === 'error' && '✗ '}
                                    {log.type === 'warning' && '! '}
                                    {log.message}
                                </span>
                            </div>
                        ))}
                        {isRunning && (
                            <div className="animate-pulse text-slate-500">_</div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
