import React, { useState } from 'react'
import { Activity, Terminal, AlertCircle, Info, Flame } from 'lucide-react'

export default function TelemetryViewer({ incident }) {
  const [activeTab, setActiveTab] = useState('metrics') // 'metrics' or 'logs'

  if (!incident) return null

  const evidenceItems = incident.active_investigation?.evidence_items || []
  const metricItems = evidenceItems.filter(e => e.source_type === 'METRICS')
  const logItem = evidenceItems.find(e => e.source_type === 'LOGS')
  const logs = logItem?.raw_data?.logs || []

  // Extract memory / connection / cpu metrics if available
  const sampleMetric = metricItems[0]?.raw_data || {
    timestamps: ['14:10', '14:15', '14:20', '14:25', '14:30'],
    values: [150, 240, 380, 512, 120],
    unit: 'MB',
    metric: 'container_memory_working_set_bytes_mb'
  }

  const values = sampleMetric.values || [10, 20, 45, 90, 15]
  const maxVal = Math.max(...values, 1)

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
      {/* Tab Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-950/40">
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setActiveTab('metrics')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'metrics'
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Telemetry Metrics</span>
          </button>

          <button
            onClick={() => setActiveTab('logs')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'logs'
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Application Logs ({logs.length})</span>
          </button>
        </div>

        <span className="text-[11px] text-slate-400 font-mono">
          Target: {incident.service_name}
        </span>
      </div>

      {/* Tab Body */}
      <div className="p-4">
        {activeTab === 'metrics' ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-300">
                Metric: <span className="font-mono text-blue-400">{sampleMetric.metric}</span>
              </span>
              <span className="text-slate-400">Peak: {Math.max(...values)} {sampleMetric.unit}</span>
            </div>

            {/* SVG Visual Sparkline / Bar Chart */}
            <div className="h-32 flex items-end gap-2 pt-4 px-2 border-b border-l border-slate-800">
              {values.map((v, i) => {
                const heightPercent = Math.max((v / maxVal) * 100, 6)
                const isPeak = v === Math.max(...values)
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
                    {/* Tooltip */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-7 text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-white font-mono pointer-events-none whitespace-nowrap z-10">
                      {v} {sampleMetric.unit}
                    </div>
                    {/* Bar */}
                    <div 
                      style={{ height: `${heightPercent}%` }}
                      className={`w-full rounded-t transition-all ${
                        isPeak 
                          ? 'bg-gradient-to-t from-rose-600 to-rose-400 shadow-md shadow-rose-500/20' 
                          : 'bg-gradient-to-t from-blue-600 to-blue-400 opacity-80 group-hover:opacity-100'
                      }`}
                    />
                    <span className="text-[9px] text-slate-400 font-mono">
                      {sampleMetric.timestamps ? sampleMetric.timestamps[i] : `T-${values.length - i}m`}
                    </span>
                  </div>
                )
              })}
            </div>

            {sampleMetric.anomaly_details && (
              <div className="flex items-start space-x-2 text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg">
                <Flame className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{sampleMetric.anomaly_details}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2 font-mono text-xs max-h-56 overflow-y-auto">
            {logs.length === 0 ? (
              <p className="text-slate-500 text-center py-4">No error logs captured in telemetry window.</p>
            ) : (
              logs.map((log, idx) => {
                const isFatal = log.level === 'FATAL'
                const isError = log.level === 'ERROR'
                const isWarn = log.level === 'WARN'

                return (
                  <div 
                    key={idx} 
                    className="p-2 rounded bg-slate-950/80 border border-slate-800/80 flex items-start space-x-2 leading-relaxed"
                  >
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      isFatal ? 'bg-rose-500 text-white' :
                      isError ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                      isWarn ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {log.level}
                    </span>
                    <span className="text-slate-500 text-[11px] shrink-0">
                      {log.timestamp ? log.timestamp.substring(11, 19) : '14:24:00'}
                    </span>
                    <span className="text-slate-300 break-all">
                      {log.message}
                    </span>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>
    </div>
  )
}
