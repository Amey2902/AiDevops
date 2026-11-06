import React, { useState } from 'react'
import { X, Flame, Cpu, Database, HardDrive, Loader2, Play } from 'lucide-react'

export default function ChaosModal({ isOpen, onClose, onTriggered }) {
  const [selectedScenario, setSelectedScenario] = useState('oom_memory_leak')
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const scenarios = [
    {
      id: 'oom_memory_leak',
      title: 'Memory Leak & Container OOMKill (Exit Code 137)',
      service: 'checkout-api',
      icon: HardDrive,
      severity: 'P1 CRITICAL',
      color: 'rose',
      description: 'Simulates unbounded memory allocation. Container memory spikes to 512MB limit, Linux kernel issues SIGKILL (137), triggering crash restarts.'
    },
    {
      id: 'db_connection_starvation',
      title: 'Database Connection Pool Starvation & HTTP 500 Outage',
      service: 'order-service',
      icon: Database,
      severity: 'P1 CRITICAL',
      color: 'amber',
      description: 'Simulates unreleased PostgreSQL sockets. Pool reaches 100/100 connections with 88 idle in transaction, causing 30s timeouts and HTTP 500 errors.'
    },
    {
      id: 'cpu_throttling',
      title: 'CFS CPU Quota Throttling & Gateway 504 Timeouts',
      service: 'auth-service',
      icon: Cpu,
      severity: 'P2 HIGH',
      color: 'blue',
      description: 'Simulates thread pool starvation. Container CPU reaches 100% of cgroup limit, 78% CFS periods throttled, failing readiness/liveness probes.'
    }
  ]

  const handleLaunch = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/simulation/trigger/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: selectedScenario, auto_investigate: true })
      })

      if (res.ok) {
        const data = await res.json()
        onTriggered(data.incident)
        onClose()
      }
    } catch (err) {
      console.error('Error triggering simulation:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0F172A] border border-slate-800 rounded-2xl max-w-xl w-full shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center">
              <Flame className="w-4 h-4 text-rose-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Simulate Production Incident</h3>
              <p className="text-xs text-slate-400">Inject controlled fault scenarios to test DevOpsAI investigation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scenarios List */}
        <div className="p-5 space-y-3">
          {scenarios.map((s) => {
            const Icon = s.icon
            const isSelected = selectedScenario === s.id
            return (
              <div
                key={s.id}
                onClick={() => setSelectedScenario(s.id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  isSelected
                    ? 'bg-slate-900 border-blue-500/80 shadow-md shadow-blue-500/10 ring-1 ring-blue-500/40'
                    : 'bg-slate-950/50 border-slate-800/80 hover:bg-slate-900/50 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <div className="flex items-center space-x-2.5">
                    <Icon className="w-4 h-4 text-slate-300" />
                    <span className="text-xs font-bold text-slate-100">{s.title}</span>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {s.service}
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed text-slate-400">
                  {s.description}
                </p>
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            DevOpsAI will autonomously inspect telemetry & runbooks.
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleLaunch}
              disabled={loading}
              className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white text-xs font-bold shadow-lg shadow-rose-600/20 transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Injecting Fault...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Launch Simulation</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

