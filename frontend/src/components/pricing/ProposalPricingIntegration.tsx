import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  FileText,
  Download,
  Copy,
  CheckCircle2,
  RefreshCw,
  Link2,
} from 'lucide-react';
import { api } from '@/services/api';
import { toast } from 'sonner';
import type { PricingNarrative, BasisOfEstimate } from '@/types/pricing';

interface ProposalPricingIntegrationProps {
  rfpId: string;
  onInsertNarrative?: (narrative: string) => void;
}

export function ProposalPricingIntegration({
  rfpId,
  onInsertNarrative,
}: ProposalPricingIntegrationProps) {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [boe, setBoe] = useState<BasisOfEstimate | null>(null);
  const [copied, setCopied] = useState(false);

  const narrativeMutation = useMutation({
    mutationFn: () => api.generatePricingNarrative(rfpId),
    onSuccess: (data: PricingNarrative) => {
      setNarrative(data.narrative);
      toast.success('Pricing narrative generated');
    },
    onError: () => {
      toast.error('Failed to generate narrative');
    },
  });

  const boeMutation = useMutation({
    mutationFn: () => api.generateBasisOfEstimate(rfpId),
    onSuccess: (data: BasisOfEstimate) => {
      setBoe(data);
      toast.success('Basis of Estimate generated');
    },
    onError: () => {
      toast.error('Failed to generate BOE');
    },
  });

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadBOE = () => {
    if (!boe) return;

    const content = formatBOEAsMarkdown(boe);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `BOE_${rfpId}_${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatBOEAsMarkdown = (boe: BasisOfEstimate): string => {
    let md = `# ${boe.document_title}\n\n`;
    md += `**RFP Number:** ${boe.rfp_number || 'N/A'}\n`;
    md += `**Date Prepared:** ${new Date(boe.date_prepared).toLocaleDateString()}\n`;
    md += `**Total Price:** $${boe.total_price?.toLocaleString()}\n`;
    md += `**Confidence Level:** ${boe.confidence_level}\n\n`;
    md += `---\n\n`;

    for (const section of boe.sections) {
      md += `## ${section.title}\n\n`;
      md += `${section.content}\n\n`;

      if (section.details && section.details.length > 0) {
        md += `| Role | Hours | Rate | Basis |\n`;
        md += `|------|-------|------|-------|\n`;
        for (const detail of section.details) {
          md += `| ${detail.role || 'N/A'} | ${detail.hours || 'N/A'} | $${detail.rate || 'N/A'}/hr | ${detail.basis || 'N/A'} |\n`;
        }
        md += `\n`;
      }
    }

    return md;
  };

  const formatCurrency = (amount: number | undefined) => {
    if (!amount) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <Card>
      <CardHeader className="py-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Link2 className="h-5 w-5" />
          Proposal Integration
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="narrative">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="narrative">Pricing Narrative</TabsTrigger>
            <TabsTrigger value="boe">Basis of Estimate</TabsTrigger>
            <TabsTrigger value="mapping">Section Mapping</TabsTrigger>
          </TabsList>

          <TabsContent value="narrative" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              Generate a professional pricing narrative to include in your proposal's
              pricing volume.
            </p>

            <Button
              onClick={() => narrativeMutation.mutate()}
              disabled={narrativeMutation.isPending}
            >
              {narrativeMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Narrative
                </>
              )}
            </Button>

            {narrative && (
              <div className="space-y-4">
                <div className="relative">
                  <Textarea
                    value={narrative}
                    onChange={(e) => setNarrative(e.target.value)}
                    rows={15}
                    className="font-mono text-sm"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(narrative)}
                  >
                    {copied ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>

                <div className="flex gap-2">
                  {onInsertNarrative && (
                    <Button onClick={() => onInsertNarrative(narrative)}>
                      <FileText className="h-4 w-4 mr-2" />
                      Insert into Proposal
                    </Button>
                  )}
                  <Button variant="outline" onClick={() => copyToClipboard(narrative)}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy to Clipboard
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="boe" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              Generate a Basis of Estimate (BOE) document for cost justification and
              audit support.
            </p>

            <Button
              onClick={() => boeMutation.mutate()}
              disabled={boeMutation.isPending}
            >
              {boeMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="h-4 w-4 mr-2" />
                  Generate BOE
                </>
              )}
            </Button>

            {boe && (
              <div className="space-y-4">
                <Card className="bg-muted/50">
                  <CardContent className="pt-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold">{boe.document_title}</h4>
                        <p className="text-sm text-muted-foreground">
                          Prepared: {new Date(boe.date_prepared).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">
                          {formatCurrency(boe.total_price)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Confidence: {boe.confidence_level}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {boe.sections.slice(0, 3).map((section, index) => (
                        <div key={index} className="border-l-2 border-blue-500 pl-3">
                          <h5 className="font-medium text-sm">{section.title}</h5>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {section.content}
                          </p>
                        </div>
                      ))}
                      {boe.sections.length > 3 && (
                        <p className="text-xs text-muted-foreground">
                          + {boe.sections.length - 3} more sections
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Button onClick={downloadBOE}>
                  <Download className="h-4 w-4 mr-2" />
                  Download BOE (Markdown)
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="mapping" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              Link labor categories and cost elements to specific proposal sections
              for traceability.
            </p>

            <div className="bg-muted/50 rounded-lg p-6 text-center">
              <Link2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h4 className="font-medium mb-2">Section Mapping</h4>
              <p className="text-sm text-muted-foreground mb-4">
                Create links between labor categories and proposal sections to ensure
                pricing aligns with technical approach.
              </p>
              <Button variant="outline" disabled>
                Coming Soon
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
