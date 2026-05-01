import { ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import type { RankedCandidate } from '../types'

type VerStatus = RankedCandidate['verification_status']
type AvailStatus = RankedCandidate['availability_status']

function cardBorder(v: VerStatus, a: AvailStatus): string {
  if (v === 'MISSING_CERT' || a === 'CONFLICT') return 'border-l-red-500'
  if (v === 'EXPIRING_SOON') return 'border-l-yellow-500'
  return 'border-l-green-500'
}

function VerBadge({ status }: { status: VerStatus }) {
  const styles: Record<VerStatus, string> = {
    VERIFIED: 'bg-green-950 text-green-400 ring-1 ring-green-800',
    EXPIRING_SOON: 'bg-yellow-950 text-yellow-400 ring-1 ring-yellow-800',
    MISSING_CERT: 'bg-red-950 text-red-400 ring-1 ring-red-800',
  }
  const labels: Record<VerStatus, string> = {
    VERIFIED: '✓ Verified',
    EXPIRING_SOON: '⚠ Expiring Soon',
    MISSING_CERT: '✕ Missing Cert',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

function AvailBadge({ status }: { status: AvailStatus }) {
  const styles: Record<AvailStatus, string> = {
    AVAILABLE: 'bg-green-950 text-green-400 ring-1 ring-green-800',
    CONFLICT: 'bg-red-950 text-red-400 ring-1 ring-red-800',
    UNKNOWN: 'bg-slate-800 text-slate-400 ring-1 ring-slate-600',
  }
  const labels: Record<AvailStatus, string> = {
    AVAILABLE: '✓ Available',
    CONFLICT: '✕ Conflict',
    UNKNOWN: '? Unknown',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

interface Props {
  data: RankedCandidate
}

export function CandidateCard({ data }: Props) {
  const [expanded, setExpanded] = useState(false)
  const c = data.candidate
  const scorePercent = Math.round(data.total_score * 100)

  return (
    <div
      className={`bg-slate-800 border border-slate-700 border-l-4 ${cardBorder(
        data.verification_status,
        data.availability_status,
      )} rounded-lg overflow-hidden animate-fade-in`}
    >
      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-xl font-bold text-slate-600 flex-shrink-0 w-6 text-right">
              {data.rank}
            </span>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-100 truncate">{c.name}</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {c.specialty} {c.role} &middot; {c.years_experience}yr exp &middot; ★{c.rating}
              </p>
            </div>
          </div>

          {/* Score */}
          <div className="text-right flex-shrink-0">
            <div className="text-lg font-bold text-slate-100 leading-none">
              {scorePercent}
              <span className="text-xs text-slate-500 font-normal">%</span>
            </div>
            <div className="text-xs text-slate-500 mt-0.5">match</div>
          </div>
        </div>

        {/* Score bar */}
        <div className="mt-3 h-1 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${scorePercent}%` }}
          />
        </div>

        {/* Status badges */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          <VerBadge status={data.verification_status} />
          <AvailBadge status={data.availability_status} />
        </div>

        {/* Reasoning */}
        <p className="text-xs text-slate-300 mt-3 leading-relaxed italic">
          "{data.reasoning}"
        </p>

        {/* Flags */}
        {data.flags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {data.flags.map((flag, i) => (
              <span
                key={i}
                className="text-xs bg-slate-700/80 text-slate-400 px-2 py-0.5 rounded"
              >
                {flag}
              </span>
            ))}
          </div>
        )}

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400
                     mt-3 transition-colors"
        >
          {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {expanded ? 'Hide profile' : 'View full profile'}
        </button>
      </div>

      {/* Expanded profile */}
      {expanded && (
        <div className="border-t border-slate-700 px-4 py-3 bg-slate-900/50 grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs animate-fade-in">
          <div>
            <p className="text-slate-500">Certifications</p>
            <p className="text-slate-300 mt-0.5">{c.certifications.join(' · ') || '—'}</p>
          </div>
          <div>
            <p className="text-slate-500">License</p>
            <p className="text-slate-300 mt-0.5">
              {c.license_state} &middot; expires {c.license_expiry}
            </p>
          </div>
          <div>
            <p className="text-slate-500">Available days</p>
            <p className="text-slate-300 mt-0.5">{c.availability.join(', ')}</p>
          </div>
          <div>
            <p className="text-slate-500">Last placement</p>
            <p className="text-slate-300 mt-0.5">{c.last_placement ?? '—'}</p>
          </div>
          <div className="col-span-2">
            <p className="text-slate-500">NPI</p>
            <p className="text-slate-300 font-mono mt-0.5 tracking-wide">{c.npi_number}</p>
          </div>
        </div>
      )}
    </div>
  )
}
