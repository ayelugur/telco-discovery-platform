import { useState } from 'react'
import { ChevronDown, ChevronUp, Zap, Users, Clock, DollarSign, AlertTriangle, CheckCircle, Sparkles } from 'lucide-react'

const WAVE_COLORS = {
  1: { accent: 'text-green-400',  border: 'border-green-500/40',  bg: 'bg-green-500/10',  bar: 'bg-green-500',  badge: 'bg-green-500/20 text-green-300' },
  2: { accent: 'text-blue-400',   border: 'border-blue-500/40',   bg: 'bg-blue-500/10',   bar: 'bg-blue-500',   badge: 'bg-blue-500/20 text-blue-300' },
  3: { accent: 'text-purple-400', border: 'border-purple-500/40', bg: 'bg-purple-500/10', bar: 'bg-purple-500', badge: 'bg-purple-500/20 text-purple-300' },
}

function WaveCard({ wave, aiOpportunities, totalDuration }) {
  const [expanded, setExpanded] = useState(wave.wave_number === 1)
  const colors = WAVE_COLORS[wave.wave_number] || WAVE_COLORS[1]

  // Find AI opps for this wave
  const waveOpps = aiOpportunities?.filter(o => o.wave === wave.wave_number) || []

  const widthPct = Math.round((wave.duration_months / totalDuration) * 100)

  return (
    <div className={`rounded-2xl border ${colors.border} overflow-hidden`}>
      {/* Wave header */}
      <div className={`${colors.bg} px-5 py-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg ${colors.bar} flex items-center justify-center`}>
              <span className="text-white font-black text-sm">{wave.wave_number}</span>
            </div>
            <div>
              <h3 className={`font-bold text-base ${colors.accent}`}>Wave {wave.wave_number}: {wave.name}</h3>
              <p className="text-xs text-slate-500">{wave.domains.join(' · ')}</p>
            </div>
          </div>
          <button onClick={() => setExpanded(e => !e)}
            className="text-slate-500 hover:text-slate-300 transition-colors">
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>

        {/* Timeline bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Duration</span>
            <span className={`font-semibold ${colors.accent}`}>{wave.duration_months} months</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2">
            <div className={`h-2 rounded-full ${colors.bar} transition-all duration-700`}
              style={{ width: `${widthPct}%` }} />
          </div>
        </div>

        {/* Metrics row */}
        <div className="grid grid-cols-4 gap-3 mt-3">
          <WaveMetric icon={Clock} label="Duration" value={`${wave.duration_months}mo`} color={colors.accent} />
          <WaveMetric icon={Users} label="Team" value={`${wave.team_size} FTE`} color={colors.accent} />
          <WaveMetric icon={DollarSign} label="Cost" value={wave.cost_range_usd} color={colors.accent} small />
          <WaveMetric icon={Zap} label="Effort" value={`${wave.effort_person_months}pm`} color={colors.accent} />
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-5 py-4 space-y-4 bg-surface-800">

          {/* Systems */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Systems in Scope</p>
            <div className="flex flex-wrap gap-2">
              {wave.systems.map((s, i) => (
                <span key={i} className={`text-xs px-2.5 py-1 rounded-full ${colors.badge} font-medium`}>{s}</span>
              ))}
            </div>
          </div>

          {/* Team composition */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Team Composition</p>
            <div className="grid grid-cols-2 gap-1.5">
              {wave.team_composition.map((role, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-400">
                  <div className={`w-1.5 h-1.5 rounded-full ${colors.bar}`} />
                  {role}
                </div>
              ))}
            </div>
          </div>

          {/* Milestones */}
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Key Milestones</p>
            <div className="space-y-1.5">
              {wave.key_milestones.map((m, i) => (
                <div key={i} className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-green-500 mt-0.5 shrink-0" />
                  <span className="text-xs text-slate-300">{m}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dependencies */}
          {wave.dependencies?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Dependencies</p>
              <div className="space-y-1.5">
                {wave.dependencies.map((d, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 shrink-0" />
                    <span className="text-xs text-slate-400">{d}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* AI Opportunities */}
          {waveOpps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-yellow-400" /> AI Opportunities
              </p>
              <div className="space-y-2">
                {waveOpps.map(opp => (
                  <div key={opp.id} className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-yellow-600">{opp.id}</span>
                      <span className="text-xs font-semibold text-yellow-300">{opp.title}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">{opp.description}</p>
                    <div className="flex items-center gap-3 mt-1.5">
                      <span className="text-xs text-slate-500">{opp.domain}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        opp.effort === 'low' ? 'bg-green-500/20 text-green-400' :
                        opp.effort === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-red-500/20 text-red-400'}`}>
                        {opp.effort} effort
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function WaveMetric({ icon: Icon, label, value, color, small }) {
  return (
    <div className="bg-black/20 rounded-lg p-2 text-center">
      <Icon className={`w-3 h-3 ${color} mx-auto mb-0.5`} />
      <p className={`font-bold ${color} ${small ? 'text-xs' : 'text-sm'} leading-tight`}>{value}</p>
      <p className="text-xs text-slate-600">{label}</p>
    </div>
  )
}

export function MigrationRoadmap({ data, aiData }) {
  if (!data?.waves?.length) return <EmptyState />

  const aiOpportunities = aiData?.opportunities || []

  return (
    <div className="h-full overflow-y-auto pr-1 space-y-4">
      {/* Header summary */}
      <div className="bg-surface-800 border border-slate-700 rounded-xl p-4 grid grid-cols-3 gap-4">
        <div className="text-center">
          <p className="text-2xl font-black text-slate-100">{data.total_duration_months}</p>
          <p className="text-xs text-slate-500">Total Months</p>
        </div>
        <div className="text-center border-x border-slate-700">
          <p className="text-lg font-black text-slate-100">{data.total_cost_range_usd}</p>
          <p className="text-xs text-slate-500">Total Investment</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-black text-slate-100">{data.waves.length}</p>
          <p className="text-xs text-slate-500">Migration Waves</p>
        </div>
      </div>

      {/* Target architecture */}
      {data.target_architecture && (
        <div className="bg-brand-600/10 border border-brand-600/30 rounded-xl p-4">
          <p className="text-xs font-semibold text-brand-400 uppercase tracking-wide mb-1">Target Architecture</p>
          <p className="text-sm text-slate-300 leading-relaxed">{data.target_architecture}</p>
        </div>
      )}

      {/* Quick wins */}
      {data.quick_wins?.length > 0 && (
        <div className="bg-surface-800 border border-slate-700 rounded-xl p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-yellow-400" /> 90-Day Quick Wins
          </p>
          <div className="grid grid-cols-2 gap-2">
            {data.quick_wins.map((win, i) => (
              <div key={i} className="flex items-start gap-2 bg-yellow-500/10 rounded-lg px-3 py-2">
                <CheckCircle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 shrink-0" />
                <span className="text-xs text-slate-300">{win}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wave cards */}
      {data.waves.map(wave => (
        <WaveCard
          key={wave.wave_number}
          wave={wave}
          aiOpportunities={aiOpportunities}
          totalDuration={data.total_duration_months}
        />
      ))}

      {data.summary && (
        <div className="bg-surface-800 border border-slate-700 rounded-xl p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Program Summary</p>
          <p className="text-sm text-slate-400 leading-relaxed">{data.summary}</p>
        </div>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-surface-700 flex items-center justify-center mx-auto mb-4">
          <Zap className="w-8 h-8 text-slate-600" />
        </div>
        <p className="text-slate-400 font-medium">No roadmap yet</p>
        <p className="text-slate-600 text-sm mt-1">Run the analysis to generate the migration roadmap</p>
      </div>
    </div>
  )
}
