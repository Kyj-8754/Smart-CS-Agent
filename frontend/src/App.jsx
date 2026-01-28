import { useState, useEffect } from 'react';
import { getCurrentUser, logout } from './services/auth';
import Login from './components/Login';
import Chat from './components/Chat';
import History from './components/History';
import Sidebar from './components/Sidebar';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState('chat');
  const [sidebarOpen, setSidebarOpen] = useState(true);

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
        <div className="app-container">
          <Sidebar
            user={user}
            onLogout={handleLogout}
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(!sidebarOpen)}
            activeView={currentView}
            onViewChange={setCurrentView}
          />
          <div className={`main-content ${!sidebarOpen ? 'sidebar-closed' : ''}`}>
            {currentView === 'chat' && <Chat user={user} />}
            {currentView === 'history' && <History />}
          </div>
        </div>
      ) : (
        <Login onLoginSuccess={handleLogin} />
      )}
    </>
  );
}

export default App;
