import { useState, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'
import { createSession, sendMessage } from './api'
import './App.css'

const WELCOME = {
  role: 'assistant',
  content: `Hi! I'm your DataDog observability assistant.\n\nYou can ask me things like:\n- "Show me error rate for the payments service in the last hour"\n- "Are there any active monitors firing right now?"\n- "What does CPU look like on the api-gateway hosts?"\n- "Summarise any incidents from the last 24 hours"`
}

export default function App() {
  const [messages, setMessages] = useState([WELCOME])
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    createSession()
      .then(id => setSessionId(id))
      .catch(() => console.error('Could not create session'))
  }, [])

  const handleSend = async (text) => {
    if (!text.trim() || loading) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const data = await sendMessage(sessionId, text)
      setSessionId(data.session_id)
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Something went wrong: ${err.message}`,
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    const id = await createSession()
    setSessionId(id)
    setMessages([WELCOME])
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">DD</div>
          <div>
            <h1 className="header-title">Observability Agent</h1>
            <p className="header-sub">Powered by DataDog + Azure OpenAI</p>
          </div>
        </div>
        <button className="clear-btn" onClick={handleClear} title="Start new session">
          New Chat
        </button>
      </header>

      <ChatWindow messages={messages} loading={loading} />
      <InputBar onSend={handleSend} disabled={loading} />
    </div>
  )
}
