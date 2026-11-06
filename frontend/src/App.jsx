import React, { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import IncidentList from './components/IncidentList'
import InvestigationReport from './components/InvestigationReport'
import TelemetryViewer from './components/TelemetryViewer'
import CopilotChatDrawer from './components/CopilotChatDrawer'
import ChaosModal from './components/ChaosModal'
import { RefreshCw } from 'lucide-react'

export default function App() {
  const [incidents, setIncidents] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [investigatingId, setInvestigatingId] = useState(null)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isChaosOpen, setIsChaosOpen] = useState(false)

  const fetchIncidents = async (selectLatest = false) => {
    try {
      const res = await fetch('/api/incidents/')
      if (res.ok) {
        const data = await res.json()
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

  useEffect(() => {
    fetchIncidents(true)
  }, [])

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

  const handleChaosTriggered = (newIncident) => {
    fetchIncidents(true)
    if (newIncident?.id) {
      setSelectedId(newIncident.id)
    }
  }

  const selectedIncident = incidents.find(i => i.id === selectedId) || incidents[0]

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <Navbar 
        onOpenChaos={() => setIsChaosOpen(true)}
        incidentCount={incidents.length}
      />

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Incident List Feed */}
        <section className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400">Live Incident Triage</span>
            <button
              onClick={() => fetchIncidents()}
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

              {/* RCA Investigation Report */}
              <InvestigationReport 
                incident={selectedIncident}
                onOpenChat={() => setIsChatOpen(true)}
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
    </div>
  )
}

