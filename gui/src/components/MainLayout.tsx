import React, { useState } from 'react';
import Sidebar from './Sidebar';

interface MainLayoutProps {
    children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div className="app-container">
            <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
            <main className="main-content">
                <header className="content-header">
                    <div className="breadcrumb">Monitoring / Dashboard</div>
                    <div className="header-actions">
                        <button className="action-btn">Export PDF</button>
                        <button className="action-btn primary">Add Widget</button>
                    </div>
                </header>
                <div className="content-inner">
                    {children}
                </div>
            </main>

            <style>{`
        .app-container {
          display: flex;
          min-height: 100vh;
          background: var(--bg-deep);
        }

        .main-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          overflow-x: hidden;
        }

        .content-header {
          height: 80px;
          padding: 0 2rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: var(--glass-border);
          background: rgba(15, 23, 42, 0.5);
          backdrop-filter: blur(4px);
        }

        .breadcrumb {
          color: var(--text-muted);
          font-size: 0.9rem;
          font-weight: 500;
        }

        .header-actions {
          display: flex;
          gap: 1rem;
        }

        .action-btn {
          padding: 0.5rem 1.25rem;
          font-size: 0.85rem;
        }

        .action-btn.primary {
          background: var(--accent-primary);
          color: white;
          border: none;
        }

        .action-btn.primary:hover {
          box-shadow: var(--glow-green);
          filter: brightness(1.1);
        }

        .content-inner {
          padding: 2rem;
          flex: 1;
        }
      `}</style>
        </div>
    );
};

export default MainLayout;
