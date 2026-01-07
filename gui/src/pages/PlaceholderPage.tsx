import React from 'react';
import { type LucideIcon, Construction } from 'lucide-react';

interface PlaceholderPageProps {
    title: string;
    icon: LucideIcon;
    description: string;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, icon: Icon, description }) => {
    return (
        <div className="placeholder-page">
            <div className="placeholder-content glass">
                <div className="placeholder-icon-wrapper">
                    <Icon size={64} className="placeholder-icon" />
                </div>
                <h1>{title}</h1>
                <p>{description}</p>
                <div className="status-badge construction">
                    <Construction size={16} />
                    <span>Under Construction</span>
                </div>
            </div>

            <style>{`
        .placeholder-page {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-main);
          padding: 2rem;
        }

        .placeholder-content {
          max-width: 500px;
          width: 100%;
          padding: 3rem;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
          border-radius: 24px;
          background: var(--bg-glass);
          backdrop-filter: var(--glass-blur);
          border: var(--glass-border);
          box-shadow: var(--glass-shadow);
        }

        .placeholder-icon-wrapper {
          width: 120px;
          height: 120px;
          border-radius: 30px;
          background: rgba(255, 255, 255, 0.03);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 1rem;
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .placeholder-icon {
          color: var(--accent-secondary);
          filter: drop-shadow(var(--glow-blue));
        }

        h1 {
          font-family: var(--font-display);
          font-size: 2rem;
          margin: 0;
          letter-spacing: 0.02em;
        }

        p {
          color: var(--text-muted);
          line-height: 1.6;
          margin: 0;
        }

        .status-badge.construction {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: rgba(245, 158, 11, 0.1);
          color: var(--accent-warning);
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          margin-top: 1rem;
          border: 1px solid rgba(245, 158, 11, 0.2);
        }
      `}</style>
        </div>
    );
};

export default PlaceholderPage;
