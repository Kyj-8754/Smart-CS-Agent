import { useState, useRef, useEffect } from 'react';
import { sendMessage, approveTransaction } from '../services/api';
import Message from './Message';
import ApprovalDialog from './ApprovalDialog';
import { colors } from '../styles/colors';
import './Chat.css';

const Chat = ({ user, onLogout }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await sendMessage(input, user.id, conversationHistory);

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.message || '응답을 생성하는 중 문제가 발생했습니다.',
        timestamp: new Date().toISOString(),
        metadata: response.metadata
      };

      setMessages(prev => [...prev, assistantMessage]);

      if (response.requires_approval) {
        setPendingApproval({
          transactionId: response.transaction_id,
          description: response.approval_message,
          data: response.transaction_data
        });
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'system',
        content: '네트워크 오류가 발생했습니다. 백엔드 서버를 확인해주세요.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approved) => {
    if (!pendingApproval) return;

    try {
      const result = await approveTransaction(pendingApproval.transactionId, approved);

      const resultMessage = {
        id: Date.now(),
        role: 'system',
        content: result.message,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, resultMessage]);
    } catch (error) {
      console.error('Approval error:', error);
    } finally {
      setPendingApproval(null);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-main">
        <div className="messages-container">
          {messages.map(msg => (
            <Message key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="메시지를 입력하세요..."
            disabled={loading}
            rows="3"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{ backgroundColor: colors.accent }}
          >
            {loading ? '전송 중...' : '전송'}
          </button>
        </div>
      </div>

      {pendingApproval && (
        <ApprovalDialog
          approval={pendingApproval}
          onApprove={() => handleApprove(true)}
          onReject={() => handleApprove(false)}
        />
      )}
    </div>
  );
};

export default Chat;
