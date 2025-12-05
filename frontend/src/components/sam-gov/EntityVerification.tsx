import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, Building2, Calendar, AlertCircle } from 'lucide-react';
import { api } from '@/services/api';

export function EntityVerification() {
  const [uei, setUei] = useState('');
  const [cageCode, setCageCode] = useState('');
  const [legalName, setLegalName] = useState('');

  const verifyMutation = useMutation({
    mutationFn: () => api.verifySamGovEntity({
      uei: uei || undefined,
      cage_code: cageCode || undefined,
      legal_name: legalName || undefined,
    }),
  });

  const handleVerify = () => {
    if (uei || cageCode || legalName) {
      verifyMutation.mutate();
    }
  };

  const result = verifyMutation.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          SAM.gov Entity Verification
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="uei">UEI (Unique Entity ID)</Label>
            <Input
              id="uei"
              placeholder="12 characters"
              value={uei}
              onChange={(e) => setUei(e.target.value.toUpperCase())}
              maxLength={12}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cage">CAGE Code</Label>
            <Input
              id="cage"
              placeholder="5 characters"
              value={cageCode}
              onChange={(e) => setCageCode(e.target.value.toUpperCase())}
              maxLength={5}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Legal Business Name</Label>
            <Input
              id="name"
              placeholder="Company name"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
            />
          </div>
        </div>

        <Button
          onClick={handleVerify}
          disabled={verifyMutation.isPending || (!uei && !cageCode && !legalName)}
        >
          {verifyMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Verify Entity
        </Button>

        {result && (
          <div className={`p-4 rounded-lg ${result.is_registered ? 'bg-green-50' : 'bg-red-50'}`}>
            <div className="flex items-center gap-2 mb-3">
              {result.is_registered ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600" />
              )}
              <span className={`font-medium ${result.is_registered ? 'text-green-800' : 'text-red-800'}`}>
                {result.is_registered ? 'Entity Verified' : 'Entity Not Found'}
              </span>
              {result.registration_status && (
                <Badge variant={result.registration_status === 'Active' ? 'default' : 'destructive'}>
                  {result.registration_status}
                </Badge>
              )}
            </div>

            {result.is_registered && (
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-muted-foreground">UEI:</span> {result.uei}</div>
                <div><span className="text-muted-foreground">CAGE:</span> {result.cage_code || 'N/A'}</div>
                <div className="col-span-2"><span className="text-muted-foreground">Legal Name:</span> {result.legal_name}</div>
                {result.expiration_date && (
                  <div className="col-span-2 flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    <span className="text-muted-foreground">Expires:</span> {result.expiration_date}
                  </div>
                )}
                {result.naics_codes?.length > 0 && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">NAICS:</span> {result.naics_codes.join(', ')}
                  </div>
                )}
              </div>
            )}

            {result.error && (
              <div className="flex items-center gap-2 text-red-700">
                <AlertCircle className="h-4 w-4" />
                {result.error}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
