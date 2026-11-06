import React, { useEffect, useState } from 'react'
import { AlertOctagon, X, ArrowRight, BellRing } from 'lucide-react'

export default function AlertToast({ alert, onClose, onViewIncident }) {
  const [progress, setProgress] = useState(100)

  useEffect(() => {
    if (!alert) return
    setProgress(100)
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev <= 0) {
          clearInterval(interval)
          onClose()
          return 0
        }
        return prev - 2
      })
    }, 140)

    return () => clearInterval(interval)
  }, [alert])

  if (!alert) return null

  const isP1 = alert.severity === 'P1_CRITICAL'

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md w-full animate-in slide-in-from-bottom-5 duration-200">
      <div className={`p-4 rounded-2xl shadow-2xl border backdrop-blur-md transition-all ${
        isP1 
          ? 'bg-rose-950/90 border-rose-500/50 shadow-rose-500/10' 
          : 'bg-amber-950/90 border-amber-500/50 shadow-amber-500/10'
      }`}>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center space-x-2">
            <span className="p-1.5 rounded-lg bg-rose-500/20 text-rose-300">
              <BellRing className="w-4 h-4 animate-bounce" />
            </span>
            <div>
              <span className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded ${
                isP1 ? 'bg-rose-500/30 text-rose-200 border border-rose-500/40' : 'bg-amber-500/30 text-amber-200'
              }`}>
                {alert.severity ? alert.severity.replace('_', ' ') : 'ALERT'}
              </span>
              <span className="text-xs font-mono text-slate-300 ml-2">
                {alert.service_name}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        <h4 className="text-sm font-bold text-white mb-1 line-clamp-1">
          {alert.title}
        </h4>
        <p className="text-xs text-slate-300 line-clamp-2 mb-3">
          {alert.summary || 'DevOpsAI SRE Agent is investigating telemetry...'}
        </p>

        <div className="flex items-center justify-between pt-2 border-t border-white/10">
          <span className="text-[11px] text-slate-400">
            Autonomous investigation active
          </span>
          <button
            onClick={() => {
              onViewIncident(alert.id)
              onClose()
            }}
            className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors"
          >
            <span>View RCA</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Dismiss countdown progress bar */}
        <div className="w-full bg-white/10 h-1 rounded-full mt-3 overflow-hidden">
          <div 
            style={{ width: `${progress}%` }} 
            className={`h-full transition-all duration-100 ${isP1 ? 'bg-rose-400' : 'bg-amber-400'}`} 
          />
        </div>
      </div>
    </div>
  )
}
