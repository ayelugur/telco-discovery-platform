import { useEffect, useRef } from 'react'
import { Bot, CheckCircle, AlertCircle, Loader2, ChevronRight } from 'lucide-react'

const AGENT_COLORS = {
  discovery: 'text-blue-400 border-blue-500',
  risk: 'text-red-400 border-red-500',
  ai_opportunities: 'text-green-400 border-green-500',
  roadmap: 'text-purple-400 border-purple-500',
}

const AGENT_BG = {
  discovery: 'bg-blue-500/10',
  risk: 'bg-red-500/10',
  ai_opportunities: 'bg-green-500/10',
  roadmap: 'bg-purple-500/10',
}

function AgentStep({ agent, label, status, log, isActive }) {
  const logRef = useRef()
  const color = AGENT_COLORS[agent] || 'text-slate-400 border-slate-500'
  const bg = AGENT_BG[agent] || 'bg-slate-500/10'

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [log])

  return (
    <div className={`rounded-xl border ${isActive ? color.split(' ')[1] : 'border-slate-700'}
      overflow-hidden transition-all duration-300`}>
      {/* Agent header */}
      <div className={`flex items-center gap-3 px-4 py-3 ${isActive ? bg : ''}`}>
        <div className="flex-shrink-0">
          {status === 'running' && <Loader2 className={`w-4 h-4 animate-spin ${color.split(' ')[0]}`} />}
          {status === 'done' && <CheckCircle className="w-4 h-4 text-green-400" />}
          {status === 'error' && <AlertCircle className="w-4 h-4 text-red-400" />}
          {!status && <Bot className="w-4 h-4 text-slate-600" />}
        </div>
        <div className="flex-1">
          <p className={`text-sm font-semibold ${status ? color.split(' ')[0] : 'text-slate-500'}`}>
            {label}
          </p>
        </div>
        <div className="text-xs font-mono">
          {status === 'running' && <span className="text-yellow-400 animate-pulse">● LIVE</span>}
          {status === 'done' && <span className="text-green-400">✓ DONE</span>}
          {status === 'error' && <span className="text-red-400">✗ ERROR</span>}
          {!status && <span className="text-slate-600">QUEUED</span>}
        </div>
      </div>

      {/* Live log output */}
      {(status === 'running' || status === 'done') && log && (
        <div ref={logRef}
          className="bg-slate-950 border-t border-slate-800 p-3 max-h-40 overflow-y-auto font-mono text-xs
            text-slate-300 leading-relaxed whitespace-pre-wrap">
          {log}
          {status === 'running' && <span className="animate-pulse text-brand-400">▋</span>}
        </div>
      )}
    </div>
  )
}

export function AgentStream({ AGENTS, AGENT_LABELS, agentStatus, agentLogs, isRunning, isComplete, onRun }) {
  return (
    <div className="h-full flex flex-col">
      {/* Run button */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100">Agent Analysis Console</h2>
          <p className="text-xs text-slate-500 mt-0.5">4 specialized Claude agents running sequentially</p>
        </div>
        <button
          onClick={onRun}
          disabled={isRunning}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50
            disabled:cursor-not-allowed text-white font-semibold px-5 py-2.5 rounded-xl
            transition-all duration-200 shadow-lg shadow-brand-600/20 text-sm">
          {isRunning ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</>
          ) : (
            <><ChevronRight className="w-4 h-4" /> Run Analysis</>
          )}
        </button>
      </div>

      {/* Agent steps */}
      <div className="space-y-3 flex-1 overflow-y-auto pr-1">
        {AGENTS.map(agent => (
          <AgentStep
            key={agent}
            agent={agent}
            label={AGENT_LABELS[agent]}
            status={agentStatus[agent]}
            log={agentLogs[agent]}
            isActive={agentStatus[agent] === 'running'}
          />
        ))}

        {isComplete && (
          <div className="rounded-xl bg-green-500/10 border border-green-500/30 px-4 py-3 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-green-400">Analysis Complete</p>
              <p className="text-xs text-slate-400 mt-0.5">Switch to the tabs above to explore results</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
