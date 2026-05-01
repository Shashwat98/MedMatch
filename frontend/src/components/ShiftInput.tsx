import { Loader2, Send, Zap } from 'lucide-react'
import { useState } from 'react'

const SAMPLE_PROMPT =
  'Looking for an ICU RN for a night shift this Saturday in Boston, MA. ' +
  'Must have ACLS and BLS certifications. At least 2 years of ICU experience ' +
  'preferred. This is urgent — facility is short-staffed.'

interface Props {
  onSubmit: (requirement: string) => void
  isRunning: boolean
}

export function ShiftInput({ onSubmit, isRunning }: Props) {
  const [value, setValue] = useState('')

  const handleSubmit = () => {
    if (!value.trim() || isRunning) return
    onSubmit(value.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
          Shift Requirement
        </p>
        <textarea
          className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2.5 text-sm
                     text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500
                     resize-none transition-colors leading-relaxed"
          rows={10}
          placeholder="Describe the open shift in plain English…"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
        />
        <p className="text-xs text-slate-600 mt-1.5">⌘ Enter to submit</p>
      </div>

      <button
        onClick={handleSubmit}
        disabled={!value.trim() || isRunning}
        className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-500
                   active:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
                   text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
      >
        {isRunning ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            Running pipeline…
          </>
        ) : (
          <>
            <Send size={14} />
            Run Pipeline
          </>
        )}
      </button>

      <div className="mt-auto">
        <p className="text-xs text-slate-600 uppercase tracking-widest mb-2">Quick demo</p>
        <button
          onClick={() => setValue(SAMPLE_PROMPT)}
          disabled={isRunning}
          className="flex items-start gap-2 w-full text-left bg-slate-800 hover:bg-slate-750
                     border border-slate-700 hover:border-slate-600 rounded-lg p-3
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed group"
        >
          <Zap size={13} className="text-yellow-500 mt-0.5 flex-shrink-0" />
          <span className="text-xs text-slate-400 group-hover:text-slate-300 leading-relaxed transition-colors">
            ICU RN · night shift · Boston, MA · ACLS + BLS · urgent
          </span>
        </button>
      </div>
    </div>
  )
}
