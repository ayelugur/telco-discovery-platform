import { useRef } from 'react'
import { Upload, FileCode, FileJson, FileText, Database, X, RefreshCw } from 'lucide-react'

const TYPE_ICON = {
  swagger: FileCode,
  sql_schema: Database,
  json_schema: FileJson,
  ticket_log: FileText,
  jil_schedule: FileText,
  unknown: FileText,
}

const TYPE_COLOR = {
  swagger: 'text-blue-400',
  sql_schema: 'text-orange-400',
  json_schema: 'text-green-400',
  ticket_log: 'text-red-400',
  jil_schedule: 'text-purple-400',
  unknown: 'text-slate-400',
}

const TYPE_LABEL = {
  swagger: 'Swagger',
  sql_schema: 'SQL Schema',
  json_schema: 'JSON Schema',
  ticket_log: 'Ticket Log',
  jil_schedule: 'JIL Schedule',
  unknown: 'Unknown',
}

export function Sidebar({ assets, onUpload, onRemove, onReset, isRunning }) {
  const fileRef = useRef()

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) onUpload(file)
  }

  return (
    <aside className="w-72 bg-surface-800 border-r border-slate-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Asset Inventory</h2>
          <span className="text-xs bg-brand-600 text-white px-2 py-0.5 rounded-full font-mono">
            {assets.length}
          </span>
        </div>
        <p className="text-xs text-slate-500">Swagger, SQL, JSON, JIL, Tickets</p>
      </div>

      {/* Asset list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {assets.map((asset) => {
          const Icon = TYPE_ICON[asset.asset_type] || FileText
          const color = TYPE_COLOR[asset.asset_type] || 'text-slate-400'
          const label = TYPE_LABEL[asset.asset_type] || 'File'
          return (
            <div key={asset.filename}
              className="bg-surface-700 rounded-lg p-3 group hover:bg-surface-600 transition-colors">
              <div className="flex items-start gap-2">
                <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${color}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-200 truncate">{asset.system_name}</p>
                  <p className="text-xs text-slate-500 truncate">{asset.filename}</p>
                  <span className={`text-xs ${color} font-mono`}>{label}</span>
                </div>
                {!asset.preloaded && (
                  <button onClick={() => onRemove(asset.filename)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-red-400">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
              {asset.preloaded && (
                <div className="mt-1.5">
                  <span className="text-xs text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">pre-loaded</span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Upload drop zone */}
      <div className="p-3 border-t border-slate-700">
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-slate-600 hover:border-brand-500 rounded-lg p-4 text-center cursor-pointer transition-colors group">
          <Upload className="w-5 h-5 text-slate-500 group-hover:text-brand-400 mx-auto mb-1 transition-colors" />
          <p className="text-xs text-slate-500 group-hover:text-slate-400">Drop file or click to upload</p>
          <p className="text-xs text-slate-600 mt-0.5">.yaml .sql .json .jil</p>
          <input ref={fileRef} type="file" className="hidden"
            accept=".yaml,.yml,.sql,.json,.jil,.txt,.csv"
            onChange={handleFile} />
        </div>

        <button onClick={onReset} disabled={isRunning}
          className="mt-2 w-full flex items-center justify-center gap-2 text-xs text-slate-400
            hover:text-slate-200 hover:bg-slate-700 rounded-lg py-2 transition-colors disabled:opacity-40">
          <RefreshCw className="w-3.5 h-3.5" />
          Reset Demo
        </button>
      </div>
    </aside>
  )
}
