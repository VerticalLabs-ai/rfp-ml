# Pricing Workspace Enhancement Plan

**Date**: December 5, 2025
**Author**: AI Assistant
**Status**: Draft
**Priority**: High

## Executive Summary

Enhance the existing pricing capabilities with a comprehensive visual interface and AI-powered optimization. This builds upon the mature pricing infrastructure already in place (pricing engine, war gaming, PTW analysis) by adding:

1. **Unified Pricing Workspace** - Central hub for all pricing activities
2. **Interactive Cost Builder** - Line-item cost breakdown with labor rate management
3. **Historical Pricing Intelligence** - Trend analysis and comparable contract insights
4. **AI-Powered Recommendations** - Optimal pricing suggestions with confidence scoring
5. **Enhanced Price-to-Win** - Competitor estimation and margin impact analysis
6. **Proposal Integration** - Seamless connection to proposal generation

---

## Existing Infrastructure Summary

### What Already Exists

**Backend (`src/pricing/`):**
- `pricing_engine.py` (855 lines) - 4 strategies, NAICS analysis, war gaming, PTW, subcontractor ID
- `win_probability.py` - Win probability model with price/probability solving
- `rag_pricing_integration.py` - RAG-enhanced pricing with historical context
- `pricing_table_generator.py` (520 lines) - Multi-year, multi-deliverable tables

**Database:**
- `PricingResult` model with full breakdown storage (JSON fields for components/risks)

**API Endpoints:**
- `POST /{rfp_id}/pricing/scenarios` - War gaming
- `GET /{rfp_id}/pricing/subcontractors` - Subcontractor opportunities
- `GET /{rfp_id}/pricing/ptw` - Price-to-Win calculation
- `POST /{rfp_id}/pricing-table` - Generate detailed tables

**Frontend:**
- `PricingSimulator.tsx` - War gaming with sliders and charts
- `PricingTable.tsx` - Multi-year pricing table with CSV export

### Gaps to Address

| Gap | Impact | Solution in This Plan |
|-----|--------|----------------------|
| No central pricing workspace | Scattered UX | Task 1: Unified workspace |
| Static cost baselines | Inflexible | Task 2: Dynamic cost builder |
| No pricing trends | Limited intelligence | Task 3: Trend analytics |
| No AI recommendations | Manual decisions | Task 4: Recommendation engine |
| Basic PTW | No competitor modeling | Task 5: Enhanced PTW |
| No proposal integration | Manual copy/paste | Task 6: Auto-integration |
| No labor rate management | Hardcoded rates | Task 2: Rate tables |

---

## Implementation Plan

### Task 1: Create Unified Pricing Workspace Page

**File**: `frontend/src/pages/PricingWorkspace.tsx`

**Purpose**: Central hub that consolidates all pricing features into a single, intuitive interface.

**UI Structure**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Pricing Workspace - [RFP Title]                            [Save] [Export]│
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│ │ Total Price │ │ Base Cost   │ │ Target Margin│ │ Win Prob    │        │
│ │ $1,234,567  │ │ $987,654    │ │ 25%         │ │ 72%         │        │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────────────────────┤
│ [Cost Builder] [Market Intel] [AI Recommend] [PTW Analysis] [Scenarios]│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─ Tab Content ──────────────────────────────────────────────────┐   │
│   │                                                                 │   │
│   │   (Dynamic content based on selected tab)                       │   │
│   │                                                                 │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ Sidebar: Similar Contracts | Risk Factors | Quick Actions              │
└─────────────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```typescript
// frontend/src/pages/PricingWorkspace.tsx

import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CostBuilder } from '@/components/pricing/CostBuilder';
import { MarketIntelligence } from '@/components/pricing/MarketIntelligence';
import { AIRecommendations } from '@/components/pricing/AIRecommendations';
import { PTWAnalysis } from '@/components/pricing/PTWAnalysis';
import { ScenarioModeler } from '@/components/pricing/ScenarioModeler';
import { PricingSummaryCards } from '@/components/pricing/PricingSummaryCards';
import { SimilarContractsSidebar } from '@/components/pricing/SimilarContractsSidebar';
import api from '@/services/api';
import { useToast } from '@/hooks/use-toast';

interface PricingWorkspaceState {
  rfp: RFPOpportunity | null;
  pricing: PricingResult | null;
  costBreakdown: CostBreakdown | null;
  isLoading: boolean;
  isDirty: boolean;
}

export default function PricingWorkspace() {
  const { rfpId } = useParams<{ rfpId: string }>();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'cost-builder');
  const [state, setState] = useState<PricingWorkspaceState>({
    rfp: null,
    pricing: null,
    costBreakdown: null,
    isLoading: true,
    isDirty: false,
  });
  const { toast } = useToast();

  useEffect(() => {
    loadPricingData();
  }, [rfpId]);

  const loadPricingData = async () => {
    try {
      setState(s => ({ ...s, isLoading: true }));
      const [rfpData, pricingData] = await Promise.all([
        api.getRFP(rfpId!),
        api.getPricingResult(rfpId!).catch(() => null),
      ]);
      setState(s => ({
        ...s,
        rfp: rfpData,
        pricing: pricingData,
        isLoading: false,
      }));
    } catch (error) {
      toast({ variant: 'destructive', title: 'Failed to load pricing data' });
      setState(s => ({ ...s, isLoading: false }));
    }
  };

  const handleSave = async () => {
    // Implementation for saving pricing data
  };

  const handleExport = async (format: 'json' | 'csv' | 'pdf') => {
    // Implementation for exporting pricing analysis
  };

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 p-6 space-y-6 overflow-auto">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Pricing Workspace</h1>
            <p className="text-muted-foreground">{state.rfp?.title}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => handleExport('pdf')}>
              Export PDF
            </Button>
            <Button onClick={handleSave} disabled={!state.isDirty}>
              Save Changes
            </Button>
          </div>
        </header>

        {/* Summary Cards */}
        <PricingSummaryCards
          totalPrice={state.pricing?.total_price}
          baseCost={state.pricing?.base_cost}
          margin={state.pricing?.margin_percentage}
          winProbability={state.pricing?.confidence_score}
        />

        {/* Tabbed Interface */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="cost-builder">Cost Builder</TabsTrigger>
            <TabsTrigger value="market-intel">Market Intel</TabsTrigger>
            <TabsTrigger value="ai-recommend">AI Recommend</TabsTrigger>
            <TabsTrigger value="ptw-analysis">PTW Analysis</TabsTrigger>
            <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
          </TabsList>

          <TabsContent value="cost-builder">
            <CostBuilder
              rfpId={rfpId!}
              initialData={state.costBreakdown}
              onUpdate={(data) => setState(s => ({ ...s, costBreakdown: data, isDirty: true }))}
            />
          </TabsContent>

          <TabsContent value="market-intel">
            <MarketIntelligence rfpId={rfpId!} naicsCode={state.rfp?.naics_code} />
          </TabsContent>

          <TabsContent value="ai-recommend">
            <AIRecommendations
              rfpId={rfpId!}
              currentPricing={state.pricing}
              onApplyRecommendation={(rec) => {/* Apply recommendation */}}
            />
          </TabsContent>

          <TabsContent value="ptw-analysis">
            <PTWAnalysis rfpId={rfpId!} currentPrice={state.pricing?.total_price} />
          </TabsContent>

          <TabsContent value="scenarios">
            <ScenarioModeler rfpId={rfpId!} basePricing={state.pricing} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Sidebar */}
      <SimilarContractsSidebar
        rfpId={rfpId!}
        naicsCode={state.rfp?.naics_code}
        agency={state.rfp?.agency}
      />
    </div>
  );
}
```

**Verification**:
- [ ] Page loads with RFP context
- [ ] All 5 tabs render correctly
- [ ] Summary cards show live data
- [ ] Save/Export buttons functional
- [ ] Sidebar shows similar contracts

---

### Task 2: Interactive Cost Builder Component

**File**: `frontend/src/components/pricing/CostBuilder.tsx`

**Purpose**: Build pricing from the ground up with line items, labor rates, materials, and overhead.

**UI Design**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Cost Builder                                     [+ Add Category] [Reset]│
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ Labor Costs ─────────────────────────────────────────────────────┐   │
│ │ Role             │ Hours │ Rate/Hr │ Total    │ Actions           │   │
│ │─────────────────────────────────────────────────────────────────────│   │
│ │ Project Manager  │  120  │ $150    │ $18,000  │ [Edit] [Delete]   │   │
│ │ Senior Developer │  400  │ $175    │ $70,000  │ [Edit] [Delete]   │   │
│ │ Developer        │  600  │ $125    │ $75,000  │ [Edit] [Delete]   │   │
│ │ Designer         │  200  │ $135    │ $27,000  │ [Edit] [Delete]   │   │
│ │                                    [+ Add Role]                    │   │
│ │ ─────────────────────────────────────────────────────────────────────│   │
│ │ Labor Subtotal                                 $190,000           │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Materials & Equipment ───────────────────────────────────────────┐   │
│ │ Item             │ Qty   │ Unit $  │ Total    │ Actions           │   │
│ │─────────────────────────────────────────────────────────────────────│   │
│ │ Cloud Hosting    │  36   │ $500/mo │ $18,000  │ [Edit] [Delete]   │   │
│ │ Licenses         │   5   │ $2,000  │ $10,000  │ [Edit] [Delete]   │   │
│ │                                    [+ Add Item]                    │   │
│ │ ─────────────────────────────────────────────────────────────────────│   │
│ │ Materials Subtotal                             $28,000            │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Subcontractor Quotes ────────────────────────────────────────────┐   │
│ │ Vendor           │ Scope           │ Quote    │ Actions           │   │
│ │─────────────────────────────────────────────────────────────────────│   │
│ │ SecureTech Inc   │ Security Audit  │ $15,000  │ [Edit] [Delete]   │   │
│ │                                    [+ Add Subcontractor]           │   │
│ │ ─────────────────────────────────────────────────────────────────────│   │
│ │ Subcontractor Subtotal                         $15,000            │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Overhead & Profit ───────────────────────────────────────────────┐   │
│ │ Overhead Rate:    [====15%====]               $34,950             │   │
│ │ G&A Rate:         [====8%=====]               $18,640             │   │
│ │ Profit Margin:    [====12%====]               $27,936             │   │
│ │ ─────────────────────────────────────────────────────────────────────│   │
│ │ TOTAL BID PRICE                                $314,526           │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Implementation**:

```typescript
// frontend/src/components/pricing/CostBuilder.tsx

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Plus, Trash2, Edit2, Save } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface LaborLineItem {
  id: string;
  role: string;
  hours: number;
  ratePerHour: number;
}

interface MaterialLineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  unit: string; // 'each', 'monthly', 'annual'
}

interface SubcontractorQuote {
  id: string;
  vendor: string;
  scope: string;
  quoteAmount: number;
}

interface OverheadConfig {
  overheadRate: number; // percentage
  gaRate: number; // G&A percentage
  profitMargin: number; // percentage
}

interface CostBreakdown {
  labor: LaborLineItem[];
  materials: MaterialLineItem[];
  subcontractors: SubcontractorQuote[];
  overhead: OverheadConfig;
}

interface CostBuilderProps {
  rfpId: string;
  initialData?: CostBreakdown | null;
  onUpdate: (data: CostBreakdown) => void;
}

const DEFAULT_LABOR_RATES: Record<string, number> = {
  'Project Manager': 150,
  'Senior Developer': 175,
  'Developer': 125,
  'Junior Developer': 85,
  'Designer': 135,
  'QA Engineer': 110,
  'DevOps Engineer': 160,
  'Technical Writer': 95,
  'Subject Matter Expert': 200,
};

export function CostBuilder({ rfpId, initialData, onUpdate }: CostBuilderProps) {
  const [breakdown, setBreakdown] = useState<CostBreakdown>(
    initialData || {
      labor: [],
      materials: [],
      subcontractors: [],
      overhead: { overheadRate: 15, gaRate: 8, profitMargin: 12 },
    }
  );

  const [editingId, setEditingId] = useState<string | null>(null);

  // Calculate totals
  const laborTotal = breakdown.labor.reduce(
    (sum, item) => sum + item.hours * item.ratePerHour,
    0
  );
  const materialsTotal = breakdown.materials.reduce(
    (sum, item) => sum + item.quantity * item.unitPrice,
    0
  );
  const subcontractorTotal = breakdown.subcontractors.reduce(
    (sum, item) => sum + item.quoteAmount,
    0
  );
  const directCosts = laborTotal + materialsTotal + subcontractorTotal;
  const overheadAmount = directCosts * (breakdown.overhead.overheadRate / 100);
  const gaAmount = (directCosts + overheadAmount) * (breakdown.overhead.gaRate / 100);
  const subtotalBeforeProfit = directCosts + overheadAmount + gaAmount;
  const profitAmount = subtotalBeforeProfit * (breakdown.overhead.profitMargin / 100);
  const totalPrice = subtotalBeforeProfit + profitAmount;

  const updateBreakdown = useCallback(
    (updates: Partial<CostBreakdown>) => {
      const newBreakdown = { ...breakdown, ...updates };
      setBreakdown(newBreakdown);
      onUpdate(newBreakdown);
    },
    [breakdown, onUpdate]
  );

  const addLaborItem = () => {
    const newItem: LaborLineItem = {
      id: crypto.randomUUID(),
      role: 'Developer',
      hours: 40,
      ratePerHour: DEFAULT_LABOR_RATES['Developer'],
    };
    updateBreakdown({ labor: [...breakdown.labor, newItem] });
    setEditingId(newItem.id);
  };

  const addMaterialItem = () => {
    const newItem: MaterialLineItem = {
      id: crypto.randomUUID(),
      description: 'New Item',
      quantity: 1,
      unitPrice: 0,
      unit: 'each',
    };
    updateBreakdown({ materials: [...breakdown.materials, newItem] });
    setEditingId(newItem.id);
  };

  const addSubcontractor = () => {
    const newItem: SubcontractorQuote = {
      id: crypto.randomUUID(),
      vendor: 'New Vendor',
      scope: 'TBD',
      quoteAmount: 0,
    };
    updateBreakdown({ subcontractors: [...breakdown.subcontractors, newItem] });
    setEditingId(newItem.id);
  };

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="space-y-6">
      {/* Labor Costs Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Labor Costs</CardTitle>
          <Button size="sm" onClick={addLaborItem}>
            <Plus className="h-4 w-4 mr-1" /> Add Role
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Role</TableHead>
                <TableHead className="text-right">Hours</TableHead>
                <TableHead className="text-right">Rate/Hr</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="w-24">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {breakdown.labor.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    {editingId === item.id ? (
                      <select
                        className="w-full border rounded p-1"
                        value={item.role}
                        onChange={(e) => {
                          const role = e.target.value;
                          updateBreakdown({
                            labor: breakdown.labor.map((l) =>
                              l.id === item.id
                                ? { ...l, role, ratePerHour: DEFAULT_LABOR_RATES[role] || l.ratePerHour }
                                : l
                            ),
                          });
                        }}
                      >
                        {Object.keys(DEFAULT_LABOR_RATES).map((role) => (
                          <option key={role} value={role}>{role}</option>
                        ))}
                      </select>
                    ) : (
                      item.role
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {editingId === item.id ? (
                      <Input
                        type="number"
                        className="w-20 text-right"
                        value={item.hours}
                        onChange={(e) =>
                          updateBreakdown({
                            labor: breakdown.labor.map((l) =>
                              l.id === item.id ? { ...l, hours: Number(e.target.value) } : l
                            ),
                          })
                        }
                      />
                    ) : (
                      item.hours.toLocaleString()
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {editingId === item.id ? (
                      <Input
                        type="number"
                        className="w-24 text-right"
                        value={item.ratePerHour}
                        onChange={(e) =>
                          updateBreakdown({
                            labor: breakdown.labor.map((l) =>
                              l.id === item.id ? { ...l, ratePerHour: Number(e.target.value) } : l
                            ),
                          })
                        }
                      />
                    ) : (
                      formatCurrency(item.ratePerHour)
                    )}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(item.hours * item.ratePerHour)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {editingId === item.id ? (
                        <Button size="icon" variant="ghost" onClick={() => setEditingId(null)}>
                          <Save className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button size="icon" variant="ghost" onClick={() => setEditingId(item.id)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() =>
                          updateBreakdown({
                            labor: breakdown.labor.filter((l) => l.id !== item.id),
                          })
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Labor Subtotal: {formatCurrency(laborTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Materials Section - Similar structure */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Materials & Equipment</CardTitle>
          <Button size="sm" onClick={addMaterialItem}>
            <Plus className="h-4 w-4 mr-1" /> Add Item
          </Button>
        </CardHeader>
        <CardContent>
          {/* Similar table structure for materials */}
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Materials Subtotal: {formatCurrency(materialsTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Subcontractors Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Subcontractor Quotes</CardTitle>
          <Button size="sm" onClick={addSubcontractor}>
            <Plus className="h-4 w-4 mr-1" /> Add Subcontractor
          </Button>
        </CardHeader>
        <CardContent>
          {/* Similar table structure for subcontractors */}
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Subcontractor Subtotal: {formatCurrency(subcontractorTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Overhead & Profit Section */}
      <Card>
        <CardHeader>
          <CardTitle>Overhead & Profit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Overhead Rate</span>
              <span>{breakdown.overhead.overheadRate}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.overheadRate]}
              onValueChange={([v]) =>
                updateBreakdown({ overhead: { ...breakdown.overhead, overheadRate: v } })
              }
              max={30}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(overheadAmount)}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span>G&A Rate</span>
              <span>{breakdown.overhead.gaRate}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.gaRate]}
              onValueChange={([v]) =>
                updateBreakdown({ overhead: { ...breakdown.overhead, gaRate: v } })
              }
              max={20}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(gaAmount)}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Profit Margin</span>
              <span>{breakdown.overhead.profitMargin}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.profitMargin]}
              onValueChange={([v]) =>
                updateBreakdown({ overhead: { ...breakdown.overhead, profitMargin: v } })
              }
              max={25}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(profitAmount)}
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="flex justify-between text-xl font-bold">
              <span>TOTAL BID PRICE</span>
              <span>{formatCurrency(totalPrice)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Backend Support** - New endpoint needed:

```python
# api/app/routes/pricing.py (new file)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from api.app.models.database import get_db, PricingResult

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])

class LaborLineItem(BaseModel):
    role: str
    hours: float
    rate_per_hour: float

class MaterialLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    unit: str = "each"

class SubcontractorQuote(BaseModel):
    vendor: str
    scope: str
    quote_amount: float

class OverheadConfig(BaseModel):
    overhead_rate: float = 15.0
    ga_rate: float = 8.0
    profit_margin: float = 12.0

class CostBreakdownInput(BaseModel):
    labor: List[LaborLineItem]
    materials: List[MaterialLineItem]
    subcontractors: List[SubcontractorQuote]
    overhead: OverheadConfig

@router.post("/{rfp_id}/cost-breakdown")
async def save_cost_breakdown(
    rfp_id: int,
    breakdown: CostBreakdownInput,
    db: Session = Depends(get_db)
):
    """Save detailed cost breakdown for an RFP."""
    # Calculate totals
    labor_total = sum(item.hours * item.rate_per_hour for item in breakdown.labor)
    materials_total = sum(item.quantity * item.unit_price for item in breakdown.materials)
    subcontractor_total = sum(item.quote_amount for item in breakdown.subcontractors)

    direct_costs = labor_total + materials_total + subcontractor_total
    overhead_amount = direct_costs * (breakdown.overhead.overhead_rate / 100)
    ga_amount = (direct_costs + overhead_amount) * (breakdown.overhead.ga_rate / 100)
    subtotal = direct_costs + overhead_amount + ga_amount
    profit = subtotal * (breakdown.overhead.profit_margin / 100)
    total_price = subtotal + profit

    # Store in database
    pricing_result = db.query(PricingResult).filter(
        PricingResult.rfp_id == rfp_id
    ).first()

    if not pricing_result:
        pricing_result = PricingResult(rfp_id=rfp_id)
        db.add(pricing_result)

    pricing_result.total_price = total_price
    pricing_result.base_cost = direct_costs
    pricing_result.margin_percentage = breakdown.overhead.profit_margin
    pricing_result.price_breakdown = {
        "labor": {"items": [item.dict() for item in breakdown.labor], "total": labor_total},
        "materials": {"items": [item.dict() for item in breakdown.materials], "total": materials_total},
        "subcontractors": {"items": [item.dict() for item in breakdown.subcontractors], "total": subcontractor_total},
        "overhead": overhead_amount,
        "ga": ga_amount,
        "profit": profit,
    }

    db.commit()
    return {"total_price": total_price, "id": pricing_result.id}

@router.get("/labor-rates")
async def get_default_labor_rates():
    """Get default labor rates by role."""
    return {
        "Project Manager": 150,
        "Senior Developer": 175,
        "Developer": 125,
        "Junior Developer": 85,
        "Designer": 135,
        "QA Engineer": 110,
        "DevOps Engineer": 160,
        "Technical Writer": 95,
        "Subject Matter Expert": 200,
        "Security Specialist": 185,
        "Data Analyst": 130,
        "Business Analyst": 140,
    }
```

**Verification**:
- [ ] Add/edit/delete labor line items
- [ ] Add/edit/delete material line items
- [ ] Add/edit/delete subcontractor quotes
- [ ] Overhead sliders update totals in real-time
- [ ] Total price calculates correctly
- [ ] Save persists to database
- [ ] Load restores saved data

---

### Task 3: Historical Pricing Intelligence Component

**File**: `frontend/src/components/pricing/MarketIntelligence.tsx`

**Purpose**: Provide insights from historical contract awards to inform pricing decisions.

**UI Design**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Market Intelligence                                    [Refresh Data]  │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─ Award Range Analysis ────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     Similar Contracts (NAICS: 541511, IT Services)               │   │
│ │     ┌─────────────────────────────────────────────────────────┐   │   │
│ │     │ Min        25th       Median     75th       Max         │   │   │
│ │     │ $45K       $125K      $280K      $450K      $1.2M       │   │   │
│ │     │   ●─────────[====●====]────────────●                    │   │   │
│ │     │            Your Price: $314K (55th percentile)          │   │   │
│ │     └─────────────────────────────────────────────────────────┘   │   │
│ │                                                                   │   │
│ │     📊 Based on 847 comparable contracts (2022-2024)             │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Pricing Trends ──────────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     Award Amounts Over Time (NAICS 541511)                       │   │
│ │     [Line chart showing trend]                                   │   │
│ │     ▲ 12% increase YoY | Market is trending upward               │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Agency Insights ─────────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     Department of Defense - Historical Awards                    │   │
│ │     ├─ Average Award: $342,500                                   │   │
│ │     ├─ Typical Duration: 3 years                                 │   │
│ │     ├─ Preferred Strategy: Best Value (78% of awards)            │   │
│ │     └─ Budget Cycle Peak: Q4 (Sept)                              │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Comparable Contracts ────────────────────────────────────────────┐   │
│ │ Contract          │ Agency      │ Award    │ Date   │ Relevance  │   │
│ │──────────────────────────────────────────────────────────────────│   │
│ │ IT Modernization  │ DoD         │ $425K    │ 2024   │ 94%        │   │
│ │ Cloud Migration   │ HHS         │ $380K    │ 2024   │ 91%        │   │
│ │ Cyber Security    │ DHS         │ $290K    │ 2023   │ 87%        │   │
│ │ [View All 15 Comparable Contracts]                                │   │
│ └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Backend Endpoints Needed**:

```python
# api/app/routes/pricing.py (additions)

from src.pricing.pricing_engine import PricingEngine
from src.rag.chroma_rag_engine import get_rag_engine
import pandas as pd
import numpy as np

@router.get("/{rfp_id}/market-intelligence")
async def get_market_intelligence(
    rfp_id: int,
    db: Session = Depends(get_db)
):
    """Get historical pricing intelligence for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = PricingEngine()

    # Get NAICS-based statistics
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None

    # Get category statistics
    category = engine._determine_category(rfp.title, rfp.description or "")
    category_stats = engine._get_category_statistics(category)

    # Get similar contracts from RAG
    rag_engine = get_rag_engine()
    similar_contracts = []
    if rag_engine and rfp.description:
        results = rag_engine.retrieve(
            f"{rfp.title} {rfp.description[:500]}",
            top_k=15
        )
        for doc in results:
            if doc.get('award_amount') and doc['award_amount'] > 0:
                similar_contracts.append({
                    "title": doc.get('title', 'Unknown'),
                    "agency": doc.get('agency', 'Unknown'),
                    "award_amount": doc['award_amount'],
                    "date": doc.get('posted_date', 'Unknown'),
                    "similarity": doc.get('similarity', 0),
                    "naics_code": doc.get('naics_code'),
                })

    # Calculate award range
    awards = [c['award_amount'] for c in similar_contracts if c['award_amount']]
    award_range = None
    if awards:
        award_range = {
            "min": min(awards),
            "p25": np.percentile(awards, 25),
            "median": np.median(awards),
            "p75": np.percentile(awards, 75),
            "max": max(awards),
            "count": len(awards),
        }

    # Get agency-specific insights
    agency_insights = None
    if rfp.agency:
        agency_data = engine._filter_by_agency(rfp.agency)
        if len(agency_data) > 0:
            agency_insights = {
                "average_award": agency_data['award_amount'].mean(),
                "contract_count": len(agency_data),
                "typical_duration": "2-3 years",  # Would need duration field
                "budget_peak": "Q4 (September)",
            }

    return {
        "naics_stats": naics_stats,
        "category_stats": category_stats,
        "award_range": award_range,
        "similar_contracts": similar_contracts[:10],
        "agency_insights": agency_insights,
        "analysis_date": datetime.now().isoformat(),
    }

@router.get("/trends/{naics_code}")
async def get_pricing_trends(naics_code: str):
    """Get pricing trend data for a NAICS code."""
    engine = PricingEngine()

    # Filter historical data by NAICS
    if engine.historical_data is not None:
        naics_data = engine.historical_data[
            engine.historical_data['naics_code'].astype(str).str.startswith(naics_code[:4])
        ]

        # Group by year and calculate statistics
        if 'posted_date' in naics_data.columns and len(naics_data) > 0:
            naics_data['year'] = pd.to_datetime(naics_data['posted_date']).dt.year
            trends = naics_data.groupby('year').agg({
                'award_amount': ['mean', 'median', 'count']
            }).reset_index()

            return {
                "naics_code": naics_code,
                "trends": trends.to_dict('records'),
                "yoy_change": calculate_yoy_change(trends),
            }

    return {"naics_code": naics_code, "trends": [], "yoy_change": None}
```

**Verification**:
- [ ] Award range visualization shows correct percentiles
- [ ] Your price indicator shows position in range
- [ ] Trend chart renders with historical data
- [ ] Agency insights load for known agencies
- [ ] Comparable contracts table populates
- [ ] Relevance scores are meaningful

---

### Task 4: AI-Powered Pricing Recommendations Component

**File**: `frontend/src/components/pricing/AIRecommendations.tsx`

**Purpose**: AI-generated optimal pricing suggestions with confidence scoring and scenario modeling.

**UI Design**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ AI Pricing Recommendations                         [Regenerate] [Help]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌─ Recommended Price ───────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     💡 OPTIMAL PRICE: $298,500                                   │   │
│ │                                                                   │   │
│ │     ┌─────────────────────────────────────────────────────────┐   │   │
│ │     │ Confidence: ████████████░░░ 82%                         │   │   │
│ │     └─────────────────────────────────────────────────────────┘   │   │
│ │                                                                   │   │
│ │     Why this price?                                              │   │
│ │     • Market median for similar contracts: $280K                 │   │
│ │     • Your win rate at this price point: 68%                     │   │
│ │     • Competition level: Moderate (3-5 bidders expected)         │   │
│ │     • Agency budget indicator: Within typical range              │   │
│ │                                                                   │   │
│ │     [Apply This Price]                                           │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Alternative Strategies ──────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│ │ │ AGGRESSIVE  │ │ COMPETITIVE │ │ VALUE-BASED │ │ COST-PLUS   │   │   │
│ │ │ $268,200    │ │ $298,500    │ │ $325,000    │ │ $342,800    │   │   │
│ │ │             │ │ ★ Optimal   │ │             │ │             │   │   │
│ │ │ Win: 78%    │ │ Win: 68%    │ │ Win: 55%    │ │ Win: 45%    │   │   │
│ │ │ Margin: 8%  │ │ Margin: 15% │ │ Margin: 22% │ │ Margin: 28% │   │   │
│ │ │ Risk: High  │ │ Risk: Low   │ │ Risk: Med   │ │ Risk: Low   │   │   │
│ │ │ [Select]    │ │ [Selected]  │ │ [Select]    │ │ [Select]    │   │   │
│ │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ "What If" Scenario Modeling ─────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     Target Win Probability: [========70%========]                │   │
│ │                                                                   │   │
│ │     At 70% win probability:                                      │   │
│ │     • Maximum price: $285,000                                    │   │
│ │     • Expected margin: 12%                                       │   │
│ │     • Expected profit: $34,200                                   │   │
│ │                                                                   │   │
│ │     [Win/Price Trade-off Chart]                                  │   │
│ │     Win%  │                                                      │   │
│ │     90%   │ ●                                                    │   │
│ │     80%   │   ●                                                  │   │
│ │     70%   │      ●  ← You are here                               │   │
│ │     60%   │          ●                                           │   │
│ │     50%   │              ●                                       │   │
│ │           └───────────────────────────────────                   │   │
│ │              $250K  $280K  $310K  $340K                          │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Risk Assessment ─────────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │ ⚠️ Below minimum margin threshold (10%)                          │   │
│ │ ⚠️ Limited historical data for this NAICS code                   │   │
│ │ ✅ Price within agency's typical award range                     │   │
│ │ ✅ Competitive with market median                                │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Backend Endpoint**:

```python
# api/app/routes/pricing.py (additions)

@router.post("/{rfp_id}/ai-recommendation")
async def get_ai_pricing_recommendation(
    rfp_id: int,
    current_price: Optional[float] = None,
    target_win_probability: float = 0.7,
    db: Session = Depends(get_db)
):
    """Get AI-powered pricing recommendation."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = PricingEngine()
    rag_engine = get_rag_engine()

    # Generate pricing for all strategies
    strategies = engine.compare_strategies(
        rfp_title=rfp.title,
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        requirements=None,
        compliance_analysis=None,
        rag_engine=rag_engine
    )

    # Calculate PTW for target probability
    ptw_result = engine.calculate_price_to_win(
        rfp_title=rfp.title,
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        target_win_probability=target_win_probability,
        rag_engine=rag_engine
    )

    # Determine optimal strategy
    optimal = None
    for name, result in strategies.items():
        if optimal is None or (
            result.confidence_score > optimal[1].confidence_score and
            result.margin_percentage >= 10  # Minimum acceptable margin
        ):
            optimal = (name, result)

    # Generate recommendation reasoning
    reasoning = []
    if optimal:
        naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
        if naics_stats:
            reasoning.append(f"Market median for similar contracts: ${naics_stats['median']:,.0f}")

        win_prob = engine.win_probability_model.predict(
            optimal[1].total_price,
            naics_stats['median'] if naics_stats else optimal[1].base_cost * 1.2,
            sensitivity=2.5
        )
        reasoning.append(f"Estimated win probability at this price: {win_prob*100:.0f}%")

        # Competition assessment
        competition_level = "Moderate" if win_prob > 0.5 else "High"
        reasoning.append(f"Competition level: {competition_level}")

    # Generate win/price curve data
    curve_data = []
    base_price = optimal[1].base_cost if optimal else 100000
    for prob in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
        price = engine.win_probability_model.solve_for_price(
            prob,
            naics_stats['median'] if naics_stats else base_price * 1.2
        )
        curve_data.append({"probability": prob, "price": price})

    return {
        "optimal": {
            "strategy": optimal[0] if optimal else "competitive",
            "price": optimal[1].total_price if optimal else None,
            "confidence": optimal[1].confidence_score if optimal else 0,
            "margin": optimal[1].margin_percentage if optimal else 0,
            "reasoning": reasoning,
        },
        "strategies": {
            name: {
                "price": result.total_price,
                "margin": result.margin_percentage,
                "confidence": result.confidence_score,
                "win_probability": engine.win_probability_model.predict(
                    result.total_price,
                    naics_stats['median'] if naics_stats else result.base_cost * 1.2
                ),
                "risk_level": "Low" if result.confidence_score > 0.7 else "Medium" if result.confidence_score > 0.5 else "High",
            }
            for name, result in strategies.items()
        },
        "price_to_win": {
            "target_probability": target_win_probability,
            "maximum_price": ptw_result.get('maximum_price'),
            "expected_margin": ptw_result.get('margin_at_target'),
        },
        "win_price_curve": curve_data,
        "risk_factors": optimal[1].risk_factors if optimal else [],
    }
```

**Verification**:
- [ ] Optimal price recommendation displayed with confidence
- [ ] All 4 strategies shown with metrics
- [ ] Win probability slider updates calculations
- [ ] Win/price curve renders correctly
- [ ] Risk factors displayed
- [ ] "Apply This Price" updates cost builder

---

### Task 5: Enhanced Price-to-Win Analysis Component

**File**: `frontend/src/components/pricing/PTWAnalysis.tsx`

**Purpose**: Deep competitor analysis and margin impact visualization.

**UI Design**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ Price-to-Win Analysis                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│ ┌─ Competitor Estimation ───────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │ Expected Competitors: 4-6 bidders                                │   │
│ │                                                                   │   │
│ │ Estimated Competitor Prices:                                     │   │
│ │ ┌──────────────────────────────────────────────────────────────┐ │   │
│ │ │                                                              │ │   │
│ │ │ Low Bidder (Aggressive):     $245,000  ▓▓▓▓▓▓▓▓░░░░░░░░░    │ │   │
│ │ │ Competitor Average:          $295,000  ▓▓▓▓▓▓▓▓▓▓▓░░░░░░    │ │   │
│ │ │ YOUR PRICE:                  $314,526  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░ ★  │ │   │
│ │ │ High Bidder (Conservative):  $385,000  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░    │ │   │
│ │ │                                                              │ │   │
│ │ └──────────────────────────────────────────────────────────────┘ │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Minimum Viable Price ────────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │     Absolute Floor (0% margin):     $233,000                     │   │
│ │     Minimum Viable (10% margin):    $256,300                     │   │
│ │     Recommended Floor (15% margin): $268,000                     │   │
│ │                                                                   │   │
│ │     ⚠️ Going below $256,300 would violate minimum margin policy  │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Margin Impact Analysis ──────────────────────────────────────────┐   │
│ │                                                                   │   │
│ │ Price Point      │ Margin  │ Profit   │ Win Prob │ Risk          │   │
│ │──────────────────────────────────────────────────────────────────│   │
│ │ $260,000         │ 11.6%   │ $30,200  │ 75%      │ ⚠️ Thin       │   │
│ │ $280,000         │ 16.8%   │ $47,100  │ 68%      │ ✅ Acceptable │   │
│ │ $300,000         │ 21.5%   │ $64,500  │ 60%      │ ✅ Good       │   │
│ │ $320,000         │ 25.8%   │ $82,600  │ 52%      │ ⚠️ Low win   │   │
│ │ $340,000         │ 29.8%   │ $101,300 │ 44%      │ ❌ High risk  │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌─ Risk Assessment at Current Price ────────────────────────────────┐   │
│ │                                                                   │   │
│ │ Overall Risk Score: 35/100 (Low-Medium)                          │   │
│ │                                                                   │   │
│ │ ✅ Price within market range                                     │   │
│ │ ✅ Margin above company minimum                                  │   │
│ │ ⚠️ 2 expected competitors may undercut significantly            │   │
│ │ ⚠️ Agency has history of LPTA selections                        │   │
│ │                                                                   │   │
│ │ Recommendation: Consider reducing by 5% to improve               │   │
│ │ competitiveness while maintaining acceptable margin.             │   │
│ │                                                                   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Backend Enhancement** - Extend existing PTW endpoint:

```python
# api/app/routes/pricing.py (additions)

@router.get("/{rfp_id}/ptw-analysis")
async def get_ptw_analysis(
    rfp_id: int,
    current_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """Get comprehensive Price-to-Win analysis."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    engine = PricingEngine()
    rag_engine = get_rag_engine()

    # Get market data
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
    market_median = naics_stats['median'] if naics_stats else 200000

    # Estimate competitor prices
    competitor_low = market_median * 0.82  # Aggressive bidder
    competitor_avg = market_median * 1.0
    competitor_high = market_median * 1.30  # Conservative bidder

    # Calculate minimum viable prices
    pricing_result = engine.generate_pricing(
        rfp_title=rfp.title,
        rfp_description=rfp.description or "",
        naics_code=rfp.naics_code,
        rag_engine=rag_engine
    )
    base_cost = pricing_result.base_cost

    minimum_viable = {
        "absolute_floor": base_cost,  # 0% margin
        "minimum_margin": base_cost * 1.10,  # 10% margin
        "recommended_floor": base_cost * 1.15,  # 15% margin
    }

    # Generate margin impact table
    margin_impact = []
    for price_point in [
        base_cost * 1.10,
        base_cost * 1.15,
        base_cost * 1.20,
        base_cost * 1.25,
        base_cost * 1.30,
    ]:
        margin = ((price_point - base_cost) / price_point) * 100
        profit = price_point - base_cost
        win_prob = engine.win_probability_model.predict(price_point, market_median)

        if margin < 12:
            risk = "Thin margin"
        elif win_prob < 0.5:
            risk = "Low win probability"
        elif win_prob > 0.7:
            risk = "Good"
        else:
            risk = "Acceptable"

        margin_impact.append({
            "price": price_point,
            "margin_percent": margin,
            "profit": profit,
            "win_probability": win_prob,
            "risk_assessment": risk,
        })

    # Calculate risk score
    risk_score = 0
    risk_factors = []

    if current_price:
        win_prob = engine.win_probability_model.predict(current_price, market_median)
        margin = ((current_price - base_cost) / current_price) * 100

        if win_prob < 0.5:
            risk_score += 30
            risk_factors.append("Low win probability at current price")

        if margin < 15:
            risk_score += 20
            risk_factors.append("Margin below recommended threshold")

        if current_price > competitor_high:
            risk_score += 25
            risk_factors.append("Price above expected competitor range")

    return {
        "competitor_estimates": {
            "expected_bidders": "4-6",
            "low_bidder": competitor_low,
            "average": competitor_avg,
            "high_bidder": competitor_high,
        },
        "minimum_viable": minimum_viable,
        "margin_impact_table": margin_impact,
        "risk_assessment": {
            "score": risk_score,
            "level": "Low" if risk_score < 30 else "Medium" if risk_score < 60 else "High",
            "factors": risk_factors,
        },
        "current_position": {
            "price": current_price,
            "vs_market": ((current_price or 0) - market_median) / market_median * 100 if current_price else None,
        }
    }
```

**Verification**:
- [ ] Competitor estimation bar chart renders
- [ ] Current price position indicator shows correctly
- [ ] Minimum viable prices calculated
- [ ] Margin impact table populates with correct values
- [ ] Risk assessment score and factors display
- [ ] Interactive price adjustment updates all metrics

---

### Task 6: Proposal Integration

**Files**:
- `api/app/routes/proposals.py` (new endpoints)
- `frontend/src/components/pricing/ProposalPricingIntegration.tsx`

**Purpose**: Seamlessly integrate pricing data into proposal generation, including auto-generated narratives and BOE documents.

**API Endpoints**:

```python
# api/app/routes/proposals.py (additions)

@router.post("/{rfp_id}/pricing-narrative")
async def generate_pricing_narrative(
    rfp_id: int,
    db: Session = Depends(get_db)
):
    """Generate pricing narrative for proposal inclusion."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp or not pricing:
        raise HTTPException(status_code=404, detail="RFP or pricing not found")

    # Build narrative from pricing data
    breakdown = pricing.price_breakdown or {}

    narrative = f"""
## Pricing Summary

{rfp.title}

### Total Proposed Price: ${pricing.total_price:,.2f}

Our pricing reflects a comprehensive understanding of the project requirements and
represents best value to the Government while ensuring successful project delivery.

### Cost Breakdown

**Direct Labor**: ${breakdown.get('labor', {}).get('total', 0):,.2f}
Our labor estimate is based on detailed analysis of each task requirement, utilizing
appropriate labor categories with rates that reflect current market conditions.

**Materials & Equipment**: ${breakdown.get('materials', {}).get('total', 0):,.2f}
Material costs are based on current vendor quotes and include appropriate contingency
for market fluctuations.

**Subcontractor Costs**: ${breakdown.get('subcontractors', {}).get('total', 0):,.2f}
Subcontractor pricing reflects competitive quotes from qualified vendors with proven
track records in their respective specialties.

**Overhead & G&A**: ${breakdown.get('overhead', 0) + breakdown.get('ga', 0):,.2f}
Indirect rates are current, audited rates applied consistently across all contracts.

**Profit**: ${breakdown.get('profit', 0):,.2f}
Our profit margin of {pricing.margin_percentage:.1f}% is reasonable and reflects
the risk profile of this requirement.

### Value Proposition

This pricing represents competitive value based on analysis of {pricing.confidence_score*100:.0f}%
confidence market data. We are committed to delivering exceptional results within this
budget framework.
"""

    return {"narrative": narrative, "generated_at": datetime.now().isoformat()}

@router.post("/{rfp_id}/basis-of-estimate")
async def generate_basis_of_estimate(
    rfp_id: int,
    db: Session = Depends(get_db)
):
    """Generate Basis of Estimate (BOE) document."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp or not pricing:
        raise HTTPException(status_code=404, detail="RFP or pricing not found")

    breakdown = pricing.price_breakdown or {}
    labor_items = breakdown.get('labor', {}).get('items', [])

    boe = {
        "document_title": f"Basis of Estimate - {rfp.title}",
        "rfp_number": rfp.rfp_number,
        "date_prepared": datetime.now().isoformat(),
        "sections": [
            {
                "title": "1. Introduction",
                "content": f"This Basis of Estimate (BOE) documents the methodology and assumptions used to develop the cost estimate for {rfp.title}."
            },
            {
                "title": "2. Labor Estimate Methodology",
                "content": "Labor hours were estimated using analogous estimation based on similar historical projects, supplemented by bottom-up estimates for unique requirements.",
                "details": [
                    {
                        "role": item.get('role'),
                        "hours": item.get('hours'),
                        "rate": item.get('rate_per_hour'),
                        "basis": f"Based on historical data from similar {rfp.naics_code or 'IT'} projects"
                    }
                    for item in labor_items
                ]
            },
            {
                "title": "3. Material/ODC Methodology",
                "content": "Material and Other Direct Costs are based on current vendor quotes and catalog pricing."
            },
            {
                "title": "4. Indirect Rates",
                "content": f"Overhead: {(breakdown.get('overhead', 0) / pricing.base_cost * 100) if pricing.base_cost else 0:.1f}%\nG&A: {(breakdown.get('ga', 0) / pricing.base_cost * 100) if pricing.base_cost else 0:.1f}%"
            },
            {
                "title": "5. Assumptions and Exclusions",
                "content": "Key assumptions: Government-furnished equipment as specified, standard work hours, no travel beyond PWS requirements."
            },
            {
                "title": "6. Risk Assessment",
                "content": f"Risk factors identified: {', '.join(pricing.risk_factors) if pricing.risk_factors else 'None significant'}"
            }
        ],
        "total_price": pricing.total_price,
        "confidence_level": f"{pricing.confidence_score*100:.0f}%"
    }

    return boe

@router.post("/{rfp_id}/link-pricing-to-sections")
async def link_pricing_to_proposal_sections(
    rfp_id: int,
    section_mapping: dict,  # {"technical_approach": ["labor_category_1"], "management": ["pm_hours"]}
    db: Session = Depends(get_db)
):
    """Link labor categories to proposal sections for traceability."""
    # Implementation to store mapping and generate cross-reference matrix
    pass
```

**Frontend Component**:

```typescript
// frontend/src/components/pricing/ProposalPricingIntegration.tsx

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/services/api';

interface ProposalPricingIntegrationProps {
  rfpId: string;
  onInsertNarrative: (narrative: string) => void;
}

export function ProposalPricingIntegration({
  rfpId,
  onInsertNarrative,
}: ProposalPricingIntegrationProps) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [boe, setBoe] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const generateNarrative = async () => {
    setIsLoading(true);
    try {
      const response = await api.generatePricingNarrative(rfpId);
      setNarrative(response.narrative);
    } finally {
      setIsLoading(false);
    }
  };

  const generateBOE = async () => {
    setIsLoading(true);
    try {
      const response = await api.generateBasisOfEstimate(rfpId);
      setBoe(response);
    } finally {
      setIsLoading(false);
    }
  };

  const downloadBOE = () => {
    if (boe) {
      const blob = new Blob([JSON.stringify(boe, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOE_${rfpId}.json`;
      a.click();
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proposal Integration</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="narrative">
          <TabsList>
            <TabsTrigger value="narrative">Pricing Narrative</TabsTrigger>
            <TabsTrigger value="boe">Basis of Estimate</TabsTrigger>
            <TabsTrigger value="mapping">Section Mapping</TabsTrigger>
          </TabsList>

          <TabsContent value="narrative" className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Generate a professional pricing narrative to include in your proposal.
            </p>
            <Button onClick={generateNarrative} disabled={isLoading}>
              Generate Narrative
            </Button>
            {narrative && (
              <div className="mt-4 space-y-4">
                <pre className="whitespace-pre-wrap bg-muted p-4 rounded text-sm">
                  {narrative}
                </pre>
                <Button onClick={() => onInsertNarrative(narrative)}>
                  Insert into Proposal
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="boe" className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Generate a Basis of Estimate (BOE) document for cost justification.
            </p>
            <Button onClick={generateBOE} disabled={isLoading}>
              Generate BOE
            </Button>
            {boe && (
              <div className="mt-4 space-y-4">
                <div className="bg-muted p-4 rounded">
                  <h4 className="font-semibold">{boe.document_title}</h4>
                  <p className="text-sm text-muted-foreground">
                    Total Price: ${boe.total_price?.toLocaleString()}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Confidence: {boe.confidence_level}
                  </p>
                </div>
                <Button onClick={downloadBOE}>Download BOE</Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="mapping">
            <p className="text-sm text-muted-foreground">
              Link labor categories to proposal sections for traceability.
            </p>
            {/* Section mapping UI */}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
```

**Verification**:
- [ ] Pricing narrative generates correctly
- [ ] Insert into proposal works
- [ ] BOE document generates with all sections
- [ ] BOE download works
- [ ] Section mapping UI allows labor-to-section linking

---

### Task 7: Backend ML Enhancements

**File**: `src/pricing/pricing_ml.py` (new)

**Purpose**: Add machine learning models for price prediction and optimization.

**Implementation**:

```python
# src/pricing/pricing_ml.py

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pickle
from pathlib import Path

@dataclass
class PricePrediction:
    predicted_price: float
    confidence_interval: Tuple[float, float]  # (lower, upper)
    feature_importance: Dict[str, float]
    model_confidence: float
    similar_awards: List[Dict]

class PricingMLModel:
    """Machine learning model for price prediction and optimization."""

    def __init__(self, model_path: Optional[Path] = None):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.model_path = model_path or Path("models/pricing_model.pkl")

        # Try to load existing model
        if self.model_path.exists():
            self._load_model()

    def train(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        """Train the pricing model on historical award data."""

        # Prepare features
        features = self._prepare_features(historical_data)
        target = historical_data['award_amount'].values

        # Remove rows with missing target
        valid_mask = ~np.isnan(target) & (target > 0)
        features = features[valid_mask]
        target = target[valid_mask]

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=0.2, random_state=42
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train ensemble model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        # Save model
        self._save_model()

        return {
            "train_r2": train_score,
            "test_r2": test_score,
            "samples_trained": len(X_train),
            "samples_tested": len(X_test),
        }

    def predict(
        self,
        naics_code: str,
        agency: str,
        description_length: int,
        requirement_count: int,
        contract_type: str = "FFP",
        set_aside: Optional[str] = None,
    ) -> PricePrediction:
        """Predict optimal price for an RFP."""

        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Prepare input features
        features = self._encode_features({
            'naics_code': naics_code,
            'agency': agency,
            'description_length': description_length,
            'requirement_count': requirement_count,
            'contract_type': contract_type,
            'set_aside': set_aside or 'None',
        })

        # Scale and predict
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        prediction = self.model.predict(features_scaled)[0]

        # Calculate confidence interval using quantile regression or bootstrap
        # For simplicity, using standard deviation of tree predictions
        tree_predictions = np.array([
            tree.predict(features_scaled)[0]
            for tree in self.model.estimators_[:, 0]
        ])
        std = tree_predictions.std()
        ci_lower = prediction - 1.96 * std
        ci_upper = prediction + 1.96 * std

        # Get feature importance
        importance = dict(zip(
            self.feature_names,
            self.model.feature_importances_
        ))

        return PricePrediction(
            predicted_price=prediction,
            confidence_interval=(ci_lower, ci_upper),
            feature_importance=importance,
            model_confidence=min(1.0, 1.0 - (std / prediction) if prediction > 0 else 0),
            similar_awards=[]  # Would be populated from historical data
        )

    def optimize_price(
        self,
        base_cost: float,
        min_margin: float = 0.10,
        max_margin: float = 0.35,
        target_win_prob: float = 0.7,
        market_median: float = None,
    ) -> Dict[str, float]:
        """Find optimal price balancing margin and win probability."""

        from src.pricing.win_probability import WinProbabilityModel
        win_model = WinProbabilityModel()

        best_score = -1
        best_price = base_cost * (1 + min_margin)

        # Grid search over possible prices
        for margin in np.arange(min_margin, max_margin + 0.01, 0.01):
            price = base_cost * (1 + margin)

            if market_median:
                win_prob = win_model.predict(price, market_median)
            else:
                win_prob = 0.5  # Default if no market data

            # Score: weighted combination of margin and win probability
            # Prioritize win probability until target is met
            if win_prob >= target_win_prob:
                score = margin * 0.6 + win_prob * 0.4
            else:
                score = win_prob  # Below target, maximize win prob

            if score > best_score:
                best_score = score
                best_price = price
                best_margin = margin
                best_win_prob = win_prob

        return {
            "optimal_price": best_price,
            "margin": best_margin,
            "win_probability": best_win_prob,
            "expected_profit": best_price - base_cost,
            "optimization_score": best_score,
        }

    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from historical data."""

        feature_columns = [
            'naics_code', 'agency', 'description_length',
            'requirement_count', 'contract_type', 'set_aside'
        ]

        # Create derived features
        data = data.copy()
        if 'description' in data.columns:
            data['description_length'] = data['description'].fillna('').str.len()
        if 'description_length' not in data.columns:
            data['description_length'] = 500  # Default

        if 'requirement_count' not in data.columns:
            data['requirement_count'] = 10  # Default

        if 'contract_type' not in data.columns:
            data['contract_type'] = 'FFP'

        if 'set_aside' not in data.columns:
            data['set_aside'] = 'None'

        # Encode categorical features
        features = []
        for col in feature_columns:
            if col in ['naics_code', 'agency', 'contract_type', 'set_aside']:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    # Fit with unknown handling
                    values = data[col].fillna('Unknown').astype(str)
                    self.label_encoders[col].fit(list(values.unique()) + ['Unknown'])

                encoded = self.label_encoders[col].transform(
                    data[col].fillna('Unknown').astype(str)
                )
                features.append(encoded)
            else:
                features.append(data[col].fillna(0).values)

        self.feature_names = feature_columns
        return np.column_stack(features)

    def _encode_features(self, data: Dict) -> np.ndarray:
        """Encode a single data point for prediction."""
        features = []
        for col in self.feature_names:
            if col in self.label_encoders:
                try:
                    encoded = self.label_encoders[col].transform([str(data.get(col, 'Unknown'))])[0]
                except ValueError:
                    encoded = self.label_encoders[col].transform(['Unknown'])[0]
                features.append(encoded)
            else:
                features.append(data.get(col, 0))
        return np.array(features)

    def _save_model(self):
        """Save model to disk."""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'label_encoders': self.label_encoders,
                'feature_names': self.feature_names,
            }, f)

    def _load_model(self):
        """Load model from disk."""
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.label_encoders = data['label_encoders']
            self.feature_names = data['feature_names']
```

**API Integration**:

```python
# api/app/routes/pricing.py (additions)

from src.pricing.pricing_ml import PricingMLModel

ml_model = PricingMLModel()

@router.post("/train-model")
async def train_pricing_model():
    """Train/retrain the ML pricing model on historical data."""
    from src.pricing.pricing_engine import PricingEngine

    engine = PricingEngine()
    if engine.historical_data is None:
        raise HTTPException(status_code=500, detail="No historical data available")

    results = ml_model.train(engine.historical_data)
    return {"status": "trained", "metrics": results}

@router.post("/{rfp_id}/ml-prediction")
async def get_ml_price_prediction(
    rfp_id: int,
    db: Session = Depends(get_db)
):
    """Get ML-based price prediction for an RFP."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    prediction = ml_model.predict(
        naics_code=rfp.naics_code or "541511",
        agency=rfp.agency or "Unknown",
        description_length=len(rfp.description or ""),
        requirement_count=10,  # Would come from compliance analysis
    )

    return {
        "predicted_price": prediction.predicted_price,
        "confidence_interval": {
            "lower": prediction.confidence_interval[0],
            "upper": prediction.confidence_interval[1],
        },
        "model_confidence": prediction.model_confidence,
        "feature_importance": prediction.feature_importance,
    }

@router.post("/{rfp_id}/optimize-price")
async def optimize_price(
    rfp_id: int,
    min_margin: float = 0.10,
    max_margin: float = 0.35,
    target_win_prob: float = 0.7,
    db: Session = Depends(get_db)
):
    """Find optimal price balancing margin and win probability."""
    rfp = db.query(RFPOpportunity).filter(RFPOpportunity.id == rfp_id).first()
    pricing = db.query(PricingResult).filter(PricingResult.rfp_id == rfp_id).first()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    base_cost = pricing.base_cost if pricing else 100000

    # Get market median
    engine = PricingEngine()
    naics_stats = engine._get_naics_statistics(rfp.naics_code) if rfp.naics_code else None
    market_median = naics_stats['median'] if naics_stats else base_cost * 1.2

    result = ml_model.optimize_price(
        base_cost=base_cost,
        min_margin=min_margin,
        max_margin=max_margin,
        target_win_prob=target_win_prob,
        market_median=market_median,
    )

    return result
```

**Verification**:
- [ ] Model trains on historical data
- [ ] Predictions return with confidence intervals
- [ ] Feature importance is meaningful
- [ ] Price optimization finds reasonable values
- [ ] Model persists across restarts

---

### Task 8: Add Route to App Router and Navigation

**Files**:
- `frontend/src/App.tsx` - Add route
- `frontend/src/components/layout/Sidebar.tsx` - Add navigation

**Implementation**:

```typescript
// In App.tsx, add route
<Route path="/pricing/:rfpId" element={<PricingWorkspace />} />

// In Sidebar.tsx or navigation, add link
<NavLink to={`/pricing/${rfpId}`}>
  <DollarSign className="h-4 w-4" />
  Pricing Workspace
</NavLink>
```

**Verification**:
- [ ] Route accessible from browser
- [ ] Navigation link appears in sidebar
- [ ] Deep linking works (direct URL access)

---

## Database Schema Changes

### New Tables/Columns Required

```sql
-- Add columns to pricing_results table if not exists
ALTER TABLE pricing_results ADD COLUMN IF NOT EXISTS
    cost_breakdown_detail JSONB;  -- Detailed line items

-- Optional: Pricing audit trail table
CREATE TABLE IF NOT EXISTS pricing_history (
    id SERIAL PRIMARY KEY,
    rfp_id INTEGER REFERENCES rfp_opportunities(id),
    pricing_snapshot JSONB,
    changed_by VARCHAR(255),
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## File Creation Checklist

### New Files to Create

| File | Type | Purpose |
|------|------|---------|
| `frontend/src/pages/PricingWorkspace.tsx` | Page | Main pricing workspace |
| `frontend/src/components/pricing/CostBuilder.tsx` | Component | Line-item cost builder |
| `frontend/src/components/pricing/MarketIntelligence.tsx` | Component | Historical insights |
| `frontend/src/components/pricing/AIRecommendations.tsx` | Component | AI pricing suggestions |
| `frontend/src/components/pricing/PTWAnalysis.tsx` | Component | Price-to-Win analysis |
| `frontend/src/components/pricing/ScenarioModeler.tsx` | Component | Scenario modeling (enhance existing) |
| `frontend/src/components/pricing/PricingSummaryCards.tsx` | Component | KPI summary cards |
| `frontend/src/components/pricing/SimilarContractsSidebar.tsx` | Component | Similar contracts panel |
| `frontend/src/components/pricing/ProposalPricingIntegration.tsx` | Component | Proposal integration |
| `api/app/routes/pricing.py` | API | Dedicated pricing endpoints |
| `src/pricing/pricing_ml.py` | Backend | ML pricing model |
| `frontend/src/types/pricing.ts` | Types | TypeScript interfaces |

### Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | Add pricing workspace route |
| `frontend/src/components/layout/Sidebar.tsx` | Add pricing nav link |
| `frontend/src/services/api.ts` | Add pricing API methods |
| `api/app/main.py` | Include pricing router |
| `api/app/routes/rfps.py` | May need minor adjustments |

---

## Dependencies

### Frontend
- No new dependencies required (uses existing shadcn/ui, recharts)

### Backend
- `scikit-learn` - For ML models (may already be in requirements)
- Add to `requirements.txt` if not present:
  ```
  scikit-learn>=1.3.0
  ```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_pricing_ml.py

def test_pricing_model_training():
    """Test that ML model trains successfully."""
    model = PricingMLModel()
    # Load test data
    # Train model
    # Assert R² > 0.5

def test_price_prediction():
    """Test price prediction returns valid results."""
    model = PricingMLModel()
    prediction = model.predict(
        naics_code="541511",
        agency="DoD",
        description_length=1000,
        requirement_count=15,
    )
    assert prediction.predicted_price > 0
    assert prediction.confidence_interval[0] < prediction.predicted_price
    assert prediction.confidence_interval[1] > prediction.predicted_price

def test_price_optimization():
    """Test price optimization finds valid price."""
    model = PricingMLModel()
    result = model.optimize_price(
        base_cost=100000,
        min_margin=0.10,
        max_margin=0.30,
        target_win_prob=0.7,
        market_median=150000,
    )
    assert result['optimal_price'] > 100000
    assert 0.10 <= result['margin'] <= 0.30
```

### Integration Tests

```python
# tests/test_pricing_api.py

def test_cost_breakdown_save():
    """Test saving cost breakdown via API."""
    response = client.post(f"/api/v1/pricing/{rfp_id}/cost-breakdown", json={
        "labor": [{"role": "Developer", "hours": 100, "rate_per_hour": 125}],
        "materials": [],
        "subcontractors": [],
        "overhead": {"overhead_rate": 15, "ga_rate": 8, "profit_margin": 12},
    })
    assert response.status_code == 200
    assert response.json()['total_price'] > 0

def test_market_intelligence():
    """Test market intelligence endpoint."""
    response = client.get(f"/api/v1/pricing/{rfp_id}/market-intelligence")
    assert response.status_code == 200
    assert 'award_range' in response.json()

def test_ai_recommendation():
    """Test AI recommendation endpoint."""
    response = client.post(f"/api/v1/pricing/{rfp_id}/ai-recommendation")
    assert response.status_code == 200
    assert 'optimal' in response.json()
    assert 'strategies' in response.json()
```

### Frontend Tests

```typescript
// frontend/src/components/pricing/__tests__/CostBuilder.test.tsx

describe('CostBuilder', () => {
  it('calculates total price correctly', () => {
    render(<CostBuilder rfpId="1" onUpdate={jest.fn()} />);
    // Add labor item
    // Verify total updates
  });

  it('handles overhead rate changes', () => {
    // Test slider updates
  });
});
```

---

## Execution Order

1. **Task 8** - Add route and navigation (foundation)
2. **Task 1** - Create PricingWorkspace page (main container)
3. **Task 2** - CostBuilder component (core functionality)
4. **Task 3** - MarketIntelligence component (data display)
5. **Task 4** - AIRecommendations component (AI integration)
6. **Task 5** - PTWAnalysis component (analysis)
7. **Task 7** - Backend ML enhancements (AI support)
8. **Task 6** - Proposal Integration (final integration)

---

## Estimated Complexity

| Task | Complexity | Effort |
|------|------------|--------|
| Task 1: Pricing Workspace | Medium | Frontend page setup |
| Task 2: Cost Builder | High | Complex state management |
| Task 3: Market Intelligence | Medium | Data visualization |
| Task 4: AI Recommendations | High | ML integration |
| Task 5: PTW Analysis | Medium | Algorithm implementation |
| Task 6: Proposal Integration | Medium | Cross-feature integration |
| Task 7: Backend ML | High | ML model development |
| Task 8: Routes/Navigation | Low | Simple configuration |

---

## Success Criteria

1. **User can build pricing from scratch** using line items, labor rates, and overhead
2. **Historical market data informs pricing decisions** with visualizations
3. **AI provides actionable pricing recommendations** with confidence scores
4. **Price-to-Win analysis shows competitive positioning** and risk assessment
5. **Pricing integrates seamlessly into proposals** with narratives and BOE
6. **ML model improves predictions over time** with training on outcomes

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ML model accuracy | Recommendations may be off | Show confidence intervals, allow manual override |
| Historical data quality | Insights may be misleading | Validate data, show sample sizes |
| Performance with large datasets | UI may lag | Implement pagination, caching |
| Integration complexity | May break existing features | Thorough testing, feature flags |

---

## Post-Implementation

After completion:
1. Train ML model on full historical dataset
2. Monitor recommendation accuracy
3. Gather user feedback on workflow
4. Consider adding actual vs estimated tracking for future model improvement
