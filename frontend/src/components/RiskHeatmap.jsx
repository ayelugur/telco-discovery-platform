import { useState } from 'react'
import { X, ShieldAlert, AlertTriangle, Info } from 'lucide-react'

const SEVERITY_COLORS = {
  critical: { bg: 'bg-red-600',    text: 'text-red-100',    border: 'border-red-500',    dot: 'bg-red-400' },
  high:     { bg: 'bg-orange-500', text: 'text-orange-100', border: 'border-orange-500', dot: 'bg-orange-400' },
  medium:   { bg: 'bg-yellow-500', text: 'text-yellow-100', border: 'border-yellow-500', dot: 'bg-yellow-400' },
  low:      { bg: 'bg-green-600',  text: 'text-green-100',  border: 'border-green-500',  dot: 'bg-green-400' },
}

const SCORE_TO_SEVERITY = (score) => {
  if (score >= 8) return 'critical'
  if (score >= 6) return 'high'
  if (score >= 3) return 'medium'
  return 'low'
}

const SCORE_CELL_COLOR = (score) => {
  if (score >= 8) return 'bg-red-600/80 hover:bg-red-500/90 border-red-500/50'
  if (score >= 6) return 'bg-orange-500/70 hover:bg-orange-400/80 border-orange-500/50'
  if (score >= 3) return 'bg-yellow-500/50 hover:bg-yellow-400/60 border-yellow-500/40'
  if (score > 0)  return 'bg-green-600/30 hover:bg-green-500/40 border-green-600/30'
  return 'bg-slate-800/50 border-slate-700/30'
}

function RiskDetailDrawer({ riskItems, cell, onClose }) {
  if (!cell) return null
  const items = riskItems.filter(r =>
    r.system === cell.system && r.category === cell.category
  )

  return (
    <div className="w-96 bg-surface-800 border-l border-slate-700 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">{cell.system}</h3>
          <p className="text-xs text-slate-500">{cell.category}</p>
        </div>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No risk items for this cell</p>
        ) : items.map((item) => {
          const sev = SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.low
          return (
            <div key={item.id} className={`rounded-xl border ${sev.border} bg-surface-700 overflow-hidden`}>
              <div className={`px-3 py-2 ${sev.bg} flex items-center gap-2`}>
                <ShieldAlert className={`w-3.5 h-3.5 ${sev.text} shrink-0`} />
                <span className={`text-xs font-bold ${sev.text} uppercase tracking-wide`}>{item.severity}</span>
                <span className="text-xs text-white/60 ml-auto font-mono">{item.id}</span>
              </div>
              <div className="p-3 space-y-2">
                <p className="text-sm font-semibold text-slate-200">{item.title}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>
                <div className="pt-2 border-t border-slate-700">
                  <p className="text-xs text-slate-500 font-semibold mb-1">IMPACT</p>
                  <p className="text-xs text-slate-400">{item.impact}</p>
                </div>
                <div className="pt-2 border-t border-slate-700">
                  <p className="text-xs text-slate-500 font-semibold mb-1">RECOMMENDATION</p>
                  <p className="text-xs text-brand-400">{item.recommendation}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function RiskHeatmap({ data }) {
  const [selectedCell, setSelectedCell] = useState(null)

  if (!data?.heatmap?.length) return <EmptyState />

  // Build grid dimensions from heatmap data
  const systems = [...new Set(data.heatmap.map(h => h.system))]
  const categories = [...new Set(data.heatmap.map(h => h.category))]

  const getCell = (system, category) =>
    data.heatmap.find(h => h.system === system && h.category === category)

  const overallSev = SCORE_TO_SEVERITY(data.overall_risk_score / 10)
  const overallColors = SEVERITY_COLORS[overallSev]

  return (
    <div className="h-full flex gap-0 overflow-hidden">
      <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-4">
        {/* Overall risk score */}
        <div className="flex items-center gap-4 bg-surface-800 rounded-xl border border-slate-700 p-4">
          <div className={`w-16 h-16 rounded-xl ${overallColors.bg} flex items-center justify-center shrink-0`}>
            <span className={`text-xl font-black ${overallColors.text}`}>{data.overall_risk_score}</span>
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-slate-200">Overall Risk Score</p>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${overallColors.bg} ${overallColors.text} uppercase`}>
                {overallSev}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">{data.summary}</p>
          </div>
        </div>

        {/* Heatmap grid */}
        <div className="bg-surface-800 rounded-xl border border-slate-700 p-4 overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="text-xs text-slate-500 font-medium text-left p-2 w-36">Category ↓ / System →</th>
                {systems.map(sys => (
                  <th key={sys} className="text-xs text-slate-400 font-semibold p-2 text-center min-w-28">
                    {sys}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {categories.map(cat => (
                <tr key={cat}>
                  <td className="text-xs text-slate-400 font-medium p-2 pr-4 whitespace-nowrap">{cat}</td>
                  {systems.map(sys => {
                    const cell = getCell(sys, cat)
                    const score = cell?.score ?? 0
                    const cellColor = SCORE_CELL_COLOR(score)
                    const isSelected = selectedCell?.system === sys && selectedCell?.category === cat

                    return (
                      <td key={sys} className="p-1">
                        <button
                          onClick={() => setSelectedCell(
                            isSelected ? null : { system: sys, category: cat }
                          )}
                          className={`w-full rounded-lg border p-2 transition-all duration-200 text-center
                            ${cellColor} ${isSelected ? 'ring-2 ring-white/30' : ''}`}>
                          <span className="text-xs font-bold text-white/90 block">{score}</span>
                          {cell?.label && (
                            <span className="text-xs text-white/60 block truncate">{cell.label}</span>
                          )}
                        </button>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Score legend */}
          <div className="flex items-center gap-4 mt-4 pt-3 border-t border-slate-700">
            <span className="text-xs text-slate-500">Score:</span>
            {[{ label: '0-2 Low', color: 'bg-green-600/40' }, { label: '3-5 Medium', color: 'bg-yellow-500/50' },
              { label: '6-7 High', color: 'bg-orange-500/70' }, { label: '8-10 Critical', color: 'bg-red-600/80' }
            ].map(({ label, color }) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className={`w-4 h-4 rounded ${color}`} />
                <span className="text-xs text-slate-500">{label}</span>
              </div>
            ))}
            <span className="text-xs text-slate-600 ml-auto flex items-center gap-1">
              <Info className="w-3 h-3" /> Click a cell to see findings
            </span>
          </div>
        </div>

        {/* Risk item list */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
            All Risk Items ({data.risk_items?.length || 0})
          </h3>
          {data.risk_items?.map(item => {
            const sev = SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.low
            return (
              <div key={item.id} className="bg-surface-800 border border-slate-700 rounded-lg px-4 py-3
                flex items-start gap-3 hover:border-slate-600 transition-colors">
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${sev.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-500">{item.id}</span>
                    <span className={`text-xs font-semibold ${sev.text.replace('100', '400')}`}>{item.severity.toUpperCase()}</span>
                    <span className="text-xs text-slate-500">— {item.system} / {item.category}</span>
                  </div>
                  <p className="text-sm text-slate-200 font-medium mt-0.5">{item.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{item.description}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Side drawer */}
      {selectedCell && (
        <RiskDetailDrawer
          riskItems={data.risk_items || []}
          cell={selectedCell}
          onClose={() => setSelectedCell(null)}
        />
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-surface-700 flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-8 h-8 text-slate-600" />
        </div>
        <p className="text-slate-400 font-medium">No risk data yet</p>
        <p className="text-slate-600 text-sm mt-1">Run the analysis to generate the risk heatmap</p>
      </div>
    </div>
  )
}
