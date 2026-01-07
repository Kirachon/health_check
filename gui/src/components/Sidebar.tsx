import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Server,
  AlertTriangle,
  Map,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Search,
  Activity,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/auth';
import { useNavigate } from 'react-router-dom';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed, setCollapsed }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };
  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
    { name: 'Devices', icon: Server, path: '/devices' },
    { name: 'Alerts', icon: AlertTriangle, path: '/alerts' },
    { name: 'Topology', icon: Map, path: '/map' },
    { name: 'Discovery', icon: Search, path: '/discovery' },
    { name: 'System Info', icon: Activity, path: '/system' },
    { name: 'Configuration', icon: Settings, path: '/config' },
  ];

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo-container">
          <Shield className="logo-icon" size={24} />
          {!collapsed && <span className="logo-text">HEALTH MONITOR</span>}
        </div>
        <button
          className="collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title={collapsed ? item.name : ''}
          >
            {({ isActive }) => (
              <>
                <item.icon className="nav-icon" size={20} />
                {!collapsed && <span className="nav-text">{item.name}</span>}
                {isActive && !collapsed && <div className="active-indicator" />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        {!collapsed ? (
          <div className="footer-content">
            <div className="user-profile">
              <div className="avatar">AD</div>
              <div className="user-info">
                <div className="username">Admin User</div>
                <div className="role">Super Admin</div>
              </div>
            </div>
            <button className="logout-action-btn" onClick={handleLogout} title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        ) : (
          <button className="logout-action-btn collapsed" onClick={handleLogout} title="Logout">
            <LogOut size={20} />
          </button>
        )}
      </div>

      <style>{`
        .sidebar {
          width: 260px;
          height: 100vh;
          background: var(--bg-glass);
          backdrop-filter: var(--glass-blur);
          border-right: var(--glass-border);
          display: flex;
          flex-direction: column;
          transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          position: sticky;
          top: 0;
          z-index: 100;
        }

        .sidebar.collapsed {
          width: 80px;
        }

        .sidebar-header {
          padding: 1.5rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          height: 80px;
        }

        .logo-container {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .logo-icon {
          color: var(--accent-primary);
          filter: drop-shadow(var(--glow-green));
        }

        .logo-text {
          font-family: var(--font-display);
          font-weight: 700;
          font-size: 1.1rem;
          letter-spacing: 0.05em;
          white-space: nowrap;
        }

        .collapse-btn {
          background: transparent;
          border: none;
          color: var(--text-muted);
          padding: 0.25rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .collapse-btn:hover {
          color: var(--text-main);
          background: rgba(255, 255, 255, 0.05);
          box-shadow: none;
        }

        .sidebar-nav {
          flex: 1;
          padding: 1rem 0.75rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 0.75rem 0.75rem;
          border-radius: 10px;
          color: var(--text-muted);
          text-decoration: none;
          transition: all 0.2s ease;
          position: relative;
        }

        .nav-item:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-main);
        }

        .nav-item.active {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent-primary);
          font-weight: 500;
        }

        .nav-icon {
          flex-shrink: 0;
        }

        .nav-text {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .active-indicator {
          position: absolute;
          right: 0;
          top: 20%;
          bottom: 20%;
          width: 3px;
          background: var(--accent-primary);
          border-radius: 3px 0 0 3px;
          box-shadow: var(--glow-green);
        }

        .sidebar-footer {
          padding: 1rem;
          border-top: var(--glass-border);
        }

        .user-profile {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem;
        }

        .avatar {
          width: 36px;
          height: 36px;
          background: var(--accent-secondary);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 0.8rem;
          box-shadow: var(--glow-blue);
        }

        .user-info {
          display: flex;
          flex-direction: column;
        }

        .username {
          font-size: 0.85rem;
          font-weight: 600;
        }

        .role {
          font-size: 0.7rem;
          color: var(--text-muted);
        }

        .footer-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }

        .logout-action-btn {
          background: transparent;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          padding: 8px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .logout-action-btn:hover {
          color: var(--accent-error);
          background: rgba(239, 68, 68, 0.1);
        }

        .logout-action-btn.collapsed {
          width: 100%;
          margin: 0 auto;
        }
      `}</style>
    </aside>
  );
};

export default Sidebar;
