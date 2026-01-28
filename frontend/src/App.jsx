import { useState, useRef, useEffect } from 'react'
import './index.css'

function App() {
  const [messages, setMessages] = useState([
    { id: 1, text: "안녕하세요! Smart CS 에이전트입니다. 어떤 도움을 드릴까요?", sender: 'agent', type: 'initial' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = { id: Date.now(), text: input, sender: 'user' }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input }),
      })

      if (!response.ok) throw new Error('Network response was not ok')
      
      const data = await response.json()
      
      const agentMessage = {
        id: Date.now() + 1,
        text: data.answer,
        sender: 'agent',
        intent: data.intent,
        confidence: data.classification_details?.confidence,
        rag: data.rag_info
      }
      
      setMessages(prev => [...prev, agentMessage])
    } catch (error) {
      console.error('Error:', error)
      const errorMessage = {
        id: Date.now() + 1,
        text: "서버와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        sender: 'agent',
        type: 'error'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>Smart CS Agent</h1>
        <div className="status-indicator">
          <div className="status-dot"></div>
          Online
        </div>
      </header>

      <div className="messages-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
            <div className="message-bubble">
              {msg.text}
              {msg.intent && (
                <div className={`intent-tag intent-${msg.intent}`}>
                  {msg.intent.replace('_', ' ')} 
                  {msg.confidence && ` (${(msg.confidence * 100).toFixed(0)}%)`}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper agent">
            <div className="message-bubble">
              에이전트가 생각 중입니다...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="input-area" onSubmit={handleSend}>
        <input
          type="text"
          className="chat-input"
          placeholder="문의 내용을 입력하세요..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="send-button" disabled={isLoading || !input.trim()}>
          {isLoading ? '...' : '전송'}
        </button>
      </form>
    </div>
  )
}

export default App
