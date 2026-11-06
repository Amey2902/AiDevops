import React, { useState, useEffect } from 'react'
import { 
  Globe, 
  Monitor, 
  Server, 
  Database, 
  Zap, 
  AlertTriangle, 
  Flame, 
  CheckCircle2, 
  Radio, 
  RefreshCw,
  ExternalLink
} from 'lucide-react'

export default function TopologyMap({ onSelectService, selectedService }) {
  const [topology, setTopology] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hoveredNode, setHoveredNode] = useState(null)

  const fetchTopology = async () => {
    try {
      const res = await fetch('/api/topology/')
      if (res.ok) {
        const data = await res.json()
        setTopology(data)
      }
    } catch (err) {
      console.error('Error fetching topology:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTopology()
    const interval = setInterval(fetchTopology, 4000)
    return () => clearInterval(interval)
  }, [])

  // Coordinate positions for SVG canvas (width: 760, height: 340)
  const nodePositions = {
    'ingress': { x: 380, y: 40 },
    'frontend': { x: 380, y: 125 },
    'checkout-api': { x: 380, y: 215 },
    'postgres-db': { x: 210, y: 295 },
    'redis-cache': { x: 550, y: 295 }
  }

  const getStatusColor = (status) => {
    if (status === 'critical') return {
      fill: 'bg-rose-500/15',
      border: 'border-rose-500/60',
      ring: 'ring-rose-500/30 shadow-rose-950/60 shadow-xl',
      text: 'text-rose-400',
      stroke: '#f43f5e',
      badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40'
    }
    if (status === 'degraded') return {
      fill: 'bg-amber-500/15',
      border: 'border-amber-500/60',
      ring: 'ring-amber-500/20 shadow-amber-950/40',
      text: 'text-amber-400',
      stroke: '#f59e0b',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40'
    }
    return {
      fill: 'bg-emerald-500/10',
      border: 'border-emerald-500/40',
      ring: 'ring-emerald-500/20',
      text: 'text-emerald-400',
      stroke: '#10b981',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
    }
  }

  const getNodeIcon = (id, iconType) => {
    switch (id) {
      case 'ingress': return Globe
      case 'frontend': return Monitor
      case 'checkout-api': return Server
      case 'postgres-db': return Database
      case 'redis-cache': return Zap
      default: return Server
    }
  }

  const nodes = topology?.nodes || [
    { id: 'ingress', name: 'Ingress Gateway', status: 'healthy', metrics: '240 req/s', details: 'NGINX Load Balancer' },
    { id: 'frontend', name: 'Web Frontend', status: 'healthy', metrics: '12ms P99', details: 'React 18 Storefront' },
    { id: 'checkout-api', name: 'Checkout API', status: 'healthy', metrics: '120MB RAM', details: 'Python Microservice' },
    { id: 'postgres-db', name: 'PostgreSQL Primary', status: 'healthy', metrics: '14/100 conns', details: 'RDS PostgreSQL 16' },
    { id: 'redis-cache', name: 'Redis Cache Cluster', status: 'healthy', metrics: '98.5% hit rate', details: 'ElastiCache Redis 7' }
  ]

  const edges = topology?.edges || [
    { from: 'ingress', to: 'frontend', status: 'active', latency: '4ms' },
    { from: 'frontend', to: 'checkout-api', status: 'active', latency: '14ms' },
    { from: 'checkout-api', to: 'postgres-db', status: 'active', latency: '6ms' },
    { from: 'checkout-api', to: 'redis-cache', status: 'active', latency: '2ms' }
  ]

  const isClusterCritical = topology?.overall_cluster_health === 'critical'
  const isClusterWarning = topology?.overall_cluster_health === 'warning'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-5 shadow-2xl space-y-4">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3.5">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Radio className="w-4 h-4 animate-pulse text-blue-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-xs font-bold text-slate-100 tracking-wide uppercase">
                Cluster Microservice Topology
              </h3>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                isClusterCritical 
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse' 
                  : (isClusterWarning 
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
                      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30')
              }`}>
                {isClusterCritical ? '🚨 Cascading Outage' : (isClusterWarning ? '⚠️ Degraded Performance' : '● All Systems Nominal')}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Live dependency architecture map showing real-time service health and traffic flows.
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-400">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
            <span>Healthy</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block"></span>
            <span>Degraded</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-rose-500 inline-block"></span>
            <span>Critical (Outage)</span>
          </span>
          <button
            onClick={fetchTopology}
            className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors ml-2"
            title="Refresh Topology"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div className="relative w-full bg-slate-950 rounded-xl border border-slate-900 overflow-hidden py-3">
        <svg 
          viewBox="0 0 760 340" 
          className="w-full h-auto max-h-[350px] overflow-visible select-none"
        >
          <defs>
            {/* Ambient Grid Pattern */}
            <pattern id="topoGrid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="12" cy="12" r="0.7" fill="#334155" />
            </pattern>

            {/* Glowing Gradients */}
            <linearGradient id="healthyWire" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0.8" />
            </linearGradient>

            <linearGradient id="brokenWire" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#991b1b" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          {/* Background dot grid */}
          <rect width="760" height="340" fill="url(#topoGrid)" />

          {/* Render Connecting Edges (Wires) */}
          {edges.map((e, idx) => {
            const src = nodePositions[e.from]
            const dst = nodePositions[e.to]
            if (!src || !dst) return null

            const isBroken = e.status === 'broken'
            const isDegraded = e.status === 'degraded'

            // Curved Bezier Path
            const midY = (src.y + dst.y) / 2
            const pathD = `M ${src.x} ${src.y + 20} C ${src.x} ${midY}, ${dst.x} ${midY}, ${dst.x} ${dst.y - 20}`

            return (
              <g key={idx} className="transition-all">
                {/* Glow Backdrop */}
                <path
                  d={pathD}
                  fill="none"
                  stroke={isBroken ? '#f43f5e' : (isDegraded ? '#f59e0b' : '#10b981')}
                  strokeWidth={isBroken ? 3.5 : 2}
                  strokeDasharray={isBroken ? '6 4' : 'none'}
                  strokeOpacity={isBroken ? 0.8 : 0.4}
                />

                {/* Animated Traffic Particles (Traveling along wire) */}
                {!isBroken && (
                  <circle r="3.5" fill={isDegraded ? '#fbbf24' : '#34d399'}>
                    <animateMotion
                      path={pathD}
                      dur={isDegraded ? '3.5s' : '1.8s'}
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                {/* Connection Status Label Pill */}
                <g transform={`translate(${(src.x + dst.x) / 2}, ${midY})`}>
                  <rect
                    x="-32"
                    y="-9"
                    width="64"
                    height="18"
                    rx="9"
                    fill="#0f172a"
                    stroke={isBroken ? '#f43f5e' : (isDegraded ? '#f59e0b' : '#1e293b')}
                    strokeWidth="1"
                  />
                  <text
                    textAnchor="middle"
                    y="3.5"
                    className="text-[9px] font-mono font-bold fill-slate-300"
                  >
                    {isBroken ? 'FAIL (500)' : e.latency}
                  </text>
                </g>
              </g>
            )
          })}

          {/* Render Nodes (Service Cards) */}
          {nodes.map((node) => {
            const pos = nodePositions[node.id]
            if (!pos) return null

            const colors = getStatusColor(node.status)
            const Icon = getNodeIcon(node.id, node.icon)
            const isSelected = selectedService === node.name
            const isCritical = node.status === 'critical'
            const isDegraded = node.status === 'degraded'

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                className="cursor-pointer group"
                onClick={() => onSelectService && onSelectService(node.name)}
                onMouseEnter={() => setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
              >
                {/* Pulsing ring for critical/degraded nodes */}
                {isCritical && (
                  <circle
                    r="44"
                    fill="none"
                    stroke="#f43f5e"
                    strokeWidth="2"
                    className="animate-ping opacity-60"
                  />
                )}

                {/* Node Box Card */}
                <rect
                  x="-75"
                  y="-22"
                  width="150"
                  height="44"
                  rx="10"
                  fill="#0b1120"
                  stroke={isSelected ? '#3b82f6' : colors.stroke}
                  strokeWidth={isSelected ? 2.5 : (isCritical ? 2 : 1.2)}
                  className="transition-all filter drop-shadow-md group-hover:fill-slate-900"
                />

                {/* Icon Circle */}
                <g transform="translate(-56, 0)">
                  <circle
                    r="12"
                    fill="#0f172a"
                    stroke={colors.stroke}
                    strokeWidth="1.2"
                  />
                  {isCritical ? (
                    <Flame className="w-3.5 h-3.5 text-rose-400" x="-7" y="-7" />
                  ) : (
                    <Icon className={`w-3.5 h-3.5 ${colors.text}`} x="-7" y="-7" />
                  )}
                </g>

                {/* Service Name & Metric */}
                <text
                  x="-38"
                  y="-4"
                  className="text-[11px] font-bold fill-slate-100 font-sans"
                >
                  {node.name}
                </text>
                <text
                  x="-38"
                  y="12"
                  className={`text-[9.5px] font-mono font-medium ${colors.text}`}
                >
                  {node.metrics}
                </text>

                {/* Right Status Dot */}
                <circle
                  cx="62"
                  cy="0"
                  r="4"
                  fill={isCritical ? '#f43f5e' : (isDegraded ? '#fbbf24' : '#10b981')}
                />
              </g>
            )
          })}
        </svg>

        {/* Floating Detail Tooltip on Hover */}
        {hoveredNode && (
          <div className="absolute bottom-3 left-4 p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl backdrop-blur-md text-xs space-y-1 z-20 pointer-events-none max-w-xs animate-fadeIn">
            <div className="flex items-center space-x-1.5 font-bold text-slate-100">
              <span>{hoveredNode.name}</span>
              <span className={`px-1.5 py-0.2 rounded text-[10px] uppercase font-mono ${
                hoveredNode.status === 'critical' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'
              }`}>
                {hoveredNode.status}
              </span>
            </div>
            <p className="text-slate-400 text-[11px]">{hoveredNode.details}</p>
            <div className="text-[11px] font-mono text-cyan-300 pt-0.5">
              Live Metric: <b>{hoveredNode.metrics}</b>
            </div>
            {hoveredNode.active_incident && (
              <div className="text-rose-400 text-[10px] font-mono pt-1 border-t border-slate-800">
                🚨 Outage: {hoveredNode.active_incident}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

