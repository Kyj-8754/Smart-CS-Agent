import { useState, useEffect } from 'react';
import { getCurrentUser, logout } from './services/auth';
import Login from './components/Login';
import Chat from './components/Chat';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const currentUser = getCurrentUser();
    setUser(currentUser);
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  if (loading) {
    return <div className="loading">로딩 중...</div>;
  }

  return (
    <>
      {user ? (
        <Chat user={user} onLogout={handleLogout} />
      ) : (
        <Login onLoginSuccess={handleLogin} />
      )}
    </>
  );
}

export default App;
