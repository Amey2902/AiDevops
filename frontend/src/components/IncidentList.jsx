import React from 'react'
import { AlertTriangle, Clock, Server, CheckCircle2, Loader2, Sparkles } from 'lucide-react'

export default function IncidentList({ 
  incidents = [], 
  selectedId, 
  onSelect, 
  onInvestigate, 
  investigatingId 
}) {
  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'P1_CRITICAL':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">P1 CRITICAL</span>
      case 'P2_HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">P2 HIGH</span>
      case 'P3_MODERATE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">P3 MODERATE</span>
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">P4 LOW</span>
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'IDENTIFIED':
        return (
          <span className="flex items-center space-x-1 text-[11px] font-medium text-emerald-400">
            <CheckCircle2 className="w-3 h-3" />
            <span>RCA Identified</span>
          </span>
        )
      case 'INVESTIGATING':
        return (
          <span className="flex items-center space-x-1 text-[11px] font-medium text-blue-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Investigating</span>
          </span>
        )
      default:
        return (
          <span className="flex items-center space-x-1 text-[11px] font-medium text-amber-400">
            <AlertTriangle className="w-3 h-3" />
            <span>Triggered</span>
          </span>
        )
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Incident Feed ({incidents.length})
        </h3>
        <span className="text-[11px] text-slate-400">Real-time telemetry</span>
      </div>

      {incidents.length === 0 ? (
        <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl">
          <p className="text-sm">No active incidents detected.</p>
          <p className="text-xs mt-1">Use "Simulate Incident" to inject a failure scenario.</p>
        </div>
      ) : (
        incidents.map((incident) => {
          const isSelected = incident.id === selectedId
          const isInvestigating = incident.id === investigatingId
          const hasRCA = incident.active_investigation?.rca_report

          return (
            <div
              key={incident.id}
              onClick={() => onSelect(incident.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? 'bg-slate-900 border-blue-500/60 shadow-lg shadow-blue-500/5 ring-1 ring-blue-500/30'
                  : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-900/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center space-x-2">
                  {getSeverityBadge(incident.severity)}
                  <span className="flex items-center space-x-1 text-xs text-slate-400">
                    <Server className="w-3 h-3 text-slate-400" />
                    <span className="font-mono text-slate-300">{incident.service_name}</span>
                  </span>
                </div>
                {getStatusBadge(incident.status)}
              </div>

              <h4 className="text-sm font-semibold text-slate-200 line-clamp-2 mb-2">
                {incident.title}
              </h4>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                <div className="flex items-center space-x-1.5">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{new Date(incident.triggered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                </div>

                {!hasRCA && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onInvestigate(incident.id)
                    }}
                    disabled={isInvestigating}
                    className="flex items-center space-x-1 px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-medium transition-colors shadow-sm disabled:opacity-50"
                  >
                    {isInvestigating ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Investigating...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3 h-3 text-blue-200" />
                        <span>Investigate</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}

