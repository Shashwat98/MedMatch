import { Activity, AlertTriangle } from 'lucide-react'
import { CandidateCard } from './components/CandidateCard'
import { ExecutionTrace } from './components/ExecutionTrace'
import { ShiftInput } from './components/ShiftInput'
import { usePipeline } from './hooks/usePipeline'
import type { ShiftRequirement } from './types'

function RequirementSummary({ req }: { req: ShiftRequirement }) {
  return (
    <div className="mb-4 p-3 bg-slate-800/50 border border-slate-700 rounded-lg text-xs">
      <p className="text-slate-500 uppercase tracking-widest mb-1.5">Parsed shift</p>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-slate-300">
        <span>
          <span className="text-slate-500">Role </span>
          {req.role} · {req.specialty}
        </span>
        <span>
          <span className="text-slate-500">Location </span>
          {req.location}
        </span>
        <span>
          <span className="text-slate-500">Shift </span>
          {req.shift_type}
          {req.shift_day_of_week ? ` · ${req.shift_day_of_week}` : ''}
        </span>
        <span>
          <span className="text-slate-500">Certs </span>
          {req.certifications_required.join(', ') || 'none'}
        </span>
        <span>
          <span className="text-slate-500">Urgency </span>
          {req.urgency}
        </span>
      </div>
    </div>
  )
}

function ResultsPanel({
  result,
  status,
  errorMessage,
}: {
  result: ReturnType<typeof usePipeline>['result']
  status: ReturnType<typeof usePipeline>['status']
  errorMessage: string | null
}) {
  return (
    <div className="flex flex-col h-full min-h-0">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3 flex-shrink-0">
        Candidate Shortlist
      </p>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-3 pr-0.5">
        {status === 'idle' && (
          <p className="text-slate-700 text-sm italic">
            Results will appear here after the pipeline completes.
          </p>
        )}

        {status === 'running' && (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="bg-slate-800 border border-slate-700 rounded-lg h-28 animate-pulse"
              />
            ))}
          </div>
        )}

        {status === 'error' && (
          <div className="flex items-start gap-2 p-3 bg-red-950/40 border border-red-800 rounded-lg text-sm text-red-300">
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
            {errorMessage ?? 'Something went wrong.'}
          </div>
        )}

        {status === 'done' && result && (
          <>
            {result.shift_requirement && (
              <RequirementSummary req={result.shift_requirement} />
            )}

            <p className="text-xs text-slate-500">
              {result.shortlist.length} candidates ranked ·{' '}
              {result.total_candidates_evaluated} evaluated
            </p>

            {result.shortlist.map(candidate => (
              <CandidateCard key={candidate.candidate.id} data={candidate} />
            ))}

            {result.error && (
              <div className="p-3 bg-yellow-950/40 border border-yellow-800 rounded-lg text-xs text-yellow-300">
                Partial result — pipeline error: {result.error}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const { status, trace, result, errorMessage, run } = usePipeline()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-slate-700/60 px-5 py-3 flex items-center gap-3 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center flex-shrink-0">
          <Activity size={14} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-none">MedMatch</h1>
          <p className="text-xs text-slate-500 mt-0.5">Healthcare Staffing Intelligence</p>
        </div>
        <div className="ml-auto hidden md:flex items-center gap-1.5">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              status === 'running' ? 'bg-blue-400 animate-pulse' : 'bg-green-500'
            }`}
          />
          <span className="text-xs text-slate-500">
            {status === 'running' ? 'Processing' : 'Ready'}
          </span>
        </div>
      </header>

      {/* Three-panel layout */}
      <main className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* Left — Input */}
        <aside className="flex-shrink-0 w-full lg:w-72 xl:w-80 border-b lg:border-b-0 lg:border-r border-slate-700/60 p-4 lg:overflow-y-auto">
          <ShiftInput onSubmit={run} isRunning={status === 'running'} />
        </aside>

        {/* Centre — Trace */}
        <section className="flex-1 border-b lg:border-b-0 lg:border-r border-slate-700/60 p-4 flex flex-col min-h-0 min-h-[280px] lg:min-h-0">
          <ExecutionTrace trace={trace} status={status} />
        </section>

        {/* Right — Results */}
        <aside className="flex-shrink-0 w-full lg:w-96 xl:w-[420px] p-4 flex flex-col min-h-0 min-h-[280px] lg:min-h-0">
          <ResultsPanel result={result} status={status} errorMessage={errorMessage} />
        </aside>
      </main>
    </div>
  )
}
