import { api } from '@/services/api'
import { useQuery } from '@tanstack/react-query'
import { Globe, Loader2, Mail, ShieldCheck, Tag, Users } from 'lucide-react'
import { useParams } from 'react-router-dom'

interface TeamingPartner {
  uei: string
  name: string
  score: number
  match_reason: string
  business_types: string // JSON string
  capabilities: string
  poc_email: string
  website: string
}

export default function TeamingPartnersPage() {
  const { rfpId } = useParams<{ rfpId: string }>()

  const { data: rfp } = useQuery({
    queryKey: ['rfps', rfpId],
    queryFn: () => api.getRFP(rfpId!),
    enabled: !!rfpId,
  })

  const { data: partners, isLoading } = useQuery<TeamingPartner[]>({
    queryKey: ['teamingPartners', rfpId],
    queryFn: () => api.getTeamingPartners(rfpId!),
    enabled: !!rfpId,
    meta: { errorMessage: "Failed to load partners." }, // Generic error message for toast
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        <p className="text-slate-500">Analyzing partner database for best matches...</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Users className="h-6 w-6 text-blue-600" />
          Teaming Partner Matchmaking
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Recommended partners based on NAICS codes ({rfp?.naics_code || 'N/A'}) and capability matching.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {partners?.length === 0 ? (
          <div className="text-center p-12 bg-slate-50 dark:bg-slate-800 rounded-lg border border-dashed border-slate-300 dark:border-slate-700">
            <Users className="mx-auto h-12 w-12 text-slate-400" />
            <h3 className="mt-2 text-sm font-medium text-slate-900 dark:text-white">No partners found</h3>
            <p className="mt-1 text-sm text-slate-500">No registered partners matched the criteria for this RFP.</p>
          </div>
        ) : (
          partners?.map((partner) => (
            <PartnerCard key={partner.uei} partner={partner} />
          ))
        )}
      </div>
    </div>
  )
}

function PartnerCard({ partner }: { partner: TeamingPartner }) {
  const handleContactPartner = () => {
    if (partner.poc_email) {
      window.location.href = `mailto:${partner.poc_email}?subject=Partnership Inquiry - ${encodeURIComponent(partner.name)}`
    }
  }
  // Parse business types safely
  let certs: string[] = []
  try {
    certs = JSON.parse(partner.business_types || '[]')
  } catch {
    certs = []
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm p-6 hover:shadow-md transition-shadow">
      <div className="flex flex-col md:flex-row justify-between gap-4">
        <div className="flex-1 space-y-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-blue-600 dark:text-blue-400">
                {partner.name}
              </h3>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                Match Score: {partner.score}
              </span>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1 mt-1">
              <ShieldCheck className="h-3 w-3" />
              UEI: {partner.uei}
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">Capabilities</h4>
            <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
              {partner.capabilities || "No capability narrative provided."}
            </p>
          </div>

          {certs.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {certs.map((cert, idx) => (
                <span key={idx} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300">
                  <Tag className="h-3 w-3 mr-1" />
                  {cert}
                </span>
              ))}
            </div>
          )}

          <div className="text-xs text-slate-400">
            Match Reason: {partner.match_reason}
          </div>
        </div>

        <div className="md:w-64 shrink-0 space-y-3 border-t md:border-t-0 md:border-l border-slate-200 dark:border-slate-700 md:pl-6 pt-4 md:pt-0">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white">Contact Info</h4>

          {partner.website && (
            <a
              href={partner.website.startsWith('http') ? partner.website : `https://${partner.website}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
            >
              <Globe className="h-4 w-4" />
              Website
            </a>
          )}

          {partner.poc_email && (
            <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <Mail className="h-4 w-4" />
              {partner.poc_email}
            </div>
          )}

          <button
            type="button"
            onClick={handleContactPartner}
            disabled={!partner.poc_email}
            className="w-full mt-2 px-4 py-2 bg-slate-900 dark:bg-slate-700 text-white text-sm font-medium rounded-lg hover:bg-slate-800 dark:hover:bg-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Contact Partner
          </button>
        </div>
      </div>
    </div>
  )
}
