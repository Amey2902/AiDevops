import React from 'react'
import { 
  Play, 
  Pause, 
  RotateCcw, 
  FastForward, 
  CheckCircle2, 
  AlertTriangle, 
  Flame, 
  Sparkles, 
  Activity, 
  Bot, 
  ShieldCheck, 
  Radio, 
  X
} from 'lucide-react'

export default function SimulationStoryboard({
  isStoryActive,
  storyCountdown,
  isPaused,
  onStartStory,
  onStopStory,
  onTogglePause,
  onFastForward,
  hasCompletedStory = false
}) {
  const elapsed = 25 - storyCountdown

  // Compute Current Stage (1 to 5)
  let currentStage = 1
  if (hasCompletedStory) {
    currentStage = 5
  } else if (!isStoryActive) {
    currentStage = 0
  } else if (elapsed <= 9) {
    currentStage = 1 // Healthy Baseline
  } else if (elapsed <= 18) {
    currentStage = 2 // Memory Leak Injected
  } else if (elapsed <= 24) {
    currentStage = 3 // Container Crash (Exit 137)
  } else {
    currentStage = 4 // AI SRE Triage & Supabase RAG
  }

  // 5 Stages Definition
  const stages = [
    {
      id: 1,
      title: 'Healthy Baseline',
      subtitle: '240 req/s • 120MB RAM',
      icon: Activity,
      color: 'emerald',
      activeBorder: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300',
      completedBorder: 'border-emerald-500/30 bg-slate-900/80 text-emerald-400'
    },
    {
      id: 2,
      title: 'Memory Leak',
      subtitle: 'Heap climbing to 460MB',
      icon: AlertTriangle,
      color: 'amber',
      activeBorder: 'border-amber-500/50 bg-amber-500/10 text-amber-300',
      completedBorder: 'border-amber-500/30 bg-slate-900/80 text-amber-400'
    },
    {
      id: 3,
      title: 'Kernel OOMKill',
      subtitle: 'Exit Code 137 (SIGKILL)',
      icon: Flame,
      color: 'rose',
      activeBorder: 'border-rose-500/60 bg-rose-500/15 text-rose-300 shadow-rose-950/50 shadow-lg',
      completedBorder: 'border-rose-500/30 bg-slate-900/80 text-rose-400'
    },
    {
      id: 4,
      title: 'AI RAG Triage',
      subtitle: 'Querying 24 Runbooks',
      icon: Sparkles,
      color: 'indigo',
      activeBorder: 'border-indigo-500/60 bg-indigo-500/15 text-indigo-300 shadow-indigo-950/50 shadow-lg',
      completedBorder: 'border-indigo-500/30 bg-slate-900/80 text-indigo-400'
    },
    {
      id: 5,
      title: 'RCA & Human Gate',
      subtitle: '96% Confidence Score',
      icon: CheckCircle2,
      color: 'cyan',
      activeBorder: 'border-cyan-500/60 bg-cyan-500/15 text-cyan-300',
      completedBorder: 'border-cyan-500/40 bg-slate-900/80 text-cyan-400'
    }
  ]

  // Live Second-by-Second SRE Commentary
  const getCommentary = () => {
    if (hasCompletedStory) {
      return {
        badge: 'RCA REPORT DELIVERED',
        badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        message: 'DevOpsAI diagnosed the outage in 2.4 seconds with 96% confidence: "Uncontrolled Memory Leak Causing Linux OOMKilled Termination". Review the human-in-the-loop recommendation below.'
      }
    }
    if (elapsed <= 4) {
      return {
        badge: 'STAGE 1: NORMAL TRAFFIC',
        badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        message: 'System Nominal: checkout-api is handling 240 req/sec with healthy 12ms latency. Memory is steady at 120MB.'
      }
    }
    if (elapsed <= 9) {
      return {
        badge: 'STAGE 1: HEALTH PROBES NOMINAL',
        badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
        message: 'Health probe /healthz responding in 12ms (status 200). Docker daemon reports container status UP with 0 restarts.'
      }
    }
    if (elapsed <= 14) {
      return {
        badge: 'STAGE 2: MEMORY LEAK INJECTED',
        badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
        message: 'Warning: A batch checkout transaction triggered an uncollected cache array leak. Watch the telemetry curve begin climbing!'
      }
    }
    if (elapsed <= 18) {
      return {
        badge: 'STAGE 2: HEAP SATURATION WARNING',
        badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
        message: 'High Memory Pressure: Memory reached 460MB (90% capacity). V8 garbage collection pauses are freezing worker threads.'
      }
    }
    if (elapsed <= 24) {
      return {
        badge: 'STAGE 3: CRITICAL KERNEL CRASH',
        badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30 animate-pulse',
        message: 'BOOM! Memory crossed 512MB ceiling. Linux kernel OOM Killer issued SIGKILL (Exit code 137). Container died instantly.'
      }
    }
    return {
      badge: 'STAGE 4: DEVOPSAI INVESTIGATING',
      badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30 animate-pulse',
      message: 'DevOpsAI Activated: SRE Agent caught webhook alert, scraped Docker logs, and is querying 24 Supabase pgvector runbook embeddings...'
    }
  }

  const commentary = getCommentary()

  // Standby View (When simulation is not running and hasn't just completed)
  if (!isStoryActive && !hasCompletedStory) {
    return (
      <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-r from-slate-900 via-indigo-950/20 to-slate-900 p-4 shadow-lg mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3.5">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Radio className="w-5 h-5 text-indigo-400 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h4 className="text-xs font-bold text-slate-200">Interactive Outage Simulation</h4>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                5-Stage Story
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Experience a real-time production outage: 20s healthy baseline ➔ memory leak ➔ Linux OOMKill crash (Exit 137) ➔ 3s AI RCA report.
            </p>
          </div>
        </div>

        <button
          onClick={onStartStory}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/25 transition-all transform hover:scale-[1.02]"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Launch Live 25s Demo</span>
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 shadow-2xl mb-6 space-y-3.5">
      {/* Top Header: Title, Countdown Timer, Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center space-x-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
              hasCompletedStory ? 'bg-emerald-400' : 'bg-rose-400'
            }`} />
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
              hasCompletedStory ? 'bg-emerald-500' : 'bg-rose-500'
            }`} />
          </span>
          <span className="text-xs font-bold text-slate-200">
            {hasCompletedStory ? 'Simulation Complete: RCA Delivered' : 'Live Simulation Flight Recorder'}
          </span>
          {!hasCompletedStory && (
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              T+{elapsed}s ({storyCountdown}s to crash)
            </span>
          )}
        </div>

        {/* Story Controls */}
        <div className="flex items-center space-x-1.5">
          {!hasCompletedStory ? (
            <>
              {/* Pause / Resume */}
              <button
                onClick={onTogglePause}
                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
                title={isPaused ? 'Resume countdown' : 'Pause countdown'}
              >
                {isPaused ? <Play className="w-3 h-3 fill-current" /> : <Pause className="w-3 h-3 fill-current" />}
                <span>{isPaused ? 'Resume' : 'Pause'}</span>
              </button>

              {/* Fast-Forward to Crash */}
              {elapsed < 23 && (
                <button
                  onClick={onFastForward}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-medium border border-rose-500/40 transition-colors"
                  title="Skip straight to the container crash"
                >
                  <FastForward className="w-3 h-3" />
                  <span>Fast-Forward to Crash &gt;&gt;</span>
                </button>
              )}
            </>
          ) : (
            <button
              onClick={onStartStory}
              className="flex items-center space-x-1.5 px-3 py-1 rounded bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-semibold border border-indigo-500/40 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Replay Demo</span>
            </button>
          )}

          {/* Dismiss / Stop */}
          <button
            onClick={onStopStory}
            className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            title="Close Simulation Bar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 5-Stage Story Stepper */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
        {stages.map((st) => {
          const isCurrent = currentStage === st.id
          const isDone = currentStage > st.id
          const IconComp = st.icon

          return (
            <div
              key={st.id}
              className={`p-2.5 rounded-lg border transition-all ${
                isCurrent 
                  ? `${st.activeBorder} ring-1 ring-white/10` 
                  : (isDone ? st.completedBorder : 'border-slate-800/60 bg-slate-900/30 opacity-40')
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Stage {st.id}
                </span>
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <IconComp className={`w-3.5 h-3.5 ${isCurrent ? 'animate-bounce' : 'text-slate-500'}`} />
                )}
              </div>
              <div className="text-xs font-bold truncate text-slate-200">
                {st.title}
              </div>
              <div className="text-[10px] text-slate-400 font-mono truncate mt-0.5">
                {st.subtitle}
              </div>
            </div>
          )
        })}
      </div>

      {/* Live Second-by-Second SRE Commentary Ticker */}
      <div className="flex items-start space-x-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800/80 shadow-inner">
        <Bot className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <div className="flex-1 space-y-1">
          <div className="flex items-center space-x-2">
            <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${commentary.badgeColor}`}>
              {commentary.badge}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              Live SRE Dispatch
            </span>
          </div>
          <p className="text-xs text-slate-200 leading-relaxed font-sans">
            {commentary.message}
          </p>
        </div>
      </div>
    </div>
  )
}

