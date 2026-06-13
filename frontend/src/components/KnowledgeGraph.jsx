import { useEffect, useRef, useState } from 'react'
import { Network } from 'vis-network'
import { DataSet } from 'vis-data'
import { Info, X } from 'lucide-react'

const DOMAIN_COLORS = {
  CRM: { bg: '#0ea5e9', border: '#0284c7' },
  Billing: { bg: '#f97316', border: '#ea580c' },
  Provisioning: { bg: '#a855f7', border: '#9333ea' },
  Inventory: { bg: '#22c55e', border: '#16a34a' },
  Assurance: { bg: '#ef4444', border: '#dc2626' },
  Integration: { bg: '#eab308', border: '#ca8a04' },
  default: { bg: '#64748b', border: '#475569' },
}

const TYPE_SHAPES = {
  system: 'box',
  domain: 'ellipse',
  database: 'database',
  api: 'diamond',
  batch_job: 'hexagon',
}

const EDGE_COLORS = {
  sync_rest: '#0ea5e9',
  sync_soap: '#f97316',
  db_link: '#ef4444',
  batch_file: '#eab308',
  event: '#22c55e',
  async_rest: '#a855f7',
}

export function KnowledgeGraph({ data }) {
  const containerRef = useRef()
  const networkRef = useRef()
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    if (!data || !containerRef.current) return

    const nodes = new DataSet(data.nodes.map(n => {
      const colors = DOMAIN_COLORS[n.domain] || DOMAIN_COLORS.default
      const statusBorder = n.status === 'critical' ? '#ef4444'
        : n.status === 'at_risk' ? '#f97316' : colors.border

      return {
        id: n.id,
        label: n.label,
        shape: TYPE_SHAPES[n.type] || 'box',
        color: { background: colors.bg + '33', border: statusBorder, highlight: { background: colors.bg + '66', border: statusBorder } },
        font: { color: '#e2e8f0', size: 12, face: 'Inter' },
        borderWidth: n.status === 'critical' ? 3 : 2,
        data: n,
      }
    }))

    const edges = new DataSet(data.edges.map((e, i) => ({
      id: i,
      from: e.from_id,
      to: e.to_id,
      label: e.label,
      color: { color: EDGE_COLORS[e.type] || '#64748b', opacity: e.risk === 'critical' ? 1 : 0.7 },
      width: e.risk === 'critical' ? 3 : e.risk === 'high' ? 2 : 1,
      dashes: e.type === 'batch_file',
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      font: { color: '#94a3b8', size: 9, face: 'Inter', strokeWidth: 2, strokeColor: '#0f172a' },
      smooth: { type: 'curvedCW', roundness: 0.2 },
      data: e,
    })))

    const options = {
      layout: { improvedLayout: true },
      physics: {
        enabled: true,
        stabilization: { iterations: 150 },
        barnesHut: { gravitationalConstant: -8000, springConstant: 0.04, damping: 0.09 },
      },
      interaction: { hover: true, tooltipDelay: 200, zoomView: true, dragView: true },
      nodes: { margin: 8 },
      edges: { smooth: true },
    }

    networkRef.current = new Network(containerRef.current, { nodes, edges }, options)

    networkRef.current.on('click', ({ nodes: clickedNodes, edges: clickedEdges }) => {
      if (clickedNodes.length > 0) {
        const node = data.nodes.find(n => n.id === clickedNodes[0])
        setSelected({ type: 'node', data: node })
      } else if (clickedEdges.length > 0) {
        const edge = data.edges[clickedEdges[0]]
        setSelected({ type: 'edge', data: edge })
      } else {
        setSelected(null)
      }
    })

    return () => { networkRef.current?.destroy() }
  }, [data])

  if (!data) return <EmptyState />

  return (
    <div className="h-full flex gap-4">
      <div className="flex-1 relative">
        <div ref={containerRef} className="w-full h-full rounded-xl bg-surface-900 border border-slate-700" />

        {/* Legend */}
        <div className="absolute bottom-3 left-3 bg-surface-800/90 backdrop-blur rounded-lg p-3 border border-slate-700">
          <p className="text-xs font-semibold text-slate-400 mb-2">Edge Types</p>
          <div className="space-y-1">
            {Object.entries(EDGE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="w-6 h-0.5 rounded" style={{ backgroundColor: color }} />
                <span className="text-xs text-slate-500 capitalize">{type.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Node detail panel */}
      {selected && (
        <div className="w-72 bg-surface-800 rounded-xl border border-slate-700 p-4 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Info className="w-4 h-4 text-brand-400" />
              {selected.type === 'node' ? 'System Node' : 'Integration Edge'}
            </h3>
            <button onClick={() => setSelected(null)} className="text-slate-500 hover:text-slate-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          {selected.type === 'node' && (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500">Name</p>
                <p className="text-sm text-slate-200 font-medium">{selected.data.label}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Domain</p>
                <p className="text-sm text-slate-200">{selected.data.domain || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Type</p>
                <p className="text-sm text-slate-200 capitalize">{selected.data.type}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Status</p>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                  selected.data.status === 'critical' ? 'bg-red-500/20 text-red-400' :
                  selected.data.status === 'at_risk' ? 'bg-orange-500/20 text-orange-400' :
                  'bg-green-500/20 text-green-400'}`}>
                  {selected.data.status || 'unknown'}
                </span>
              </div>
            </div>
          )}

          {selected.type === 'edge' && (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500">Integration</p>
                <p className="text-sm text-slate-200 font-medium">{selected.data.label}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Type</p>
                <p className="text-sm text-slate-200 capitalize">{selected.data.type?.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Risk Level</p>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                  selected.data.risk === 'critical' ? 'bg-red-500/20 text-red-400' :
                  selected.data.risk === 'high' ? 'bg-orange-500/20 text-orange-400' :
                  selected.data.risk === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                  'bg-green-500/20 text-green-400'}`}>
                  {selected.data.risk || 'low'}
                </span>
              </div>
            </div>
          )}
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
          <Info className="w-8 h-8 text-slate-600" />
        </div>
        <p className="text-slate-400 font-medium">No graph data yet</p>
        <p className="text-slate-600 text-sm mt-1">Run the analysis to generate the knowledge graph</p>
      </div>
    </div>
  )
}
