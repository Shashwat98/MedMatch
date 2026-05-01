import { useCallback, useEffect, useRef, useState } from 'react'
import type { MatchResponse, PipelineStatus, WsMessage } from '../types'

const WS_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws')

interface PipelineState {
  status: PipelineStatus
  trace: string[]
  result: MatchResponse | null
  errorMessage: string | null
}

const INITIAL: PipelineState = {
  status: 'idle',
  trace: [],
  result: null,
  errorMessage: null,
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)

  const run = useCallback((requirement: string) => {
    wsRef.current?.close()

    setState({ status: 'running', trace: [], result: null, errorMessage: null })

    const ws = new WebSocket(`${WS_BASE}/ws/match`)
    wsRef.current = ws

    ws.onopen = () => ws.send(JSON.stringify({ requirement }))

    ws.onmessage = (event: MessageEvent<string>) => {
      const msg = JSON.parse(event.data) as WsMessage

      if (msg.type === 'trace') {
        setState(prev => ({ ...prev, trace: [...prev.trace, msg.message!] }))
      } else if (msg.type === 'done') {
        setState(prev => ({ ...prev, status: 'done', result: msg.result! }))
      } else if (msg.type === 'error') {
        setState(prev => ({
          ...prev,
          status: 'error',
          errorMessage: msg.message ?? 'An unknown error occurred',
        }))
      }
    }

    ws.onerror = () => {
      setState(prev => ({
        ...prev,
        status: 'error',
        errorMessage: 'Connection failed. Is the backend running on port 8000?',
      }))
    }

    ws.onclose = (event: CloseEvent) => {
      if (!event.wasClean) {
        setState(prev => {
          if (prev.status === 'running') {
            return { ...prev, status: 'error', errorMessage: 'Connection closed unexpectedly' }
          }
          return prev
        })
      }
    }
  }, [])

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => { wsRef.current?.close() }
  }, [])

  return { ...state, run }
}
