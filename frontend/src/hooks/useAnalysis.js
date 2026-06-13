import { useState, useCallback, useRef } from 'react'
import { api } from '../lib/api'

const AGENTS = ['discovery', 'risk', 'ai_opportunities', 'roadmap']

const AGENT_LABELS = {
  discovery: 'Discovery & Dependency Mapping',
  risk: 'Risk & Architecture Analysis',
  ai_opportunities: 'AI Opportunity Identification',
  roadmap: 'Migration Roadmap Generation',
}

export function useAnalysis() {
  const [assets, setAssets] = useState([])
  const [agentStatus, setAgentStatus] = useState({}) // idle | running | done | error
  const [agentLogs, setAgentLogs] = useState({})     // agent -> text chunks
  const [results, setResults] = useState({})          // agent -> parsed data
  const [isRunning, setIsRunning] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [activeAgent, setActiveAgent] = useState(null)
  const closeStream = useRef(null)

  const loadAssets = useCallback(async () => {
    const data = await api.getAssets()
    setAssets(data.assets || [])
  }, [])

  const uploadAsset = useCallback(async (file) => {
    await api.uploadAsset(file)
    await loadAssets()
  }, [loadAssets])

  const removeAsset = useCallback(async (filename) => {
    await api.removeAsset(filename)
    await loadAssets()
  }, [loadAssets])

  const reset = useCallback(async () => {
    if (closeStream.current) closeStream.current()
    await api.reset()
    setAgentStatus({})
    setAgentLogs({})
    setResults({})
    setIsRunning(false)
    setIsComplete(false)
    setActiveAgent(null)
    await loadAssets()
  }, [loadAssets])

  const runAnalysis = useCallback(() => {
    if (isRunning) return
    setIsRunning(true)
    setIsComplete(false)
    setAgentStatus({})
    setAgentLogs({})
    setResults({})
    setActiveAgent(null)

    closeStream.current = api.streamFullAnalysis({
      onAgentStart: (agent) => {
        setActiveAgent(agent)
        setAgentStatus(s => ({ ...s, [agent]: 'running' }))
        setAgentLogs(l => ({ ...l, [agent]: '' }))
      },
      onChunk: (agent, text) => {
        setAgentLogs(l => ({ ...l, [agent]: (l[agent] || '') + text }))
      },
      onResult: (agent, data) => {
        setResults(r => ({ ...r, [agent]: data }))
      },
      onAgentDone: (agent) => {
        setAgentStatus(s => ({ ...s, [agent]: 'done' }))
      },
      onError: (agent, message) => {
        setAgentStatus(s => ({ ...s, [agent]: 'error' }))
        console.error(`Agent ${agent} error:`, message)
      },
      onComplete: () => {
        setIsRunning(false)
        setIsComplete(true)
        setActiveAgent(null)
      }
    })
  }, [isRunning])

  return {
    assets, loadAssets, uploadAsset, removeAsset,
    agentStatus, agentLogs, results,
    isRunning, isComplete, activeAgent,
    runAnalysis, reset,
    AGENTS, AGENT_LABELS,
  }
}
