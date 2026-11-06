import React, { useState } from 'react'
import { 
  ShieldCheck, 
  AlertOctagon, 
  CheckSquare, 
  Square, 
  BookOpen, 
  Cpu, 
  Terminal, 
  FileText, 
  Sparkles,
  ArrowRight,
  Clock,
  Layers,
  MessageSquare
} from 'lucide-react'

export default function InvestigationReport({ incident, onOpenChat }) {
  const [completedSteps, setCompletedSteps] = useState({})

  if (!incident) {
    return (
      <div className="h-full flex items-center justify-center p-12 text-slate-500">
        <p>Select an incident to view its investigation report.</p>
      </div>
    )
  }

  const investigation = incident.active_investigation
  const rca = investigation?.rca_report
  const evidenceItems = investigation?.evidence_items || []

  const toggleCheck = (idx) => {
    setCompletedSteps(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  if (!rca) {
    return (
      <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-2xl">
        <Sparkles className="w-8 h-8 text-blue-400 mx-auto mb-3 animate-bounce" />
        <h3 className="text-base font-semibold text-slate-200">Investigation Pending</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
          DevOpsAI has not investigated this incident yet. Click "Investigate with AI" to probe container health, cluster logs, and query troubleshooting runbooks.
        </p>
      </div>
    )
  }

  const confidencePercent = Math.round((rca.confidence_score || 0.9) * 100)

  return (
    <div className="space-y-6">
      {/* Root Cause Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900/90 to-blue-950/30 border border-blue-500/30 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center space-x-2">
            <span className="flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>AI Investigation Complete</span>
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Service: <strong className="text-slate-200">{incident.service_name}</strong>
            </span>
          </div>

          <div className="flex items-center space-x-3">
            {/* Confidence Score Pill */}
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1 rounded-lg border border-slate-700">
              <span className="text-xs text-slate-400">Confidence:</span>
              <span className={`text-sm font-bold ${
                confidencePercent >= 90 ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {confidencePercent}%
              </span>
            </div>

            <button
              onClick={onOpenChat}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs font-medium transition-all"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Ask DevOpsAI</span>
            </button>
          </div>
        </div>

        <h2 className="text-lg font-bold text-white mb-2 flex items-center space-x-2">
          <AlertOctagon className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{rca.root_cause_title}</span>
        </h2>

        <p className="text-xs leading-relaxed text-slate-300 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/80">
          {rca.root_cause_summary}
        </p>
      </div>

      {/* Investigation Timeline & Evidence Chain */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            <span>Investigation Evidence Chain ({evidenceItems.length} findings)</span>
          </h3>
          <span className="text-[11px] text-slate-400">Chronological verification</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {evidenceItems.map((item, idx) => {
            const isLog = item.source_type === 'LOGS'
            const isMetric = item.source_type === 'METRICS'
            const isContainer = item.source_type === 'CONTAINER_STATE'
            const isRunbook = item.source_type === 'RUNBOOK_MATCH'

            return (
              <div 
                key={item.id || idx}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="flex items-center space-x-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                      {isContainer && <Cpu className="w-3.5 h-3.5 text-purple-400" />}
                      {isLog && <Terminal className="w-3.5 h-3.5 text-amber-400" />}
                      {isMetric && <Layers className="w-3.5 h-3.5 text-blue-400" />}
                      {isRunbook && <BookOpen className="w-3.5 h-3.5 text-emerald-400" />}
                      <span>{item.source_type.replace('_', ' ')}</span>
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Weight: {Math.round(item.confidence_impact * 100)}%
                    </span>
                  </div>

                  <h4 className="text-xs font-semibold text-slate-200 mb-1.5">
                    {item.title}
                  </h4>

                  <p className="text-[11px] leading-relaxed text-slate-400 whitespace-pre-line line-clamp-4">
                    {item.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Recommended Action Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Immediate Mitigation */}
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center space-x-2 mb-3">
            <CheckSquare className="w-3.5 h-3.5" />
            <span>Immediate Mitigation Actions</span>
          </h3>

          <div className="space-y-2.5">
            {(rca.recommended_immediate_actions || []).map((action, idx) => {
              const isChecked = !!completedSteps[`imm_${idx}`]
              return (
                <div 
                  key={idx}
                  onClick={() => toggleCheck(`imm_${idx}`)}
                  className={`flex items-start space-x-2.5 p-2 rounded-lg cursor-pointer text-xs transition-colors ${
                    isChecked 
                      ? 'bg-emerald-500/5 text-slate-400 line-through' 
                      : 'hover:bg-slate-800/60 text-slate-200'
                  }`}
                >
                  {isChecked ? (
                    <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <Square className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <span className="leading-relaxed">{action}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Preventative Long-term Fixes */}
        <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center space-x-2 mb-3">
            <FileText className="w-3.5 h-3.5" />
            <span>Permanent Preventative Measures</span>
          </h3>

          <div className="space-y-2.5">
            {(rca.recommended_preventative_actions || []).map((action, idx) => (
              <div key={idx} className="flex items-start space-x-2.5 p-2 rounded-lg text-xs text-slate-300">
                <ArrowRight className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cited Runbooks */}
      {rca.cited_runbooks && rca.cited_runbooks.length > 0 && (
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2 mb-3">
            <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
            <span>Cited RAG Runbooks & Troubleshooting Playbooks</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {rca.cited_runbooks.map((rb, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-slate-200 line-clamp-1">{rb.title}</span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    Match: {Math.round((rb.similarity_score || 0.8) * 100)}%
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2">{rb.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

