import React, { useState, useEffect, useRef } from 'react'
import Navbar from './components/Navbar'
import IncidentList from './components/IncidentList'
import InvestigationReport from './components/InvestigationReport'
import TelemetryViewer from './components/TelemetryViewer'
import CopilotChatDrawer from './components/CopilotChatDrawer'
import ChaosModal from './components/ChaosModal'
import AlertToast from './components/AlertToast'
import SimulationStoryboard from './components/SimulationStoryboard'
import TopologyMap from './components/TopologyMap'
import { RefreshCw, Network, ChevronDown, ChevronUp } from 'lucide-react'

export default function App() {
  const [incidents, setIncidents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [investigatingId, setInvestigatingId] = useState(null)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isChaosOpen, setIsChaosOpen] = useState(false)
  
  // Real-time Watchdog & Alert Toast States
  const [watchdogStatus, setWatchdogStatus] = useState('healthy')
  const [lastProbeSeconds, setLastProbeSeconds] = useState(0)
  const [pollInterval, setPollInterval] = useState(5)
  const [activeAlert, setActiveAlert] = useState(null)
  const [isRemediating, setIsRemediating] = useState(false)

  // Live 25-Second Storyboard Demo Mode
  const [isStoryActive, setIsStoryActive] = useState(false)
  const [storyCountdown, setStoryCountdown] = useState(25)
  const [isStoryPaused, setIsStoryPaused] = useState(false)
  const [hasCompletedStory, setHasCompletedStory] = useState(false)
  
  // Live Topology Map State
  const [showTopology, setShowTopology] = useState(true)
  const [selectedService, setSelectedService] = useState(null)
  
  const knownIncidentIds = useRef(new Set())

  const fetchIncidents = async (selectLatest = false) => {
    try {
      const res = await fetch('/api/incidents/')
      if (res.ok) {
        const data = await res.json()
        
        // Detect newly arrived incidents for toast alert
        if (knownIncidentIds.current.size > 0 && data.length > 0) {
          const newest = data[0]
          if (!knownIncidentIds.current.has(newest.id) && newest.status !== 'RESOLVED') {
            setActiveAlert(newest)
            setSelectedId(newest.id) // Automatically select newly triggered attack
          }
        }

        // Update known IDs
        data.forEach(item => knownIncidentIds.current.add(item.id))

        setIncidents(data)
        if (data.length > 0) {
          if (selectLatest || !selectedId) {
            setSelectedId(data[0].id)
          }
        }
      }
    } catch (err) {
      console.error('Error fetching incidents:', err)
    } finally {
      setLoading(false)
    }
  }

  const checkWatchdogHealth = async () => {
    try {
      const res = await fetch('/api/health/watchdog/')
      if (res.ok) {
        const data = await res.json()
        setWatchdogStatus(data.status || 'healthy')
        setLastProbeSeconds(0)
      }
    } catch (err) {
      console.error('Error checking watchdog health:', err)
    }
  }

  // Initial load
  useEffect(() => {
    fetchIncidents(true)
    checkWatchdogHealth()
  }, [])

  // Live Heartbeat Watchdog Poller
  useEffect(() => {
    // 1-second probe counter
    const counterTimer = setInterval(() => {
      setLastProbeSeconds(prev => prev + 1)
    }, 1000)

    // Periodic health probe
    const pollTimer = setInterval(() => {
      checkWatchdogHealth()
      fetchIncidents(false)
    }, pollInterval * 1000)

    return () => {
      clearInterval(counterTimer)
      clearInterval(pollTimer)
    }
  }, [pollInterval])

  // Live 25-Second Storyboard Demo Countdown
  useEffect(() => {
    let timer = null
    if (isStoryActive && !isStoryPaused) {
      if (storyCountdown > 0) {
        timer = setTimeout(() => {
          setStoryCountdown(prev => prev - 1)
        }, 1000)
      } else {
        setIsStoryActive(false)
        setHasCompletedStory(true)
        triggerChaosStrike()
      }
    }
    return () => {
      if (timer) clearTimeout(timer)
    }
  }, [isStoryActive, storyCountdown, isStoryPaused])

  const triggerChaosStrike = async () => {
    try {
      const res = await fetch('/api/simulation/trigger/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: 'oom_memory_leak', auto_investigate: true })
      })
      if (res.ok) {
        const data = await res.json()
        await fetchIncidents(true)
        if (data.incident) {
          setSelectedId(data.incident.id)
          setActiveAlert(data.incident)
        }
        setWatchdogStatus('critical')
      }
    } catch (err) {
      console.error('Error triggering chaos strike:', err)
    }
  }

  const handleStartStory = () => {
    setStoryCountdown(25)
    setIsStoryActive(true)
    setIsStoryPaused(false)
    setHasCompletedStory(false)
    setWatchdogStatus('healthy')
  }

  const handleStopStory = () => {
    setIsStoryActive(false)
    setHasCompletedStory(false)
  }

  const handleFastForward = () => {
    setStoryCountdown(1)
  }

  const handleInvestigate = async (id) => {
    setInvestigatingId(id)
    try {
      const res = await fetch(`/api/incidents/${id}/investigate/`, {
        method: 'POST'
      })
      if (res.ok) {
        await fetchIncidents()
        setSelectedId(id)
      }
    } catch (err) {
      console.error('Error triggering investigation:', err)
    } finally {
      setInvestigatingId(null)
    }
  }

  const handleRemediate = async (id, actionName) => {
    setIsRemediating(true)
    try {
      const res = await fetch(`/api/incidents/${id}/remediate/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: actionName })
      })
      if (res.ok) {
        await fetchIncidents()
        await checkWatchdogHealth()
      }
    } catch (err) {
      console.error('Error executing remediation:', err)
    } finally {
      setIsRemediating(false)
    }
  }

  const handleChaosTriggered = (newIncident) => {
    fetchIncidents(true)
    if (newIncident?.id) {
      setSelectedId(newIncident.id)
      setActiveAlert(newIncident)
    }
  }

  // Active Incident Resolver (supports Live Story Dynamic Evolution)
  const getActiveDisplayIncident = () => {
    if (isStoryActive) {
      const elapsed = 25 - storyCountdown
      const now = new Date()
      
      let values = [110, 115, 118, 122, 120]
      let anomaly = false
      let anomalyDetails = null
      let logs = [
        { timestamp: new Date(now.getTime() - 12000).toISOString(), level: 'INFO', message: 'Traffic normal: 240 req/sec on /api/v1/checkout (status 200 OK)' },
        { timestamp: new Date(now.getTime() - 8000).toISOString(), level: 'INFO', message: 'Health probe /healthz responded in 12ms (status healthy)' },
        { timestamp: new Date(now.getTime() - 3000).toISOString(), level: 'INFO', message: 'Worker pool active connections: 14/100, memory usage nominal (120MB)' }
      ]

      if (elapsed > 10 && elapsed <= 20) {
        values = [120, 140, 220, 310, 420, 460]
        anomaly = true
        anomalyDetails = `Warning: Memory allocation climbing rapidly (${values[values.length - 1]}MB / 512MB)`
        logs.push({
          timestamp: new Date().toISOString(),
          level: 'WARN',
          message: 'Memory heap utilization exceeded 85% threshold (435MB/512MB).'
        })
        logs.push({
          timestamp: new Date().toISOString(),
          level: 'WARN',
          message: 'Garbage collection pause 1820ms (> pause target).'
        })
      } else if (elapsed > 20) {
        values = [120, 140, 220, 310, 420, 512, 120]
        anomaly = true
        anomalyDetails = 'CRITICAL: Container memory hit 512MB ceiling. Linux kernel OOM Killer invoked SIGKILL (Exit code 137).'
        logs.push({
          timestamp: new Date().toISOString(),
          level: 'ERROR',
          message: 'MemoryError: Unable to allocate 32.0 MiB buffer for batch transaction.'
        })
        logs.push({
          timestamp: new Date().toISOString(),
          level: 'FATAL',
          message: 'Process terminated by SIGKILL (Signal 9 / Exit Code 137). Linux OOM Killer invoked.'
        })
      }

      return {
        id: 'live-story-demo',
        service_name: 'checkout-api',
        title: elapsed < 20 ? 'Live Monitored Session: checkout-api (Traffic Baseline)' : 'Container Crash Loop & Linux OOMKiller (Exit 137)',
        severity: elapsed < 12 ? 'P4_LOW' : (elapsed < 20 ? 'P2_HIGH' : 'P1_CRITICAL'),
        status: elapsed < 20 ? 'INVESTIGATING' : 'IDENTIFIED',
        active_investigation: {
          evidence_items: [
            {
              source_type: 'METRICS',
              raw_data: {
                metric: 'container_memory_working_set_bytes_mb',
                unit: 'MB',
                limit_mb: 512,
                values: values,
                timestamps: values.map((_, i) => `${now.getHours()}:${String(now.getMinutes()).padStart(2, '0')}:${String((now.getSeconds() + i * 4) % 60).padStart(2, '0')}`),
                anomaly_detected: anomaly,
                anomaly_details: anomalyDetails
              }
            },
            {
              source_type: 'LOGS',
              raw_data: {
                logs: logs
              }
            }
          ],
          rca_report: elapsed > 20 ? {
            root_cause_title: 'Uncontrolled Memory Leak Causing Linux OOMKilled Termination (Exit Code 137)',
            root_cause_summary: 'Service checkout-api exceeded its allotted container memory ceiling (512MB). Memory consumption climbed steadily without deallocation until the Linux kernel Out-Of-Memory Killer issued SIGKILL (Exit code 137).',
            confidence_score: 0.96,
            recommended_immediate_actions: [
              'Increase container memory limit from 512MB to 1024MB in docker-compose.yml.',
              'Restart container instance to reclaim leaked heap memory.',
              'Verify memory working set stabilizes below 50% post-restart.'
            ],
            recommended_preventative_actions: [
              'Profile application heap allocations to identify uncollected object references.',
              'Implement streaming response processing for batch/bulk export endpoints.'
            ],
            cited_runbooks: [
              { title: 'Oom Killed 137 > Runbook: Investigating Container OOMKilled', similarity_score: 0.86, excerpt: 'When a container exceeds its configured memory limit...' }
            ]
          } : null
        }
      }
    }

    return incidents.find(i => i.id === selectedId) || incidents[0]
  }

  const selectedIncident = getActiveDisplayIncident()

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col">
      {/* Top Navigation with Live Heartbeat */}
      <Navbar 
        onOpenChaos={() => setIsChaosOpen(true)}
        incidentCount={incidents.length}
        watchdogStatus={watchdogStatus}
        lastProbeSeconds={lastProbeSeconds}
        pollInterval={pollInterval}
        onChangePollInterval={(val) => setPollInterval(val)}
        isStoryActive={isStoryActive}
        storyCountdown={storyCountdown}
        onStartStory={handleStartStory}
        onStopStory={handleStopStory}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Simulation Storyboard Stepper & Commentary */}
        <SimulationStoryboard
          isStoryActive={isStoryActive}
          storyCountdown={storyCountdown}
          isPaused={isStoryPaused}
          onStartStory={handleStartStory}
          onStopStory={handleStopStory}
          onTogglePause={() => setIsStoryPaused(!isStoryPaused)}
          onFastForward={handleFastForward}
          hasCompletedStory={hasCompletedStory}
        />

        {/* Live Microservice Topology Map */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <button
              onClick={() => setShowTopology(!showTopology)}
              className="flex items-center space-x-2 text-xs font-bold text-slate-300 hover:text-white transition-colors bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800"
            >
              <Network className="w-4 h-4 text-blue-400" />
              <span>Cluster Topology & Dependency Architecture</span>
              {showTopology ? <ChevronUp className="w-3.5 h-3.5 text-slate-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
            </button>
            <span className="text-[11px] font-mono text-slate-500">
              Interactive Microservice Service Map
            </span>
          </div>

          {showTopology && (
            <TopologyMap
              selectedService={selectedService}
              onSelectService={(svcName) => {
                setSelectedService(svcName)
                const matching = incidents.find(i => i.service_name === svcName)
                if (matching) setSelectedId(matching.id)
              }}
            />
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Incident List Feed */}
          <section className="lg:col-span-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400">Live Incident Triage</span>
              <button
                onClick={() => {
                  fetchIncidents()
                  checkWatchdogHealth()
                }}
                className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            <IncidentList
              incidents={incidents}
              selectedId={selectedIncident?.id}
              onSelect={(id) => setSelectedId(id)}
              onInvestigate={handleInvestigate}
              investigatingId={investigatingId}
            />
          </section>

          {/* Right Column: Investigation & Telemetry */}
          <section className="lg:col-span-8 space-y-6">
            {loading ? (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                Connecting to DevOpsAI Observability Hub...
              </div>
            ) : selectedIncident ? (
              <>
                {/* Telemetry Resource Inspector */}
                <TelemetryViewer incident={selectedIncident} />

                {/* RCA Investigation Report with 1-Click Remediation */}
                <InvestigationReport 
                  incident={selectedIncident}
                  onOpenChat={() => setIsChatOpen(true)}
                  onRemediate={handleRemediate}
                  isRemediating={isRemediating}
                />
              </>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                No incidents selected.
              </div>
            )}
          </section>
        </div>
      </main>

      {/* "Ask DevOpsAI" Copilot Drawer */}
      <CopilotChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        incident={selectedIncident}
      />

      {/* Chaos Simulation Trigger Modal */}
      <ChaosModal
        isOpen={isChaosOpen}
        onClose={() => setIsChaosOpen(false)}
        onTriggered={handleChaosTriggered}
      />

      {/* Real-Time Floating Alert Notification Toast */}
      <AlertToast
        alert={activeAlert}
        onClose={() => setActiveAlert(null)}
        onViewIncident={(id) => setSelectedId(id)}
      />
    </div>
  )
}

