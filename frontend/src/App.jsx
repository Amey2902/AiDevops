import React, { useState, useEffect, useRef } from 'react'
import Navbar from './components/Navbar'
import IncidentList from './components/IncidentList'
import InvestigationReport from './components/InvestigationReport'
import TelemetryViewer from './components/TelemetryViewer'
import CopilotChatDrawer from './components/CopilotChatDrawer'
import ChaosModal from './components/ChaosModal'
import AlertToast from './components/AlertToast'
import { RefreshCw } from 'lucide-react'

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
  const [pollInterval, setPollInterval] = useState(15)
  const [activeAlert, setActiveAlert] = useState(null)
  const [isRemediating, setIsRemediating] = useState(false)
  
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

  const selectedIncident = incidents.find(i => i.id === selectedId) || incidents[0]

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
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
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

