/**
 * Types for the Import from URL feature.
 * Used by ImportRFPDialog for preview/edit flow.
 */

/**
 * Response from the /scraper/preview endpoint.
 * Contains extracted RFP data for user review before saving.
 */
export interface PreviewResponse {
  source_url: string
  source_platform: string
  detected_fields: DetectedFields
  documents: PreviewDocument[]
  qa_items: PreviewQA[]
  duplicate_check: DuplicateCheck | null
}

/**
 * Extracted RFP fields from preview.
 * All fields are nullable as extraction may not find everything.
 */
export interface DetectedFields {
  title: string | null
  solicitation_number: string | null
  agency: string | null
  office: string | null
  description: string | null
  posted_date: string | null
  response_deadline: string | null
  naics_code: string | null
  category: string | null
  estimated_value: number | null
}

/**
 * Document info from preview.
 * Documents are not downloaded until import is confirmed.
 */
export interface PreviewDocument {
  filename: string
  source_url: string
  file_type: string | null
}

/**
 * Q&A item from preview.
 */
export interface PreviewQA {
  question: string
  answer: string | null
  number: string | null
}

/**
 * Info about existing RFP if URL was already imported.
 * Used to warn users about duplicates.
 */
export interface DuplicateCheck {
  rfp_id: string
  title: string
  imported_at: string | null
}

/**
 * Editable fields that the user can modify before confirming import.
 * These are sent as overrides to the /scraper/confirm endpoint.
 */
export interface EditableFields {
  title: string
  solicitation_number: string
  agency: string
  office: string
  description: string
  naics_code: string
  category: string
}

/**
 * Request body for /scraper/confirm endpoint.
 */
export interface ConfirmImportRequest {
  source_url: string
  company_profile_id?: number
  overrides?: Partial<EditableFields>
}

/**
 * Import dialog step type.
 */
export type ImportStep = 'url' | 'preview' | 'importing'
