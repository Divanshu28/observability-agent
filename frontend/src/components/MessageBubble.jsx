import ReactMarkdown from 'react-markdown'
import './MessageBubble.css'

export default function MessageBubble({ role, content, error }) {
  const isUser = role === 'user'

  return (
    <div className={`bubble-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="avatar">DD</div>}
      <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'} ${error ? 'bubble-error' : ''}`}>
        {isUser ? (
          <p>{content}</p>
        ) : (
          <ReactMarkdown>{content}</ReactMarkdown>
        )}
      </div>
      {isUser && <div className="avatar avatar-user">You</div>}
    </div>
  )
}
