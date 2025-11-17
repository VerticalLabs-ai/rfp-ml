export interface RFPOpportunity {
  id: number;
  rfp_id: string;
  solicitation_number?: string;
  title: string;
  description?: string;
  agency?: string;
  office?: string;
  naics_code?: string;
  category?: string;

  // Dates
  posted_date?: string;
  response_deadline?: string;
  award_date?: string;

  // Amounts
  award_amount?: number;
  estimated_value?: number;

  // Pipeline tracking
  current_stage: PipelineStage;
  triage_score?: number;
  overall_score?: number;
  decision_recommendation?: 'go' | 'no-go' | 'review';
  confidence_level?: number;

  // Timestamps
  discovered_at: string;
  started_at: string;
  updated_at: string;
  completed_at?: string;

  // Assignment
  assigned_to?: string;
  priority: number;
}

export type PipelineStage =
  | 'discovered'
  | 'triaged'
  | 'analyzing'
  | 'pricing'
  | 'decision_pending'
  | 'approved'
  | 'document_generation'
  | 'review'
  | 'submission_ready'
  | 'submitted'
  | 'rejected'
  | 'failed';

export interface RFPStats {
  total_discovered: number;
  in_pipeline: number;
  approved_count: number;
  rejected_count: number;
  submitted_count: number;
  pending_reviews: number;
}

export interface SubmissionStats {
  total_submissions: number;
  queued: number;
  submitted: number;
  confirmed: number;
  failed: number;
  success_rate: number;
}

export type SubmissionStatus =
  | 'queued'
  | 'validating'
  | 'formatting'
  | 'submitting'
  | 'submitted'
  | 'confirmed'
  | 'failed'
  | 'rejected';

export interface Submission {
  id: number;
  submission_id: string;
  rfp_id: number;
  portal: string;
  status: SubmissionStatus;
  scheduled_time?: string;
  submitted_at?: string;
  confirmed_at?: string;
  confirmation_number?: string;
  attempts: number;
  created_at: string;
}
