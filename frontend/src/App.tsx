import { Toaster } from '@/components/ui/sonner'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'

// Pages
import Dashboard from './pages/Dashboard'
import DecisionReview from './pages/DecisionReview'
import LiveDiscovery from './pages/LiveDiscovery'
import PipelineMonitor from './pages/PipelineMonitor'
import RFPDiscovery from './pages/RFPDiscovery'
import SubmissionQueue from './pages/SubmissionQueue'
import { FutureOpportunities } from './pages/FutureOpportunities'
import PricingSimulator from './pages/PricingSimulator'
import SettingsPage from './pages/Settings'
import ProjectKickoffPage from './pages/ProjectKickoff'
import TeamingPartnersPage from './pages/TeamingPartners'
import CompanyProfiles from './pages/CompanyProfiles'

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
            <Route path="/discovery/live" element={<LiveDiscovery />} />
            <Route path="/forecasts" element={<FutureOpportunities />} />
            <Route path="/rfps/:rfpId/pricing" element={<PricingSimulator />} />
            <Route path="/pipeline" element={<PipelineMonitor />} />
            <Route path="/decisions" element={<DecisionReview />} />
            <Route path="/submissions" element={<SubmissionQueue />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/rfps/:rfpId/kickoff" element={<ProjectKickoffPage />} />
            <Route path="/rfps/:rfpId/partners" element={<TeamingPartnersPage />} />
            <Route path="/profiles" element={<CompanyProfiles />} />
          </Routes>
        </Layout>
      </Router>
      <Toaster />
    </QueryClientProvider>
  )
}

export default App
