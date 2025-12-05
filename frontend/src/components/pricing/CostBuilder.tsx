import { useState, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Edit2, Save, DollarSign } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type {
  CostBreakdown,
  LaborLineItem,
  MaterialLineItem,
  SubcontractorQuote,
} from '@/types/pricing';
import { DEFAULT_LABOR_RATES } from '@/types/pricing';

interface CostBuilderProps {
  rfpId?: string;
  initialData?: CostBreakdown | null;
  onUpdate: (data: CostBreakdown) => void;
}

const generateId = () => crypto.randomUUID();

export function CostBuilder({ initialData, onUpdate }: CostBuilderProps) {
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
  const totals = useMemo(() => {
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

    return {
      laborTotal,
      materialsTotal,
      subcontractorTotal,
      directCosts,
      overheadAmount,
      gaAmount,
      subtotalBeforeProfit,
      profitAmount,
      totalPrice,
    };
  }, [breakdown]);

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
      id: generateId(),
      role: 'Developer',
      hours: 40,
      ratePerHour: DEFAULT_LABOR_RATES['Developer'],
    };
    updateBreakdown({ labor: [...breakdown.labor, newItem] });
    setEditingId(newItem.id);
  };

  const updateLaborItem = (id: string, updates: Partial<LaborLineItem>) => {
    updateBreakdown({
      labor: breakdown.labor.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    });
  };

  const deleteLaborItem = (id: string) => {
    updateBreakdown({
      labor: breakdown.labor.filter((item) => item.id !== id),
    });
  };

  const addMaterialItem = () => {
    const newItem: MaterialLineItem = {
      id: generateId(),
      description: 'New Item',
      quantity: 1,
      unitPrice: 0,
      unit: 'each',
    };
    updateBreakdown({ materials: [...breakdown.materials, newItem] });
    setEditingId(newItem.id);
  };

  const updateMaterialItem = (id: string, updates: Partial<MaterialLineItem>) => {
    updateBreakdown({
      materials: breakdown.materials.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    });
  };

  const deleteMaterialItem = (id: string) => {
    updateBreakdown({
      materials: breakdown.materials.filter((item) => item.id !== id),
    });
  };

  const addSubcontractor = () => {
    const newItem: SubcontractorQuote = {
      id: generateId(),
      vendor: 'New Vendor',
      scope: 'TBD',
      quoteAmount: 0,
    };
    updateBreakdown({ subcontractors: [...breakdown.subcontractors, newItem] });
    setEditingId(newItem.id);
  };

  const updateSubcontractor = (id: string, updates: Partial<SubcontractorQuote>) => {
    updateBreakdown({
      subcontractors: breakdown.subcontractors.map((item) =>
        item.id === id ? { ...item, ...updates } : item
      ),
    });
  };

  const deleteSubcontractor = (id: string) => {
    updateBreakdown({
      subcontractors: breakdown.subcontractors.filter((item) => item.id !== id),
    });
  };

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <div className="space-y-6">
      {/* Labor Costs Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg">Labor Costs</CardTitle>
          <Button size="sm" onClick={addLaborItem}>
            <Plus className="h-4 w-4 mr-1" /> Add Role
          </Button>
        </CardHeader>
        <CardContent>
          {breakdown.labor.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">Role</TableHead>
                  <TableHead className="text-right w-[100px]">Hours</TableHead>
                  <TableHead className="text-right w-[120px]">Rate/Hr</TableHead>
                  <TableHead className="text-right w-[120px]">Total</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breakdown.labor.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {editingId === item.id ? (
                        <Select
                          value={item.role}
                          onValueChange={(role) => {
                            updateLaborItem(item.id, {
                              role,
                              ratePerHour: DEFAULT_LABOR_RATES[role] || item.ratePerHour,
                            });
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.keys(DEFAULT_LABOR_RATES).map((role) => (
                              <SelectItem key={role} value={role}>
                                {role}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
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
                            updateLaborItem(item.id, { hours: Number(e.target.value) })
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
                            updateLaborItem(item.id, { ratePerHour: Number(e.target.value) })
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
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(null)}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(item.id)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => deleteLaborItem(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No labor items. Click "Add Role" to begin.
            </p>
          )}
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Labor Subtotal: {formatCurrency(totals.laborTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Materials & Equipment Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg">Materials & Equipment</CardTitle>
          <Button size="sm" onClick={addMaterialItem}>
            <Plus className="h-4 w-4 mr-1" /> Add Item
          </Button>
        </CardHeader>
        <CardContent>
          {breakdown.materials.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[250px]">Description</TableHead>
                  <TableHead className="text-right w-[80px]">Qty</TableHead>
                  <TableHead className="w-[100px]">Unit</TableHead>
                  <TableHead className="text-right w-[120px]">Unit Price</TableHead>
                  <TableHead className="text-right w-[120px]">Total</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breakdown.materials.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {editingId === item.id ? (
                        <Input
                          value={item.description}
                          onChange={(e) =>
                            updateMaterialItem(item.id, { description: e.target.value })
                          }
                        />
                      ) : (
                        item.description
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {editingId === item.id ? (
                        <Input
                          type="number"
                          className="w-16 text-right"
                          value={item.quantity}
                          onChange={(e) =>
                            updateMaterialItem(item.id, { quantity: Number(e.target.value) })
                          }
                        />
                      ) : (
                        item.quantity
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === item.id ? (
                        <Select
                          value={item.unit}
                          onValueChange={(unit: 'each' | 'monthly' | 'annual') =>
                            updateMaterialItem(item.id, { unit })
                          }
                        >
                          <SelectTrigger className="w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="each">Each</SelectItem>
                            <SelectItem value="monthly">Monthly</SelectItem>
                            <SelectItem value="annual">Annual</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        item.unit
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {editingId === item.id ? (
                        <Input
                          type="number"
                          className="w-24 text-right"
                          value={item.unitPrice}
                          onChange={(e) =>
                            updateMaterialItem(item.id, { unitPrice: Number(e.target.value) })
                          }
                        />
                      ) : (
                        formatCurrency(item.unitPrice)
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(item.quantity * item.unitPrice)}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {editingId === item.id ? (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(null)}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(item.id)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => deleteMaterialItem(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No materials. Click "Add Item" to begin.
            </p>
          )}
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Materials Subtotal: {formatCurrency(totals.materialsTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Subcontractors Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-4">
          <CardTitle className="text-lg">Subcontractor Quotes</CardTitle>
          <Button size="sm" onClick={addSubcontractor}>
            <Plus className="h-4 w-4 mr-1" /> Add Subcontractor
          </Button>
        </CardHeader>
        <CardContent>
          {breakdown.subcontractors.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[200px]">Vendor</TableHead>
                  <TableHead className="w-[300px]">Scope</TableHead>
                  <TableHead className="text-right w-[150px]">Quote Amount</TableHead>
                  <TableHead className="w-[80px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breakdown.subcontractors.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {editingId === item.id ? (
                        <Input
                          value={item.vendor}
                          onChange={(e) =>
                            updateSubcontractor(item.id, { vendor: e.target.value })
                          }
                        />
                      ) : (
                        item.vendor
                      )}
                    </TableCell>
                    <TableCell>
                      {editingId === item.id ? (
                        <Input
                          value={item.scope}
                          onChange={(e) =>
                            updateSubcontractor(item.id, { scope: e.target.value })
                          }
                        />
                      ) : (
                        item.scope
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {editingId === item.id ? (
                        <Input
                          type="number"
                          className="w-32 text-right"
                          value={item.quoteAmount}
                          onChange={(e) =>
                            updateSubcontractor(item.id, { quoteAmount: Number(e.target.value) })
                          }
                        />
                      ) : (
                        formatCurrency(item.quoteAmount)
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {editingId === item.id ? (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(null)}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                        ) : (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => setEditingId(item.id)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => deleteSubcontractor(item.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No subcontractors. Click "Add Subcontractor" to begin.
            </p>
          )}
          <div className="flex justify-end mt-4 text-lg font-semibold">
            Subcontractor Subtotal: {formatCurrency(totals.subcontractorTotal)}
          </div>
        </CardContent>
      </Card>

      {/* Overhead & Profit Section */}
      <Card>
        <CardHeader className="py-4">
          <CardTitle className="text-lg">Overhead & Profit</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-medium">Direct Costs</span>
              <span className="text-lg font-semibold">
                {formatCurrency(totals.directCosts)}
              </span>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Overhead Rate</span>
              <span className="font-medium">{breakdown.overhead.overheadRate}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.overheadRate]}
              onValueChange={([v]) =>
                updateBreakdown({
                  overhead: { ...breakdown.overhead, overheadRate: v },
                })
              }
              max={30}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(totals.overheadAmount)}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span>G&A Rate</span>
              <span className="font-medium">{breakdown.overhead.gaRate}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.gaRate]}
              onValueChange={([v]) =>
                updateBreakdown({
                  overhead: { ...breakdown.overhead, gaRate: v },
                })
              }
              max={20}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(totals.gaAmount)}
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Profit Margin</span>
              <span className="font-medium">{breakdown.overhead.profitMargin}%</span>
            </div>
            <Slider
              value={[breakdown.overhead.profitMargin]}
              onValueChange={([v]) =>
                updateBreakdown({
                  overhead: { ...breakdown.overhead, profitMargin: v },
                })
              }
              max={25}
              step={0.5}
            />
            <div className="text-right text-muted-foreground">
              {formatCurrency(totals.profitAmount)}
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="flex justify-between items-center text-xl font-bold">
              <span className="flex items-center gap-2">
                <DollarSign className="h-6 w-6 text-green-600" />
                TOTAL BID PRICE
              </span>
              <span className="text-green-600">{formatCurrency(totals.totalPrice)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
