import { CheckCircle2, Loader2 } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { PipelineStatus } from '../types'

const AGENT_STYLES: Record<string, string> = {
  RequirementParser: 'text-blue-400',
  CandidateMatcher: 'text-purple-400',
  CredentialVerifier: 'text-orange-400',
  AvailabilityAgent: 'text-teal-400',
  RankingAgent: 'text-pink-400',
}

function TraceEntry({ message }: { message: string }) {
  const match = message.match(/^\[([^\]]+)\]\s*(.*)$/)

  if (!match) {
    return (
      <div className="py-0.5 text-slate-500 animate-fade-in">{message}</div>
    )
  }

  const [, agent, content] = match
  const agentStyle = AGENT_STYLES[agent] ?? 'text-slate-300'

  return (
    <div className="py-0.5 leading-relaxed animate-fade-in">
      <span className={`${agentStyle} font-semibold`}>[{agent}]</span>
      <span className="text-slate-400"> {content}</span>
    </div>
  )
}

interface Props {
  trace: string[]
  status: PipelineStatus
}

export function ExecutionTrace({ trace, status }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [trace])

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
          Agent Execution
        </p>
        {status === 'running' && (
          <span className="flex items-center gap-1.5 text-xs text-blue-400">
            <Loader2 size={10} className="animate-spin" />
            live
          </span>
        )}
        {status === 'done' && (
          <span className="flex items-center gap-1.5 text-xs text-green-400">
            <CheckCircle2 size={10} />
            complete
          </span>
        )}
      </div>

      <div className="flex-1 min-h-0 bg-slate-950 rounded-lg p-4 overflow-y-auto font-mono text-xs leading-5">
        {status === 'idle' && (
          <p className="text-slate-700 italic select-none">
            Submit a shift requirement to watch the agent pipeline run in real time…
          </p>
        )}

        {trace.map((msg, i) => (
          <TraceEntry key={i} message={msg} />
        ))}

        {status === 'running' && trace.length > 0 && (
          <div className="flex items-center gap-2 text-slate-600 mt-1 animate-pulse">
            <span className="inline-block w-1.5 h-3 bg-slate-600 rounded-sm" />
          </div>
        )}

        {status === 'error' && (
          <div className="text-red-400 mt-2">Pipeline encountered an error.</div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
