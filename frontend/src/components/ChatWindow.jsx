import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import './ChatWindow.css'

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <main className="chat-window">
      {messages.map((msg, i) => (
        <MessageBubble key={i} role={msg.role} content={msg.content} error={msg.error} />
      ))}
      {loading && (
        <div className="typing-indicator">
          <span /><span /><span />
        </div>
      )}
      <div ref={bottomRef} />
    </main>
  )
}
