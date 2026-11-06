import React, { useState } from 'react'
import { Activity, Terminal, AlertCircle, Info, Flame, Layers } from 'lucide-react'

export default function TelemetryViewer({ incident }) {
  const [activeTab, setActiveTab] = useState('metrics') // 'metrics' or 'logs'
  const [selectedMetricIdx, setSelectedMetricIdx] = useState(0)
  const [hoveredIndex, setHoveredIndex] = useState(null)

  if (!incident) return null

  const evidenceItems = incident.active_investigation?.evidence_items || []
  const metricItems = evidenceItems.filter(e => e.source_type === 'METRICS')
  const logItem = evidenceItems.find(e => e.source_type === 'LOGS')
  const logs = logItem?.raw_data?.logs || []

  // Fallback metric if no metrics in evidence
  const fallbackMetric = {
    timestamps: ['14:10', '14:12', '14:14', '14:16', '14:18', '14:20', '14:22', '14:24'],
    values: [20, 25, 30, 45, 60, 85, 100, 100],
    unit: 'connections',
    metric: 'active_connections'
  }

  const currentMetricData = (metricItems[selectedMetricIdx]?.raw_data) || fallbackMetric
  const values = (currentMetricData.values && currentMetricData.values.length > 0) ? currentMetricData.values : [10, 20, 30, 50, 80, 100]
  const timestamps = (currentMetricData.timestamps && currentMetricData.timestamps.length > 0) ? currentMetricData.timestamps : values.map((_, i) => `T-${values.length - i}m`)
  const unit = currentMetricData.unit || ''
  const maxVal = Math.max(...values, 1)
  const minVal = 0

  // SVG dimensions
  const svgWidth = 600
  const svgHeight = 130
  const paddingX = 20
  const paddingY = 15
  const chartWidth = svgWidth - paddingX * 2
  const chartHeight = svgHeight - paddingY * 2

  // Compute SVG coordinates
  const points = values.map((val, idx) => {
    const x = paddingX + (idx / Math.max(values.length - 1, 1)) * chartWidth
    const y = paddingY + chartHeight - ((val - minVal) / (maxVal - minVal || 1)) * chartHeight
    return { x, y, val, time: timestamps[idx] || '' }
  })

  // SVG Path strings
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${svgHeight - paddingY} L ${points[0].x} ${svgHeight - paddingY} Z`

  const isAnomalous = currentMetricData.anomaly_detected || values[values.length - 1] === maxVal

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-lg">
      {/* Tab & Metric Header */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-950/50 gap-2">
        <div className="flex items-center space-x-1.5">
          <button
            onClick={() => setActiveTab('metrics')}
            className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
              activeTab === 'metrics'
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Telemetry Metrics ({metricItems.length || 1})</span>
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
          Target Service: <strong className="text-slate-200">{incident.service_name}</strong>
        </span>
      </div>

      {/* Tab Body */}
      <div className="p-4">
        {activeTab === 'metrics' ? (
          <div className="space-y-3">
            {/* Multi-Metric Switcher (if more than 1 metric exists) */}
            {metricItems.length > 1 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                <span className="text-[10px] text-slate-500 uppercase font-bold shrink-0">Metrics:</span>
                {metricItems.map((m, idx) => {
                  const mName = m.raw_data?.metric || `Metric ${idx + 1}`
                  const isSelected = selectedMetricIdx === idx
                  return (
                    <button
                      key={idx}
                      onClick={() => {
                        setSelectedMetricIdx(idx)
                        setHoveredIndex(null)
                      }}
                      className={`text-[11px] px-2.5 py-0.5 rounded-full font-mono transition-all ${
                        isSelected 
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 font-bold' 
                          : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-transparent'
                      }`}
                    >
                      {mName}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Metric Meta Row */}
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-300">
                Metric: <span className="font-mono text-blue-400 font-bold">{currentMetricData.metric}</span>
              </span>
              <div className="flex items-center space-x-3 text-xs">
                <span className="text-slate-400">
                  Peak: <strong className="text-slate-200">{Math.max(...values)} {unit}</strong>
                </span>
                {hoveredIndex !== null && (
                  <span className="text-blue-400 font-mono font-bold bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                    {points[hoveredIndex]?.time}: {points[hoveredIndex]?.val} {unit}
                  </span>
                )}
              </div>
            </div>

            {/* Crisp Interactive SVG Telemetry Chart */}
            <div className="relative w-full bg-slate-950/70 rounded-xl p-3 border border-slate-800/80 overflow-hidden">
              <svg 
                viewBox={`0 0 ${svgWidth} ${svgHeight}`} 
                className="w-full h-36 overflow-visible"
              >
                <defs>
                  {/* Glowing Area Gradient */}
                  <linearGradient id="metricGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={isAnomalous ? '#f43f5e' : '#3b82f6'} stopOpacity="0.45" />
                    <stop offset="90%" stopColor={isAnomalous ? '#f43f5e' : '#3b82f6'} stopOpacity="0.02" />
                  </linearGradient>
                  {/* Subtle Grid Pattern */}
                  <linearGradient id="strokeGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={isAnomalous ? '#fb7185' : '#60a5fa'} />
                    <stop offset="100%" stopColor={isAnomalous ? '#f43f5e' : '#2563eb'} />
                  </linearGradient>
                </defs>

                {/* Horizontal Grid Lines */}
                {[0.25, 0.5, 0.75, 1.0].map((ratio, i) => {
                  const y = paddingY + chartHeight * (1 - ratio)
                  return (
                    <line
                      key={i}
                      x1={paddingX}
                      y1={y}
                      x2={svgWidth - paddingX}
                      y2={y}
                      stroke="#1e293b"
                      strokeDasharray="4 4"
                      strokeWidth="1"
                    />
                  )
                })}

                {/* Filled Area Under Curve */}
                <path d={areaPath} fill="url(#metricGradient)" />

                {/* Main Metric Curve Line */}
                <path
                  d={linePath}
                  fill="none"
                  stroke="url(#strokeGradient)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Interactive Data Point Dots */}
                {points.map((p, idx) => {
                  const isHovered = hoveredIndex === idx
                  const isPeak = p.val === maxVal
                  return (
                    <g key={idx} onMouseEnter={() => setHoveredIndex(idx)}>
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={isHovered ? 6 : (isPeak ? 4.5 : 3)}
                        fill={isPeak ? '#f43f5e' : '#3b82f6'}
                        stroke="#ffffff"
                        strokeWidth={isHovered ? 2.5 : 1.5}
                        className="cursor-pointer transition-all"
                      />
                    </g>
                  )
                })}
              </svg>

              {/* X-Axis Timestamps */}
              <div className="flex justify-between text-[10px] text-slate-500 font-mono pt-1.5 px-2 border-t border-slate-800/80">
                {timestamps.filter((_, i) => i % Math.max(1, Math.floor(timestamps.length / 6)) === 0 || i === timestamps.length - 1).map((t, idx) => (
                  <span key={idx}>{t}</span>
                ))}
              </div>
            </div>

            {/* Anomaly Callout Banner */}
            {currentMetricData.anomaly_details && (
              <div className="flex items-start space-x-2 text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg">
                <Flame className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{currentMetricData.anomaly_details}</span>
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
