import React, { useState } from 'react'
import { X, Send, Bot, User, Sparkles, BookOpen, Loader2 } from 'lucide-react'

export default function CopilotChatDrawer({ isOpen, onClose, incident }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: `Hello! I am your **DevOpsAI SRE Copilot**. I have analyzed the incident for \`${incident?.service_name || 'the service'}\`. Ask me about logs, anomalous metrics, or recommended remediation procedures.`
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  if (!isOpen || !incident) return null

  const handleSend = async (messageToSend) => {
    const text = messageToSend || input
    if (!text.trim() || loading) return

    const newMessages = [...messages, { role: 'user', text }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`/api/incidents/${incident.id}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })

      if (res.ok) {
        const data = await res.json()
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            text: data.message,
            citations: data.citations
          }
        ])
      } else {
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            text: 'Encountered an issue communicating with the AI Engine. Please retry.'
          }
        ])
      }
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: 'Unable to reach backend API. Ensure the Django server is running.'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const quickPrompts = [
    'Show me error logs',
    'What are the recommended fixes?',
    'Inspect memory metrics',
    'Has this happened before?'
  ]

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-[#0F172A] border-l border-slate-800 shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Ask DevOpsAI Copilot</h3>
            <p className="text-[11px] text-slate-400">Context: {incident.service_name}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, idx) => {
          const isAssistant = m.role === 'assistant'
          return (
            <div
              key={idx}
              className={`flex items-start space-x-2.5 ${
                isAssistant ? '' : 'flex-row-reverse space-x-reverse'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs shrink-0 ${
                  isAssistant ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-200'
                }`}
              >
                {isAssistant ? <Sparkles className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
              </div>

              <div
                className={`p-3 rounded-xl text-xs max-w-[85%] leading-relaxed ${
                  isAssistant
                    ? 'bg-slate-900 border border-slate-800 text-slate-200 whitespace-pre-wrap'
                    : 'bg-blue-600 text-white'
                }`}
              >
                {m.text}

                {m.citations && m.citations.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-800 text-[10px] text-slate-400 flex flex-wrap gap-1">
                    <span className="flex items-center space-x-1 text-emerald-400">
                      <BookOpen className="w-3 h-3" />
                      <span>Citations:</span>
                    </span>
                    {m.citations.map((c, i) => (
                      <span key={i} className="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300">
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}

        {loading && (
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
            <span>DevOpsAI is analyzing telemetry and runbooks...</span>
          </div>
        )}
      </div>

      {/* Quick Prompts */}
      <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950/30 flex items-center gap-1.5 overflow-x-auto">
        {quickPrompts.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            disabled={loading}
            className="text-[10px] px-2.5 py-1 rounded-full bg-slate-800/80 hover:bg-slate-700 text-slate-300 whitespace-nowrap transition-colors border border-slate-700/60 disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/60">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about root cause, logs, metrics..."
            disabled={loading}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  )
}

