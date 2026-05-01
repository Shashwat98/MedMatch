export interface Candidate {
  id: string
  name: string
  specialty: string
  role: string
  certifications: string[]
  license_state: string
  license_expiry: string
  years_experience: number
  availability: string[]
  last_placement: string | null
  rating: number
  npi_number: string
}

export interface RankedCandidate {
  rank: number
  candidate: Candidate
  total_score: number
  verification_status: 'VERIFIED' | 'EXPIRING_SOON' | 'MISSING_CERT'
  availability_status: 'AVAILABLE' | 'CONFLICT' | 'UNKNOWN'
  reasoning: string
  flags: string[]
}

export interface ShiftRequirement {
  specialty: string
  role: string
  certifications_required: string[]
  location: string
  license_state: string
  shift_type: string
  shift_date: string | null
  shift_day_of_week: string | null
  min_years_experience: number
  urgency: string
  raw_text: string
}

export interface MatchResponse {
  shortlist: RankedCandidate[]
  execution_trace: string[]
  shift_requirement: ShiftRequirement | null
  total_candidates_evaluated: number
  error: string | null
}

export type PipelineStatus = 'idle' | 'running' | 'done' | 'error'

export interface WsMessage {
  type: 'trace' | 'done' | 'error'
  message?: string
  result?: MatchResponse
}
