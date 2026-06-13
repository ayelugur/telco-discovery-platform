const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = {
  async getAssets() {
    const r = await fetch(`${BASE}/api/assets`)
    return r.json()
  },

  async uploadAsset(file) {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`${BASE}/api/assets/upload`, { method: 'POST', body: fd })
    return r.json()
  },

  async removeAsset(filename) {
    const r = await fetch(`${BASE}/api/assets/${encodeURIComponent(filename)}`, { method: 'DELETE' })
    return r.json()
  },

  async reset() {
    const r = await fetch(`${BASE}/api/reset`, { method: 'POST' })
    return r.json()
  },

  async getState() {
    const r = await fetch(`${BASE}/api/state`)
    return r.json()
  },

  streamFullAnalysis(callbacks) {
    let cancelled = false

    const run = async () => {
      try {
        // Use fetch instead of EventSource — gives us full control over
        // headers, timeouts, and streaming, and works reliably through Railway
        const response = await fetch(`${BASE}/api/analyze/full`, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          // No timeout — analysis can take 2-3 minutes
        })

        if (!response.ok) {
          callbacks.onError?.('stream', `HTTP ${response.status}: ${response.statusText}`)
          return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          if (cancelled) break

          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // SSE messages are separated by double newlines
          const messages = buffer.split('\n\n')
          buffer = messages.pop() // last item may be incomplete

          for (const message of messages) {
            const trimmed = message.trim()
            if (!trimmed || trimmed.startsWith(':')) continue // skip keepalive comments

            // Parse "data: {...}" lines
            const dataLine = trimmed.split('\n').find(l => l.startsWith('data: '))
            if (!dataLine) continue

            try {
              const data = JSON.parse(dataLine.slice(6)) // strip "data: "
              switch (data.event) {
                case 'agent_start':      callbacks.onAgentStart?.(data.agent, data.label); break
                case 'chunk':            callbacks.onChunk?.(data.agent, data.text); break
                case 'result':           callbacks.onResult?.(data.agent, data.data); break
                case 'agent_done':       callbacks.onAgentDone?.(data.agent); break
                case 'error':            callbacks.onError?.(data.agent, data.message); break
                case 'analysis_complete': callbacks.onComplete?.(); return
              }
            } catch (parseErr) {
              console.warn('SSE parse error:', parseErr, 'raw:', dataLine)
            }
          }
        }

        // Stream ended without analysis_complete — treat as complete
        if (!cancelled) callbacks.onComplete?.()

      } catch (err) {
        if (!cancelled) {
          console.error('Stream fetch error:', err)
          callbacks.onError?.('stream', err.message || 'Connection failed')
        }
      }
    }

    run()

    // Return cancel function
    return () => { cancelled = true }
  }
}
