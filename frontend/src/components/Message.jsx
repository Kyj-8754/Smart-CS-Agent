import { colors } from '../styles/colors';
import './Message.css';

const Message = ({ message }) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const getMessageStyle = () => {
    if (isUser) {
      return { backgroundColor: colors.primary, color: 'white' };
    } else if (isSystem) {
      return { backgroundColor: '#f0f0f0', color: colors.secondary };
    } else {
      return { backgroundColor: colors.background, color: colors.text.primary };
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-bubble" style={getMessageStyle()}>
        <div className="message-content">{message.content}</div>
        <div className="message-time">{formatTime(message.timestamp)}</div>
      </div>
    </div>
  );
};

export default Message;
