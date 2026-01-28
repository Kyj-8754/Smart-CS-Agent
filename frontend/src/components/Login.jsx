import { useState } from 'react';
import { login } from '../services/auth';
import { colors } from '../styles/colors';
import './Login.css';

const Login = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);
    
    setLoading(false);
    
    if (result.success) {
      onLoginSuccess(result.user);
    } else {
      setError(result.message);
    }
  };

  return (
    <div className="login-container" style={{ backgroundColor: colors.background }}>
      <div className="login-card">
        <h1 style={{ color: colors.primary }}>Smart CS Agent</h1>
        <p style={{ color: colors.secondary }}>고객 지원 에이전트 시스템</p>
        
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <input
              type="text"
              placeholder="아이디"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <input
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          
          {error && (
            <div className="error-message">{error}</div>
          )}
          
          <button
            type="submit"
            className="login-button"
            style={{ backgroundColor: colors.primary }}
            disabled={loading}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
        
        <div className="test-info" style={{ color: colors.secondary }}>
          <small>테스트 계정: admin / admin123</small>
        </div>
      </div>
    </div>
  );
};

export default Login;
