import { Activity, AlertTriangle, CheckCircle, XCircle, Server, Globe, Database } from 'lucide-react'

const DOMAIN_GRADIENTS = {
  CRM:          'from-blue-600/20 to-blue-900/10 border-blue-500/30',
  Billing:      'from-orange-600/20 to-orange-900/10 border-orange-500/30',
  Provisioning: 'from-purple-600/20 to-purple-900/10 border-purple-500/30',
  Inventory:    'from-green-600/20 to-green-900/10 border-green-500/30',
  Assurance:    'from-red-600/20 to-red-900/10 border-red-500/30',
  Integration:  'from-yellow-600/20 to-yellow-900/10 border-yellow-500/30',
}

const DOMAIN_ACCENT = {
  CRM: 'text-blue-400',
  Billing: 'text-orange-400',
  Provisioning: 'text-purple-400',
  Inventory: 'text-green-400',
  Assurance: 'text-red-400',
  Integration: 'text-yellow-400',
}

function HealthBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="w-full bg-slate-700 rounded-full h-1.5 mt-1">
      <div className={`h-1.5 rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${score}%` }} />
    </div>
  )
}

function HealthBadge({ score }) {
  if (score >= 70) return <span className="flex items-center gap-1 text-xs text-green-400"><CheckCircle className="w-3 h-3" /> Healthy</span>
  if (score >= 40) return <span className="flex items-center gap-1 text-xs text-yellow-400"><AlertTriangle className="w-3 h-3" /> At Risk</span>
  return <span className="flex items-center gap-1 text-xs text-red-400"><XCircle className="w-3 h-3" /> Critical</span>
}

function DomainCard({ domain }) {
  const gradient = DOMAIN_GRADIENTS[domain.name] || 'from-slate-600/20 to-slate-900/10 border-slate-500/30'
  const accent = DOMAIN_ACCENT[domain.name] || 'text-slate-400'
  const score = domain.health_score ?? 50

  return (
    <div className={`bg-gradient-to-br ${gradient} border rounded-2xl p-5 flex flex-col gap-4`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className={`text-base font-bold ${accent}`}>{domain.name}</h3>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-xs text-slate-500">{(domain.systems || []).join(', ')}</p>
          </div>
        </div>
        <HealthBadge score={score} />
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 gap-3">
        <Metric icon={Database} label="Entities" value={domain.entity_count ?? '—'} accent={accent} />
        <Metric icon={Globe} label="APIs" value={domain.api_surface ?? '—'} accent={accent} />
        <Metric icon={Server} label="Systems" value={(domain.systems || []).length} accent={accent} />
      </div>

      {/* Health score */}
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-slate-500">Health Score</span>
          <span className={`font-mono font-bold ${accent}`}>{score}/100</span>
        </div>
        <HealthBar score={score} />
      </div>

      {/* Issues */}
      {domain.primary_issues?.length > 0 && (
        <div className="space-y-1">
          {domain.primary_issues.slice(0, 3).map((issue, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <AlertTriangle className="w-3 h-3 text-yellow-500 mt-0.5 shrink-0" />
              <p className="text-xs text-slate-400 leading-snug">{issue}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Metric({ icon: Icon, label, value, accent }) {
  return (
    <div className="bg-black/20 rounded-lg p-2 text-center">
      <Icon className={`w-3.5 h-3.5 ${accent} mx-auto mb-1`} />
      <p className={`text-sm font-bold ${accent}`}>{value}</p>
      <p className="text-xs text-slate-600">{label}</p>
    </div>
  )
}

export function ApplicationMap({ data }) {
  if (!data?.domains?.length) return <EmptyState />

  const summary = data.summary

  return (
    <div className="h-full flex flex-col gap-4 overflow-y-auto pr-1">
      {summary && (
        <div className="bg-surface-800 border border-slate-700 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-brand-400" />
            <h3 className="text-sm font-semibold text-slate-200">Discovery Summary</h3>
          </div>
          <p className="text-sm text-slate-400 leading-relaxed">{summary}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {data.domains.map((domain, i) => (
          <DomainCard key={i} domain={domain} />
        ))}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-surface-700 flex items-center justify-center mx-auto mb-4">
          <Activity className="w-8 h-8 text-slate-600" />
        </div>
        <p className="text-slate-400 font-medium">No domain data yet</p>
        <p className="text-slate-600 text-sm mt-1">Run the analysis to map functional domains</p>
      </div>
    </div>
  )
}
