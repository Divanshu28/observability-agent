import { useState } from 'react'
import './InputBar.css'

export default function InputBar({ onSend, disabled }) {
  const [value, setValue] = useState('')

  const submit = () => {
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <footer className="input-bar">
      <textarea
        className="input-textarea"
        rows={1}
        placeholder="Ask about your infrastructure..."
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
      />
      <button
        className="send-btn"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send"
      >
        &#9658;
      </button>
    </footer>
  )
}
