import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { toast } from 'sonner'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 300000 // 5 minutes timeout for long operations (scraping, AI generation)
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor with retry logic
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Network error or 5xx server error - Retry logic
    if (
      !originalRequest._retry &&
      (error.code === 'ERR_NETWORK' || (error.response && error.response.status >= 500))
    ) {
      originalRequest._retry = true
      try {
        // Wait 1 second before retrying
        await new Promise(resolve => setTimeout(resolve, 1000))
        return apiClient(originalRequest)
      } catch (retryError) {
        return Promise.reject(retryError)
      }
    }

    // Global Error Handling
    if (error.response) {
      const status = error.response.status
      const data = error.response.data as any
      const message = data?.detail || data?.message || 'An unexpected error occurred'

      if (status >= 500) {
        toast.error(`Server Error: ${message}`)
      } else if (status === 401) {
        // Handle unauthorized (redirect to login if implemented)
        toast.error('Session expired. Please refresh.')
      } else if (status === 403) {
        toast.error('You do not have permission to perform this action.')
      } else if (status === 404) {
        // 404s might be expected in some cases, so maybe just log or show mild warning
        console.warn('Resource not found:', originalRequest.url)
      } else {
        toast.error(`Error: ${message}`)
      }
    } else if (error.request) {
      // The request was made but no response was received
      toast.error('Network Error: Unable to reach the server. Please check your connection.')
    } else {
      // Something happened in setting up the request that triggered an Error
      toast.error('Request Error: Failed to send request.')
    }

    return Promise.reject(error)
  }
)

export interface DiscoveryParams {
  limit?: number
  days_back?: number
}

export const api = {
  // RFP endpoints
  getDiscoveredRFPs: (filters: any) =>
    apiClient.get('/rfps/discovered', { params: filters }).then(res => res.data),

  getRFP: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}`).then(res => res.data),

  updateTriageDecision: (rfpId: string, decision: string) =>
    apiClient.post(`/rfps/${rfpId}/triage`, { decision }).then(res => res.data),

  deleteRFP: (rfpId: string) =>
    apiClient.delete(`/rfps/${rfpId}`).then(res => res.data),

  getRFPStats: () =>
    apiClient.get('/rfps/stats/overview').then(res => res.data),

  getRecentRFPs: (limit: number = 10) =>
    apiClient.get('/rfps/recent', { params: { limit } }).then(res => res.data),

  // Pipeline endpoints
  getPipelineStatus: (options?: { skip?: number; limit?: number; useCache?: boolean }) =>
    apiClient.get('/pipeline/status', {
      params: {
        skip: options?.skip ?? 0,
        limit: options?.limit ?? 50,
        use_cache: options?.useCache ?? true
      },
      timeout: 15000  // 15 second timeout
    }).then(res => res.data),

  getRFPPipeline: (rfpId: string) =>
    apiClient.get(`/pipeline/${rfpId}`).then(res => res.data),

  getPipelineMetrics: () =>
    apiClient.get('/pipeline/metrics/performance').then(res => res.data),

  clearPipelineCache: () =>
    apiClient.delete('/pipeline/cache').then(res => res.data),

  // Decision endpoints
  getPendingDecisions: () =>
    apiClient.get('/rfps/discovered', { params: { stage: 'decision_pending' } }).then(res => res.data),

  approveDecision: (rfpId: string) =>
    apiClient.post(`/rfps/${rfpId}/advance-stage`).then(res => res.data),

  rejectDecision: (rfpId: string) =>
    apiClient.put(`/rfps/${rfpId}`, { current_stage: 'rejected' }).then(res => res.data),

  // Submission endpoints
  getSubmissionQueue: (status?: string) =>
    apiClient.get('/submissions/queue', { params: { status } }).then(res => res.data),

  getSubmission: (submissionId: string) =>
    apiClient.get(`/submissions/${submissionId}`).then(res => res.data),

  createSubmission: (data: any) =>
    apiClient.post('/submissions', data).then(res => res.data),

  retrySubmission: (submissionId: string) =>
    apiClient.post(`/submissions/${submissionId}/retry`).then(res => res.data),

  getSubmissionStats: () =>
    apiClient.get('/submissions/stats/overview').then(res => res.data),

  // ML Pipeline Integration endpoints
  discoverRFPs: (params?: DiscoveryParams) =>
    apiClient.post('/rfps/discover', params).then(res => res.data),

  getDiscoveryStatus: (jobId: string) =>
    apiClient.get(`/rfps/discover/status/${jobId}`).then(res => res.data),

  cancelDiscovery: (jobId: string) =>
    apiClient.post(`/rfps/discover/cancel/${jobId}`).then(res => res.data),

  processManualRFP: (data: {
    title: string
    agency?: string
    solicitation_number?: string
    description?: string
    url?: string
    award_amount?: number
    response_deadline?: string
    category?: string
  }) =>
    apiClient.post('/rfps/process', data).then(res => res.data),

  // Bid Generation endpoints
  generateBid: (rfpId: string, options?: {
    generation_mode?: 'template' | 'claude_standard' | 'claude_enhanced' | 'claude_premium'
    enable_thinking?: boolean
    thinking_budget?: number
  }) =>
    apiClient.post(`/rfps/${rfpId}/generate-bid`, options || {}).then(res => res.data),

  getBidDocument: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/bid-document`).then(res => res.data),

  downloadBid: (bidId: string, format: 'markdown' | 'html' | 'json') =>
    apiClient.get(`/rfps/bids/${bidId}/download/${format}`, { responseType: 'blob' }).then(res => res.data),

  // Copilot endpoints
  saveBidDraft: (rfpId: string, data: { sections: Record<string, string> }) =>
    apiClient.post(`/copilot/${rfpId}/draft`, data).then(res => res.data),

  checkCompliance: (rfpId: string, sections: Record<string, { content: string }>) =>
    apiClient.post(`/copilot/${rfpId}/compliance-check`, { sections }).then(res => res.data),

  // Pricing Table endpoints
  generatePricingTable: (rfpId: string, options?: {
    num_websites?: number
    base_years?: number
    optional_years?: number
    base_budget_per_site?: number
  }) =>
    apiClient.post(`/rfps/${rfpId}/pricing-table`, options || {}).then(res => res.data),

  downloadPricingTableCSV: (rfpId: string, params?: {
    num_websites?: number
    base_years?: number
    optional_years?: number
    base_budget_per_site?: number
  }) =>
    apiClient.get(`/rfps/${rfpId}/pricing-table/csv`, {
      params,
      responseType: 'blob'
    }).then(res => res.data),

  // Prediction endpoints
  getPredictions: (confidence: number = 0.7, options?: { timeout?: number; use_ai?: boolean }) =>
    apiClient.get('/predictions/upcoming', {
      params: { confidence, timeout: options?.timeout ?? 55, use_ai: options?.use_ai ?? true },
      timeout: 60000 // 60 second client timeout
    }).then(res => res.data),

  getPredictionStatus: () =>
    apiClient.get('/predictions/status').then(res => res.data),

  getFallbackPredictions: (confidence: number = 0.3) =>
    apiClient.get('/predictions/fallback', { params: { confidence } }).then(res => res.data),

  triggerPredictionGeneration: (use_ai: boolean = true) =>
    apiClient.post('/predictions/generate', null, { params: { use_ai } }).then(res => res.data),

  clearPredictionCache: () =>
    apiClient.delete('/predictions/cache').then(res => res.data),

  // Pricing endpoints
  runPricingScenarios: (rfpId: string, params: any) =>
    apiClient.post(`/rfps/${rfpId}/pricing/scenarios`, params).then(res => res.data),
    
  getSubcontractors: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/pricing/subcontractors`).then(res => res.data),
    
  getPriceToWin: (rfpId: string, targetProb: number = 0.7) =>
    apiClient.get(`/rfps/${rfpId}/pricing/ptw`, { params: { target_prob: targetProb } }).then(res => res.data),
    
  // Competitor endpoints
  getCompetitors: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/competitors`).then(res => res.data),

  // Generation endpoints
  refineText: (text: string, instruction: string, context?: string) =>
    apiClient.post('/generation/refine', { text, instruction, context }).then(res => res.data),

  // Post-Award endpoints
  getPostAwardChecklist: (rfpInternalId: number) =>
    apiClient.get(`/rfps/${rfpInternalId}/checklist`).then(res => res.data),

  // Teaming endpoints
  getTeamingPartners: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/partners`).then(res => res.data),

  // Scraper endpoints
  scrapeRFP: (url: string, profileId?: number) =>
    apiClient.post('/scraper/scrape', { url, company_profile_id: profileId }).then(res => res.data),

  refreshRFP: (rfpId: string) =>
    apiClient.post(`/scraper/${rfpId}/refresh`).then(res => res.data),

  getRFPDocuments: (rfpId: string) =>
    apiClient.get(`/scraper/${rfpId}/documents`).then(res => res.data),

  downloadRFPDocument: (rfpId: string, docId: number) =>
    apiClient.get(`/scraper/${rfpId}/documents/${docId}/download`, { responseType: 'blob' }).then(res => res.data),

  getRFPQandA: (rfpId: string, newOnly: boolean = false) =>
    apiClient.get(`/scraper/${rfpId}/qa`, { params: { new_only: newOnly } }).then(res => res.data),

  analyzeRFPQandA: (rfpId: string) =>
    apiClient.post(`/scraper/${rfpId}/qa/analyze`).then(res => res.data),

  // Company Profile endpoints
  getCompanyProfiles: () =>
    apiClient.get('/profiles').then(res => res.data),

  createCompanyProfile: (data: any) =>
    apiClient.post('/profiles', data).then(res => res.data),

  updateCompanyProfile: (profileId: number, data: any) =>
    apiClient.put(`/profiles/${profileId}`, data).then(res => res.data),

  deleteCompanyProfile: (profileId: number) =>
    apiClient.delete(`/profiles/${profileId}`).then(res => res.data),

  setDefaultProfile: (profileId: number) =>
    apiClient.post(`/profiles/${profileId}/default`).then(res => res.data),

  // Document upload endpoints
  uploadDocument: (rfpId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post(`/documents/${rfpId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data)
  },

  getUploadedDocuments: (rfpId: string) =>
    apiClient.get(`/documents/${rfpId}/uploads`).then(res => res.data),

  getDocumentProcessingStatus: (rfpId: string, documentId: string) =>
    apiClient.get(`/documents/${rfpId}/uploads/${documentId}/status`).then(res => res.data),

  deleteUploadedDocument: (rfpId: string, documentId: string) =>
    apiClient.delete(`/documents/${rfpId}/uploads/${documentId}`).then(res => res.data),

  // Natural Language Search endpoints
  searchRFPs: (params: {
    query: string
    search_type?: 'hybrid' | 'semantic' | 'keyword'
    top_k?: number
    skip?: number
    min_score?: number
    filters?: Record<string, any>
  }) =>
    apiClient.post('/discovery/search', params).then(res => res.data),

  getSearchSuggestions: (q: string) =>
    apiClient.get('/discovery/search/suggestions', { params: { q } }).then(res => res.data),

  // Compliance Matrix endpoints
  getComplianceMatrix: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/compliance-matrix`).then(res => res.data),

  // Activity Log / Pipeline Events endpoints
  getActivityLog: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}/activity`).then(res => res.data),

  // RFP Stage management endpoints
  advanceStage: (rfpId: string) =>
    apiClient.post(`/rfps/${rfpId}/advance-stage`).then(res => res.data),

  archiveRFP: (rfpId: string) =>
    apiClient.post(`/rfps/${rfpId}/archive`).then(res => res.data),

  // AI Chat endpoints
  sendChatMessage: (rfpId: string, message: string, conversationId?: string) =>
    apiClient.post(`/rfps/${rfpId}/chat`, { message, conversation_id: conversationId }).then(res => res.data),

  getChatHistory: (rfpId: string, conversationId?: string) =>
    apiClient.get(`/rfps/${rfpId}/chat`, { params: { conversation_id: conversationId } }).then(res => res.data),
}




// WebSocket connection
export const connectWebSocket = (onMessage: (data: any) => void) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/pipeline`
  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  return ws
}
