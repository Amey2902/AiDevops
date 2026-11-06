import React from 'react'
import { Activity, ShieldAlert, Sparkles, BookOpen, Flame } from 'lucide-react'

export default function Navbar({ 
  onOpenChaos, 
  incidentCount = 0,
  watchdogStatus = 'healthy',
  lastProbeSeconds = 0,
  pollInterval = 15,
  onChangePollInterval
}) {
  const getWatchdogColor = () => {
    if (watchdogStatus === 'critical') return 'text-rose-400 bg-rose-500/20 border-rose-500/30'
    if (watchdogStatus === 'warning') return 'text-amber-400 bg-amber-500/20 border-amber-500/30'
    return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30'
  }

  const getWatchdogDot = () => {
    if (watchdogStatus === 'critical') return 'bg-rose-500'
    if (watchdogStatus === 'warning') return 'bg-amber-500'
    return 'bg-emerald-500'
  }
  return (
    <header className="border-b border-slate-800 bg-[#0B0F19]/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                DevOpsAI
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                SRE Agent Active
              </span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Incident Investigation & RCA Platform</p>
          </div>
        </div>

        {/* Live Metrics & Watchdog Telemetry Strip */}
        <div className="hidden lg:flex items-center space-x-4 text-xs text-slate-400">
          {/* Live Watchdog Heartbeat Badge */}
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border transition-all ${getWatchdogColor()}`}>
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${getWatchdogDot()}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${getWatchdogDot()}`}></span>
            </span>
            <span className="font-semibold capitalize">
              {watchdogStatus === 'critical' ? 'Anomaly Active' : watchdogStatus === 'warning' ? 'Degraded' : 'All Systems Nominal'}
            </span>
            <span className="text-[10px] opacity-70">({lastProbeSeconds}s ago)</span>
          </div>

          {/* Polling Interval Selector */}
          <div className="flex items-center space-x-1.5 bg-slate-900/60 px-2.5 py-1.5 rounded-lg border border-slate-800 text-[11px]">
            <span className="text-slate-500">Probe:</span>
            <select
              value={pollInterval}
              onChange={(e) => onChangePollInterval && onChangePollInterval(Number(e.target.value))}
              className="bg-transparent text-slate-200 font-semibold focus:outline-none cursor-pointer"
            >
              <option value={10} className="bg-slate-900">Every 10s</option>
              <option value={15} className="bg-slate-900">Every 15s</option>
              <option value={30} className="bg-slate-900">Every 30s</option>
              <option value={60} className="bg-slate-900">Every 60s</option>
            </select>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900/60 px-3 py-1.5 rounded-md border border-slate-800">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>Incidents:</span>
            <span className="font-semibold text-white">{incidentCount}</span>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900/60 px-3 py-1.5 rounded-md border border-slate-800">
            <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            <span>Supabase RAG:</span>
            <span className="font-semibold text-emerald-400">pgvector Live</span>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenChaos}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-rose-500/20 to-amber-500/20 hover:from-rose-500/30 hover:to-amber-500/30 border border-rose-500/30 text-rose-300 text-xs font-semibold transition-all shadow-sm"
          >
            <Flame className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
            <span>Simulate Incident</span>
          </button>
        </div>
      </div>
    </header>
  )
}

