import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Building2,
  Plus,
  Pencil,
  Trash2,
  Star,
  Phone,
  Mail,
  Globe,
  Award,
  Briefcase,
  Users
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api } from '@/lib/api'

interface CompanyProfile {
  id: number
  name: string
  legal_name: string | null
  is_default: boolean
  uei: string | null
  cage_code: string | null
  duns_number: string | null
  headquarters: string | null
  website: string | null
  primary_contact_name: string | null
  primary_contact_email: string | null
  primary_contact_phone: string | null
  established_year: number | null
  employee_count: string | null
  certifications: string[]
  naics_codes: string[]
  core_competencies: string[]
  past_performance: object[]
  created_at: string
  updated_at: string
}

interface ProfileFormData {
  name: string
  legal_name: string
  uei: string
  cage_code: string
  duns_number: string
  headquarters: string
  website: string
  primary_contact_name: string
  primary_contact_email: string
  primary_contact_phone: string
  established_year: string
  employee_count: string
  certifications: string
  naics_codes: string
  core_competencies: string
}

const emptyFormData: ProfileFormData = {
  name: '',
  legal_name: '',
  uei: '',
  cage_code: '',
  duns_number: '',
  headquarters: '',
  website: '',
  primary_contact_name: '',
  primary_contact_email: '',
  primary_contact_phone: '',
  established_year: '',
  employee_count: '',
  certifications: '',
  naics_codes: '',
  core_competencies: '',
}

export default function CompanyProfiles() {
  const queryClient = useQueryClient()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingProfile, setEditingProfile] = useState<CompanyProfile | null>(null)
  const [formData, setFormData] = useState<ProfileFormData>(emptyFormData)

  // Fetch profiles
  const { data: profiles, isLoading } = useQuery({
    queryKey: ['company-profiles'],
    queryFn: () => api.get<CompanyProfile[]>('/profiles')
  })

  // Create profile mutation
  const createMutation = useMutation({
    mutationFn: (data: object) => api.post<CompanyProfile>('/profiles', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-profiles'] })
      toast.success('Profile created successfully')
      setIsDialogOpen(false)
      resetForm()
    },
    onError: (error: Error) => {
      toast.error(`Failed to create profile: ${error.message}`)
    }
  })

  // Update profile mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: object }) =>
      api.put<CompanyProfile>(`/profiles/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-profiles'] })
      toast.success('Profile updated successfully')
      setIsDialogOpen(false)
      resetForm()
    },
    onError: (error: Error) => {
      toast.error(`Failed to update profile: ${error.message}`)
    }
  })

  // Delete profile mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/profiles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-profiles'] })
      toast.success('Profile deleted successfully')
    },
    onError: (error: Error) => {
      toast.error(`Failed to delete profile: ${error.message}`)
    }
  })

  // Set default mutation
  const setDefaultMutation = useMutation({
    mutationFn: (id: number) => api.post(`/profiles/${id}/default`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['company-profiles'] })
      toast.success('Default profile updated')
    },
    onError: (error: Error) => {
      toast.error(`Failed to set default: ${error.message}`)
    }
  })

  const resetForm = () => {
    setFormData(emptyFormData)
    setEditingProfile(null)
  }

  const openCreateDialog = () => {
    resetForm()
    setIsDialogOpen(true)
  }

  const openEditDialog = (profile: CompanyProfile) => {
    setEditingProfile(profile)
    setFormData({
      name: profile.name,
      legal_name: profile.legal_name || '',
      uei: profile.uei || '',
      cage_code: profile.cage_code || '',
      duns_number: profile.duns_number || '',
      headquarters: profile.headquarters || '',
      website: profile.website || '',
      primary_contact_name: profile.primary_contact_name || '',
      primary_contact_email: profile.primary_contact_email || '',
      primary_contact_phone: profile.primary_contact_phone || '',
      established_year: profile.established_year?.toString() || '',
      employee_count: profile.employee_count || '',
      certifications: profile.certifications.join(', '),
      naics_codes: profile.naics_codes.join(', '),
      core_competencies: profile.core_competencies.join(', '),
    })
    setIsDialogOpen(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const data = {
      name: formData.name,
      legal_name: formData.legal_name || null,
      uei: formData.uei || null,
      cage_code: formData.cage_code || null,
      duns_number: formData.duns_number || null,
      headquarters: formData.headquarters || null,
      website: formData.website || null,
      primary_contact_name: formData.primary_contact_name || null,
      primary_contact_email: formData.primary_contact_email || null,
      primary_contact_phone: formData.primary_contact_phone || null,
      established_year: formData.established_year ? parseInt(formData.established_year) : null,
      employee_count: formData.employee_count || null,
      certifications: formData.certifications ? formData.certifications.split(',').map(s => s.trim()).filter(Boolean) : [],
      naics_codes: formData.naics_codes ? formData.naics_codes.split(',').map(s => s.trim()).filter(Boolean) : [],
      core_competencies: formData.core_competencies ? formData.core_competencies.split(',').map(s => s.trim()).filter(Boolean) : [],
    }

    if (editingProfile) {
      updateMutation.mutate({ id: editingProfile.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleDelete = (profile: CompanyProfile) => {
    if (confirm(`Are you sure you want to delete "${profile.name}"?`)) {
      deleteMutation.mutate(profile.id)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Building2 className="h-6 w-6 text-blue-500" />
            Company Profiles
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Manage company profiles for proposal generation
          </p>
        </div>
        <Button onClick={openCreateDialog} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Profile
        </Button>
      </div>

      {/* Profiles Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="space-y-2">
                <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-3/4" />
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-5/6" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : profiles?.length === 0 ? (
        <Card className="p-12 text-center">
          <Building2 className="h-12 w-12 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
            No Company Profiles
          </h3>
          <p className="text-slate-500 dark:text-slate-400 mb-4">
            Create your first company profile to use for proposal generation.
          </p>
          <Button onClick={openCreateDialog} className="gap-2">
            <Plus className="h-4 w-4" />
            Create Profile
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles?.map((profile) => (
            <Card key={profile.id} className={profile.is_default ? 'ring-2 ring-blue-500' : ''}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {profile.name}
                      {profile.is_default && (
                        <Badge variant="secondary" className="gap-1">
                          <Star className="h-3 w-3" />
                          Default
                        </Badge>
                      )}
                    </CardTitle>
                    {profile.legal_name && (
                      <CardDescription>{profile.legal_name}</CardDescription>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditDialog(profile)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(profile)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Identifiers */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {profile.uei && (
                    <div>
                      <span className="text-slate-500">UEI:</span>{' '}
                      <span className="font-mono">{profile.uei}</span>
                    </div>
                  )}
                  {profile.cage_code && (
                    <div>
                      <span className="text-slate-500">CAGE:</span>{' '}
                      <span className="font-mono">{profile.cage_code}</span>
                    </div>
                  )}
                </div>

                {/* Contact */}
                <div className="space-y-1 text-sm">
                  {profile.primary_contact_name && (
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4 text-slate-400" />
                      {profile.primary_contact_name}
                    </div>
                  )}
                  {profile.primary_contact_email && (
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-slate-400" />
                      {profile.primary_contact_email}
                    </div>
                  )}
                  {profile.primary_contact_phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-slate-400" />
                      {profile.primary_contact_phone}
                    </div>
                  )}
                  {profile.website && (
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4 text-slate-400" />
                      <a href={profile.website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                        {profile.website}
                      </a>
                    </div>
                  )}
                </div>

                {/* Business Info */}
                <div className="flex flex-wrap gap-2">
                  {profile.established_year && (
                    <Badge variant="outline" className="gap-1">
                      <Briefcase className="h-3 w-3" />
                      Est. {profile.established_year}
                    </Badge>
                  )}
                  {profile.employee_count && (
                    <Badge variant="outline" className="gap-1">
                      <Users className="h-3 w-3" />
                      {profile.employee_count} employees
                    </Badge>
                  )}
                </div>

                {/* Certifications */}
                {profile.certifications.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {profile.certifications.map((cert, i) => (
                      <Badge key={i} variant="secondary" className="gap-1">
                        <Award className="h-3 w-3" />
                        {cert}
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Actions */}
                {!profile.is_default && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => setDefaultMutation.mutate(profile.id)}
                  >
                    <Star className="h-4 w-4 mr-2" />
                    Set as Default
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProfile ? 'Edit Company Profile' : 'Create Company Profile'}
            </DialogTitle>
            <DialogDescription>
              {editingProfile
                ? 'Update the company profile information below.'
                : 'Add a new company profile for proposal generation.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Display Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Company"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="legal_name">Legal Name</Label>
                <Input
                  id="legal_name"
                  value={formData.legal_name}
                  onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                  placeholder="My Company, LLC"
                />
              </div>
            </div>

            {/* Identifiers */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="uei">UEI</Label>
                <Input
                  id="uei"
                  value={formData.uei}
                  onChange={(e) => setFormData({ ...formData, uei: e.target.value })}
                  placeholder="ABC123DEF456"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cage_code">CAGE Code</Label>
                <Input
                  id="cage_code"
                  value={formData.cage_code}
                  onChange={(e) => setFormData({ ...formData, cage_code: e.target.value })}
                  placeholder="12ABC"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duns_number">DUNS Number</Label>
                <Input
                  id="duns_number"
                  value={formData.duns_number}
                  onChange={(e) => setFormData({ ...formData, duns_number: e.target.value })}
                  placeholder="123456789"
                />
              </div>
            </div>

            {/* Contact Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="headquarters">Headquarters</Label>
                <Input
                  id="headquarters"
                  value={formData.headquarters}
                  onChange={(e) => setFormData({ ...formData, headquarters: e.target.value })}
                  placeholder="Washington, DC"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="website">Website</Label>
                <Input
                  id="website"
                  type="url"
                  value={formData.website}
                  onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  placeholder="https://example.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="primary_contact_name">Contact Name</Label>
                <Input
                  id="primary_contact_name"
                  value={formData.primary_contact_name}
                  onChange={(e) => setFormData({ ...formData, primary_contact_name: e.target.value })}
                  placeholder="John Smith"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="primary_contact_email">Contact Email</Label>
                <Input
                  id="primary_contact_email"
                  type="email"
                  value={formData.primary_contact_email}
                  onChange={(e) => setFormData({ ...formData, primary_contact_email: e.target.value })}
                  placeholder="john@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="primary_contact_phone">Contact Phone</Label>
                <Input
                  id="primary_contact_phone"
                  type="tel"
                  value={formData.primary_contact_phone}
                  onChange={(e) => setFormData({ ...formData, primary_contact_phone: e.target.value })}
                  placeholder="(555) 123-4567"
                />
              </div>
            </div>

            {/* Business Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="established_year">Year Established</Label>
                <Input
                  id="established_year"
                  type="number"
                  min="1800"
                  max="2030"
                  value={formData.established_year}
                  onChange={(e) => setFormData({ ...formData, established_year: e.target.value })}
                  placeholder="2010"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="employee_count">Employee Count</Label>
                <Input
                  id="employee_count"
                  value={formData.employee_count}
                  onChange={(e) => setFormData({ ...formData, employee_count: e.target.value })}
                  placeholder="50-100"
                />
              </div>
            </div>

            {/* Certifications & NAICS */}
            <div className="space-y-2">
              <Label htmlFor="certifications">Certifications (comma-separated)</Label>
              <Input
                id="certifications"
                value={formData.certifications}
                onChange={(e) => setFormData({ ...formData, certifications: e.target.value })}
                placeholder="8(a), HUBZone, SDVOSB, ISO 9001"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="naics_codes">NAICS Codes (comma-separated)</Label>
              <Input
                id="naics_codes"
                value={formData.naics_codes}
                onChange={(e) => setFormData({ ...formData, naics_codes: e.target.value })}
                placeholder="541512, 541519, 541611"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="core_competencies">Core Competencies (comma-separated)</Label>
              <Textarea
                id="core_competencies"
                value={formData.core_competencies}
                onChange={(e) => setFormData({ ...formData, core_competencies: e.target.value })}
                placeholder="Software Development, Cloud Migration, Cybersecurity, Data Analytics"
                rows={2}
              />
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save Profile'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
