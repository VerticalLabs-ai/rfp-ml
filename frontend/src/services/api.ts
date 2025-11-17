import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

export const api = {
  // RFP endpoints
  getDiscoveredRFPs: (filters: any) =>
    apiClient.get('/rfps/discovered', { params: filters }).then(res => res.data),

  getRFP: (rfpId: string) =>
    apiClient.get(`/rfps/${rfpId}`).then(res => res.data),

  updateTriageDecision: (rfpId: string, decision: string) =>
    apiClient.post(`/rfps/${rfpId}/triage`, { decision }).then(res => res.data),

  getRFPStats: () =>
    apiClient.get('/rfps/stats/overview').then(res => res.data),

  getRecentRFPs: (limit: number = 10) =>
    apiClient.get('/rfps/recent', { params: { limit } }).then(res => res.data),

  // Pipeline endpoints
  getPipelineStatus: () =>
    apiClient.get('/pipeline/status').then(res => res.data),

  getRFPPipeline: (rfpId: string) =>
    apiClient.get(`/pipeline/${rfpId}`).then(res => res.data),

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
    apiClient.get('/submissions/stats/overview').then(res => res.data)
}

// WebSocket connection
export const connectWebSocket = (onMessage: (data: any) => void) => {
  const ws = new WebSocket('ws://localhost:8000/ws/pipeline')

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }

  return ws
}
