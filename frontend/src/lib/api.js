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
        const response = await fetch(`${BASE}/api/analyze/full`, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
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

          // Split on double newlines (SSE message separator)
          const messages = buffer.split('\n\n')
          buffer = messages.pop() // keep incomplete last chunk

          for (const message of messages) {
            const trimmed = message.trim()
            if (!trimmed || trimmed.startsWith(':')) continue // skip keepalives

            // Find the data line
            const lines = trimmed.split('\n')
            const dataLine = lines.find(l => l.startsWith('data: '))
            if (!dataLine) continue

            const jsonStr = dataLine.slice(6).trim()
            if (!jsonStr) continue

            try {
              const data = JSON.parse(jsonStr)
              console.log('[SSE]', data.event, data.agent || '')

              switch (data.event) {
                case 'agent_start':
                  callbacks.onAgentStart?.(data.agent, data.label)
                  break
                case 'chunk':
                  // Only show chunk in console, don't display raw JSON in UI
                  callbacks.onChunk?.(data.agent, data.text)
                  break
                case 'result':
                  console.log('[SSE] result data keys:', Object.keys(data.data || {}))
                  callbacks.onResult?.(data.agent, data.data)
                  break
                case 'agent_done':
                  callbacks.onAgentDone?.(data.agent)
                  break
                case 'error':
                  callbacks.onError?.(data.agent, data.message)
                  break
                case 'analysis_complete':
                  callbacks.onComplete?.()
                  return
              }
            } catch (parseErr) {
              console.warn('[SSE] parse error:', parseErr.message, 'raw:', jsonStr.slice(0, 100))
            }
          }
        }

        if (!cancelled) callbacks.onComplete?.()

      } catch (err) {
        if (!cancelled) {
          console.error('[SSE] fetch error:', err)
          callbacks.onError?.('stream', err.message || 'Connection failed')
        }
      }
    }

    run()
    return () => { cancelled = true }
  }
}
