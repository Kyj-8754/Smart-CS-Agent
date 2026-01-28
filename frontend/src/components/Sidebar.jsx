import { colors } from '../styles/colors';
import './Sidebar.css';

const Sidebar = ({ user, onLogout, isOpen, onToggle }) => {
  return (
    <>
      <div className={`sidebar ${!isOpen ? 'sidebar-hidden' : ''}`} style={{ backgroundColor: colors.primary }}>
        <div className="sidebar-header">
          <h2>Smart CS</h2>
        </div>
        
        <div className="sidebar-user">
          <div className="user-avatar">
            {user.name.charAt(0)}
          </div>
          <div className="user-info">
            <div className="user-name">{user.name}</div>
            <div className="user-role">{user.role === 'admin' ? '관리자' : '사용자'}</div>
          </div>
        </div>
        
        <div className="sidebar-menu">
          <div className="menu-item active">
            <span>채팅</span>
          </div>
          <div className="menu-item disabled">
            <span>대화 기록</span>
            <small>개발 중</small>
          </div>
          <div className="menu-item disabled">
            <span>설정</span>
            <small>개발 중</small>
          </div>
        </div>
        
        <div className="sidebar-footer">
          <button onClick={onLogout} className="logout-button">
            로그아웃
          </button>
        </div>

        <button className="sidebar-toggle-edge" onClick={onToggle}>
          <span className="toggle-icon"></span>
        </button>
      </div>

      {!isOpen && (
        <button className="sidebar-toggle-floating" onClick={onToggle}>
          <span className="toggle-icon-open"></span>
        </button>
      )}
    </>
  );
};

export default Sidebar;
