import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../services/api'
import { Calculator, RefreshCw, TrendingUp } from 'lucide-react'
import { Slider } from '@/components/ui/slider'
import { Button } from '@/components/ui/button'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

// Simple UI components since we might not have full shadcn library installed in this env
const Card = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
  <div className={`bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm ${className}`}>
    {children}
  </div>
)

export default function PricingSimulator() {
  const { rfpId } = useParams<{ rfpId: string }>()
  const [searchParams] = useSearchParams()
  const rfpTitle = searchParams.get('title') || 'RFP Pricing Analysis'

  // State for sliders
  const [laborMult, setLaborMult] = useState(1.0)
  const [materialMult, setMaterialMult] = useState(1.0)
  const [risk, setRisk] = useState(0.0)
  const [margin, setMargin] = useState(0.0)

  // Query for initial simulation (default params)
  const { data: initialResults, isLoading } = useQuery({
    queryKey: ['pricing', rfpId],
    queryFn: () => api.runPricingScenarios(rfpId!, {
      labor_cost_multiplier: 1.0,
      material_cost_multiplier: 1.0,
      risk_contingency_percent: 0.0,
      desired_margin: 0.0
    }),
    enabled: !!rfpId
  })

  // Mutation for custom updates
  const mutation = useMutation({
    mutationFn: (params: any) => api.runPricingScenarios(rfpId!, params)
  })

  const handleSimulate = () => {
    mutation.mutate({
      labor_cost_multiplier: laborMult,
      material_cost_multiplier: materialMult,
      risk_contingency_percent: risk,
      desired_margin: margin
    })
  }

  const results = mutation.data || initialResults

  if (isLoading) return <div className="p-8">Loading pricing engine...</div>

  // Format data for chart
  const chartData = results ? Object.entries(results).map(([name, data]: [string, any]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    Price: data.total_price,
    Cost: data.total_price / (1 + (data.margin_percent / 100)),
    Profit: data.total_price - (data.total_price / (1 + (data.margin_percent / 100))),
    margin: data.margin_percent
  })) : []

  const customResult = results?.['custom']

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Calculator className="h-6 w-6 text-blue-500" />
            Pricing War Games
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            {rfpTitle}
          </p>
        </div>
        <Button onClick={handleSimulate} disabled={mutation.isPending}>
          {mutation.isPending ? <RefreshCw className="animate-spin mr-2 h-4 w-4"/> : <TrendingUp className="mr-2 h-4 w-4"/>}
          Run Simulation
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <Card className="p-6 space-y-8 lg:col-span-1">
          <h3 className="font-semibold text-lg">Scenario Parameters</h3>
          
          <div className="space-y-4">
            <div className="flex justify-between">
              <label className="text-sm font-medium">Labor Cost Multiplier</label>
              <span className="text-sm text-slate-500">{laborMult.toFixed(2)}x</span>
            </div>
            <Slider 
              value={[laborMult]} 
              min={0.8} max={1.5} step={0.05} 
              onValueChange={(val) => setLaborMult(val[0])} 
            />
            <p className="text-xs text-slate-400">Adjust for potential overtime or wage increases.</p>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between">
              <label className="text-sm font-medium">Material Cost Multiplier</label>
              <span className="text-sm text-slate-500">{materialMult.toFixed(2)}x</span>
            </div>
            <Slider 
              value={[materialMult]} 
              min={0.8} max={1.5} step={0.05}
              onValueChange={(val) => setMaterialMult(val[0])}
            />
            <p className="text-xs text-slate-400">Adjust for supply chain volatility.</p>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between">
              <label className="text-sm font-medium">Risk Contingency</label>
              <span className="text-sm text-slate-500">{(risk * 100).toFixed(0)}%</span>
            </div>
            <Slider 
              value={[risk]} 
              min={0.0} max={0.30} step={0.01}
              onValueChange={(val) => setRisk(val[0])}
            />
            <p className="text-xs text-slate-400">Buffer for unknown variables.</p>
          </div>

          <div className="space-y-4">
            <div className="flex justify-between">
              <label className="text-sm font-medium">Target Margin</label>
              <span className="text-sm text-slate-500">{(margin * 100).toFixed(0)}%</span>
            </div>
            <Slider 
              value={[margin]} 
              min={0.0} max={0.50} step={0.01}
              onValueChange={(val) => setMargin(val[0])}
            />
            <p className="text-xs text-slate-400">0% uses strategy default.</p>
          </div>
        </Card>

        {/* Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(results || {}).map(([key, val]: [string, any]) => (
              <Card key={key} className={`p-4 ${key === 'custom' ? 'border-blue-500 border-2' : ''}`}>
                <div className="text-xs text-slate-500 uppercase font-bold mb-1">{key.replace('_', ' ')}</div>
                <div className="text-lg font-bold text-slate-900 dark:text-white">
                  ${val.total_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </div>
                <div className={`text-sm font-medium ${(val.margin_percent ?? 0) < 15 ? 'text-red-500' : 'text-green-500'}`}>
                  {(val.margin_percent ?? 0).toFixed(1)}% Margin
                </div>
              </Card>
            ))}
          </div>

          {/* Chart */}
          <Card className="p-6 h-[400px]">
            <h3 className="font-semibold mb-4">Scenario Comparison</h3>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip 
                  formatter={(value: number) => [`$${value.toLocaleString()}`, '']}
                  contentStyle={{ backgroundColor: '#1e293b', color: '#fff', border: 'none' }}
                />
                <Legend />
                <Bar dataKey="Cost" stackId="a" fill="#64748b" />
                <Bar dataKey="Profit" stackId="a" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* Breakdown Table */}
          {customResult && (
             <Card className="p-6">
                <h3 className="font-semibold mb-4">Custom Scenario Breakdown</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b dark:border-slate-700 text-left">
                        <th className="pb-2">Component</th>
                        <th className="pb-2 text-right">Value</th>
                        <th className="pb-2 text-right">% of Total</th>
                      </tr>
                    </thead>
                    <tbody className="text-slate-600 dark:text-slate-300">
                      {Object.entries(customResult.breakdown).map(([key, val]: [string, any]) => (
                        <tr key={key} className="border-b dark:border-slate-700/50 last:border-0">
                          <td className="py-2 capitalize">{key.replace('_', ' ')}</td>
                          <td className="py-2 text-right font-mono">${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="py-2 text-right">
                            {((val / customResult.total_price) * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                      <tr className="font-bold text-slate-900 dark:text-white bg-slate-50 dark:bg-slate-800">
                        <td className="py-3 pl-2">TOTAL PRICE</td>
                        <td className="py-3 text-right font-mono">${customResult.total_price.toLocaleString()}</td>
                        <td className="py-3 text-right">100.0%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
             </Card>
          )}
        </div>
      </div>
    </div>
  )
}
