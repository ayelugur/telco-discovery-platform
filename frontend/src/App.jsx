import { useEffect, useState } from 'react'
import { Network, Map, ShieldAlert, GitBranch, Terminal, Zap } from 'lucide-react'
import { useAnalysis } from './hooks/useAnalysis'
import { Sidebar } from './components/Sidebar'
import { AgentStream } from './components/AgentStream'
import { KnowledgeGraph } from './components/KnowledgeGraph'
import { ApplicationMap } from './components/ApplicationMap'
import { RiskHeatmap } from './components/RiskHeatmap'
import { MigrationRoadmap } from './components/MigrationRoadmap'

const TABS = [
  { id: 'console',  label: 'Agent Console',    icon: Terminal,    result: null },
  { id: 'graph',    label: 'Knowledge Graph',   icon: Network,     result: 'discovery' },
  { id: 'appmap',   label: 'Application Map',   icon: Map,         result: 'discovery' },
  { id: 'risk',     label: 'Risk Heatmap',      icon: ShieldAlert, result: 'risk' },
  { id: 'roadmap',  label: 'Migration Roadmap', icon: GitBranch,   result: 'roadmap' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('console')
  const analysis = useAnalysis()

  useEffect(() => { analysis.loadAssets() }, [])

  // Auto-switch to graph tab when analysis finishes
  useEffect(() => {
    if (analysis.isComplete) {
      setTimeout(() => setActiveTab('graph'), 500)
    }
  }, [analysis.isComplete])

  // Tab is unlocked if it needs no result, OR if we have that result
  const isUnlocked = (tab) => {
    if (!tab.result) return true
    return !!analysis.results[tab.result]
  }

  return (
    <div className="flex flex-col h-screen bg-surface-900 overflow-hidden">

      {/* Top bar */}
      <header className="bg-surface-800 border-b border-slate-700 px-6 py-3 flex items-center gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100 leading-none">Telco Discovery Platform</h1>
            <p className="text-xs text-slate-500 mt-0.5">Autonomous OSS/BSS Transformation Intelligence</p>
          </div>
        </div>

        {/* Tab nav */}
        <nav className="flex items-center gap-1 ml-8 bg-surface-900 rounded-xl p-1">
          {TABS.map(tab => {
            const Icon = tab.icon
            const unlocked = isUnlocked(tab)
            const isActive = activeTab === tab.id
            return (
              <button key={tab.id}
                onClick={() => unlocked && setActiveTab(tab.id)}
                disabled={!unlocked}
                title={!unlocked ? 'Run analysis to unlock' : ''}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium
                  transition-all duration-200 whitespace-nowrap
                  ${isActive
                    ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
                    : unlocked
                      ? 'text-slate-400 hover:text-slate-200 hover:bg-surface-700'
                      : 'text-slate-700 cursor-not-allowed'}`}>
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
                {unlocked && tab.result && (
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                )}
              </button>
            )
          })}
        </nav>

        {/* Status */}
        <div className="ml-auto flex items-center gap-3">
          {analysis.isRunning && (
            <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-400/10
              border border-yellow-400/20 rounded-lg px-3 py-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
              Agents Running
            </div>
          )}
          {analysis.isComplete && (
            <div className="flex items-center gap-2 text-xs text-green-400 bg-green-400/10
              border border-green-400/20 rounded-lg px-3 py-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Analysis Complete
            </div>
          )}
          <div className="text-xs text-slate-600 font-mono">{analysis.assets.length} assets loaded</div>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          assets={analysis.assets}
          onUpload={analysis.uploadAsset}
          onRemove={analysis.removeAsset}
          onReset={analysis.reset}
          isRunning={analysis.isRunning}
        />

        <main className="flex-1 overflow-hidden p-5">

          {activeTab === 'console' && (
            <AgentStream
              AGENTS={analysis.AGENTS}
              AGENT_LABELS={analysis.AGENT_LABELS}
              agentStatus={analysis.agentStatus}
              agentLogs={analysis.agentLogs}
              isRunning={analysis.isRunning}
              isComplete={analysis.isComplete}
              onRun={analysis.runAnalysis}
            />
          )}

          {activeTab === 'graph' && (
            <div className="h-full flex flex-col">
              <h2 className="text-lg font-bold text-slate-100 mb-3 flex items-center gap-2">
                <Network className="w-5 h-5 text-brand-400" /> Knowledge Graph
                <span className="text-xs text-slate-500 font-normal ml-1">— Click nodes and edges to explore</span>
              </h2>
              <div className="flex-1 min-h-0">
                <KnowledgeGraph data={analysis.results.discovery} />
              </div>
            </div>
          )}

          {activeTab === 'appmap' && (
            <div className="h-full flex flex-col">
              <h2 className="text-lg font-bold text-slate-100 mb-3 flex items-center gap-2">
                <Map className="w-5 h-5 text-brand-400" /> Application Map
                <span className="text-xs text-slate-500 font-normal ml-1">— Functional domain health</span>
              </h2>
              <div className="flex-1 min-h-0 overflow-y-auto">
                <ApplicationMap data={analysis.results.discovery} />
              </div>
            </div>
          )}

          {activeTab === 'risk' && (
            <div className="h-full flex flex-col">
              <h2 className="text-lg font-bold text-slate-100 mb-3 flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-brand-400" /> Risk Heatmap
                <span className="text-xs text-slate-500 font-normal ml-1">— Click cells to see findings</span>
              </h2>
              <div className="flex-1 min-h-0">
                <RiskHeatmap data={analysis.results.risk} />
              </div>
            </div>
          )}

          {activeTab === 'roadmap' && (
            <div className="h-full flex flex-col">
              <h2 className="text-lg font-bold text-slate-100 mb-3 flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-brand-400" /> Migration Roadmap
                <span className="text-xs text-slate-500 font-normal ml-1">— Phased wave plan</span>
              </h2>
              <div className="flex-1 min-h-0">
                <MigrationRoadmap
                  data={analysis.results.roadmap}
                  aiData={analysis.results.ai_opportunities}
                />
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
