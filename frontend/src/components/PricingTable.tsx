import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Download, DollarSign, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { api } from '../services/api'

interface LineItem {
  category: string
  description: string
  unit: string
  quantity: number
  unit_price: number
  total: number
  is_optional: boolean
  notes: string
}

interface YearlyBudget {
  year: number
  year_label: string
  is_optional: boolean
  subtotal: number
  line_items: LineItem[]
}

interface Deliverable {
  id: string
  name: string
  description: string
  total: number
  total_with_optional: number
  yearly_budgets: YearlyBudget[]
}

interface PricingTableData {
  rfp_id: string
  rfp_title: string
  company_name: string
  generated_at: string
  deliverables: Deliverable[]
  grand_total: number
  grand_total_with_optional: number
  notes: string[]
}

interface PricingTableProps {
  rfpId: string
}

export default function PricingTable({ rfpId }: PricingTableProps) {
  const [options, setOptions] = useState({
    num_websites: 3,
    base_years: 3,
    optional_years: 2,
    base_budget_per_site: 50000,
  })

  const [expandedDeliverables, setExpandedDeliverables] = useState<Set<string>>(new Set())
  const [expandedYears, setExpandedYears] = useState<Set<string>>(new Set())

  // Generate pricing table
  const {
    data: pricingData,
    isLoading,
    refetch,
  } = useQuery<PricingTableData>({
    queryKey: ['pricing-table', rfpId, options],
    queryFn: () => api.generatePricingTable(rfpId, options),
    enabled: false, // Don't fetch automatically
  })

  const generateMutation = useMutation({
    mutationFn: () => api.generatePricingTable(rfpId, options),
    onSuccess: () => {
      refetch()
      toast.success('Pricing table generated')
    },
    onError: () => {
      toast.error('Failed to generate pricing table')
    },
  })

  const downloadCSV = async () => {
    try {
      const blob = await api.downloadPricingTableCSV(rfpId, options)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pricing_table_${rfpId}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success('CSV downloaded')
    } catch (error) {
      toast.error('Failed to download CSV')
    }
  }

  const toggleDeliverable = (id: string) => {
    const newSet = new Set(expandedDeliverables)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedDeliverables(newSet)
  }

  const toggleYear = (key: string) => {
    const newSet = new Set(expandedYears)
    if (newSet.has(key)) {
      newSet.delete(key)
    } else {
      newSet.add(key)
    }
    setExpandedYears(newSet)
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Bid Pricing Configuration
          </CardTitle>
          <CardDescription>
            Configure the pricing parameters for this multi-year, multi-website project
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="num_websites">Number of Websites</Label>
              <Input
                id="num_websites"
                type="number"
                min={1}
                max={10}
                value={options.num_websites}
                onChange={(e) =>
                  setOptions({ ...options, num_websites: parseInt(e.target.value) || 1 })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_years">Base Contract Years</Label>
              <Input
                id="base_years"
                type="number"
                min={1}
                max={5}
                value={options.base_years}
                onChange={(e) =>
                  setOptions({ ...options, base_years: parseInt(e.target.value) || 1 })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="optional_years">Optional Years</Label>
              <Input
                id="optional_years"
                type="number"
                min={0}
                max={5}
                value={options.optional_years}
                onChange={(e) =>
                  setOptions({ ...options, optional_years: parseInt(e.target.value) || 0 })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="base_budget">Base Budget/Site ($)</Label>
              <Input
                id="base_budget"
                type="number"
                min={10000}
                step={5000}
                value={options.base_budget_per_site}
                onChange={(e) =>
                  setOptions({
                    ...options,
                    base_budget_per_site: parseInt(e.target.value) || 50000,
                  })
                }
              />
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <DollarSign className="mr-2 h-4 w-4" />
                  Generate Pricing Table
                </>
              )}
            </Button>

            {pricingData && (
              <Button variant="outline" onClick={downloadCSV}>
                <Download className="mr-2 h-4 w-4" />
                Download CSV
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pricing Table Results */}
      {isLoading && (
        <div className="text-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-gray-400" />
          <p className="mt-2 text-gray-500">Generating pricing table...</p>
        </div>
      )}

      {pricingData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-gray-500">Base Contract Total</div>
                <div className="text-2xl font-bold text-green-600">
                  {formatCurrency(pricingData.grand_total)}
                </div>
                <div className="text-xs text-gray-400">
                  Years 1-{options.base_years}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-gray-500">Including Optional Years</div>
                <div className="text-2xl font-bold text-blue-600">
                  {formatCurrency(pricingData.grand_total_with_optional)}
                </div>
                <div className="text-xs text-gray-400">
                  Years 1-{options.base_years + options.optional_years}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-sm text-gray-500">Per Website Average</div>
                <div className="text-2xl font-bold text-purple-600">
                  {formatCurrency(pricingData.grand_total / options.num_websites)}
                </div>
                <div className="text-xs text-gray-400">
                  {options.num_websites} websites
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Cost Breakdown</CardTitle>
              <CardDescription>
                Click on deliverables and years to expand line items
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {pricingData.deliverables.map((deliverable) => (
                  <div key={deliverable.id} className="border rounded-lg">
                    {/* Deliverable Header */}
                    <button
                      className="w-full flex items-center justify-between p-4 hover:bg-gray-50"
                      onClick={() => toggleDeliverable(deliverable.id)}
                    >
                      <div className="flex items-center gap-2">
                        {expandedDeliverables.has(deliverable.id) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                        <span className="font-medium">{deliverable.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{formatCurrency(deliverable.total)}</div>
                        <div className="text-xs text-gray-500">
                          {formatCurrency(deliverable.total_with_optional)} with options
                        </div>
                      </div>
                    </button>

                    {/* Yearly Breakdowns */}
                    {expandedDeliverables.has(deliverable.id) && (
                      <div className="border-t">
                        {deliverable.yearly_budgets.map((yearly) => {
                          const yearKey = `${deliverable.id}-${yearly.year}`
                          return (
                            <div key={yearly.year} className="border-b last:border-b-0">
                              {/* Year Header */}
                              <button
                                className="w-full flex items-center justify-between p-3 pl-8 hover:bg-gray-50"
                                onClick={() => toggleYear(yearKey)}
                              >
                                <div className="flex items-center gap-2">
                                  {expandedYears.has(yearKey) ? (
                                    <ChevronDown className="h-4 w-4" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4" />
                                  )}
                                  <span>{yearly.year_label}</span>
                                  {yearly.is_optional && (
                                    <Badge variant="secondary">Optional</Badge>
                                  )}
                                </div>
                                <span className="font-medium">
                                  {formatCurrency(yearly.subtotal)}
                                </span>
                              </button>

                              {/* Line Items Table */}
                              {expandedYears.has(yearKey) && (
                                <div className="pl-12 pr-4 pb-4">
                                  <Table>
                                    <TableHeader>
                                      <TableRow>
                                        <TableHead>Category</TableHead>
                                        <TableHead>Description</TableHead>
                                        <TableHead className="text-right">Qty</TableHead>
                                        <TableHead className="text-right">Unit Price</TableHead>
                                        <TableHead className="text-right">Total</TableHead>
                                      </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                      {yearly.line_items.map((item, idx) => (
                                        <TableRow
                                          key={idx}
                                          className={item.is_optional ? 'text-gray-400' : ''}
                                        >
                                          <TableCell>
                                            <div className="flex items-center gap-2">
                                              {item.category}
                                              {item.is_optional && (
                                                <Badge variant="outline" className="text-xs">
                                                  Optional
                                                </Badge>
                                              )}
                                            </div>
                                          </TableCell>
                                          <TableCell>
                                            {item.description}
                                            {item.notes && (
                                              <div className="text-xs text-gray-400">
                                                {item.notes}
                                              </div>
                                            )}
                                          </TableCell>
                                          <TableCell className="text-right">
                                            {item.quantity} {item.unit}
                                          </TableCell>
                                          <TableCell className="text-right">
                                            {formatCurrency(item.unit_price)}
                                          </TableCell>
                                          <TableCell className="text-right font-medium">
                                            {formatCurrency(item.total)}
                                          </TableCell>
                                        </TableRow>
                                      ))}
                                    </TableBody>
                                  </Table>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          {pricingData.notes && pricingData.notes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Notes & Assumptions</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                  {pricingData.notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
