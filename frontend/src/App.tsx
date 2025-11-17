import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'

// Pages
import Dashboard from './pages/Dashboard'
import RFPDiscovery from './pages/RFPDiscovery'
import PipelineMonitor from './pages/PipelineMonitor'
import DecisionReview from './pages/DecisionReview'
import SubmissionQueue from './pages/SubmissionQueue'

// Components
import Layout from './components/Layout'

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000
    }
  }
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/discovery" element={<RFPDiscovery />} />
            <Route path="/pipeline" element={<PipelineMonitor />} />
            <Route path="/decisions" element={<DecisionReview />} />
            <Route path="/submissions" element={<SubmissionQueue />} />
          </Routes>
        </Layout>
      </Router>
      <Toaster />
    </QueryClientProvider>
  )
}

export default App
