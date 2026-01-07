import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Monitor,
    MapPin,
    Cpu,
    History,
    ChevronRight,
    MoreVertical,
    Trash2
} from 'lucide-react';

interface DeviceCardProps {
    device: {
        id: string;
        hostname: string;
        ip: string;
        os: string;
        status: string;
        last_seen: string | null;
    };
    onDelete: () => void;
}

const DeviceCard: React.FC<DeviceCardProps> = ({ device, onDelete }) => {
    const navigate = useNavigate();

    const formatLastSeen = (lastSeen: string | null) => {
        if (!lastSeen) return 'Never connected';
        const date = new Date(lastSeen);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Active now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return `${Math.floor(diffMins / 1440)}d ago`;
    };

    const isOnline = device.status === 'online';

    return (
        <div className={`spectacular-device-card glass ${!isOnline ? 'offline' : ''}`}>
            <div className="card-header">
                <div className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
                    <div className="pulse-dot"></div>
                    <span>{device.status.toUpperCase()}</span>
                </div>
                <div className="card-actions">
                    <button className="icon-action delete" onClick={(e) => { e.stopPropagation(); onDelete(); }} title="Remove Device">
                        <Trash2 size={14} />
                    </button>
                    <button className="icon-action">
                        <MoreVertical size={14} />
                    </button>
                </div>
            </div>

            <div className="card-body" onClick={() => navigate(`/devices/${device.id}`)}>
                <div className="primary-info">
                    <div className={`device-icon-wrapper ${isOnline ? 'glow-green' : 'glow-red'}`}>
                        <Monitor size={24} />
                    </div>
                    <div className="titles">
                        <h3 className="hostname">{device.hostname}</h3>
                        <span className="os-tag">{device.os || 'Unknown OS'}</span>
                    </div>
                </div>

                <div className="details-grid">
                    <div className="detail-item">
                        <MapPin size={14} className="icon" />
                        <span className="label">IP Address</span>
                        <span className="value">{device.ip}</span>
                    </div>
                    <div className="detail-item">
                        <Cpu size={14} className="icon" />
                        <span className="label">Resource Load</span>
                        <span className="value">Nominal</span>
                    </div>
                    <div className="detail-item full-width">
                        <History size={14} className="icon" />
                        <span className="label">Heartbeat</span>
                        <span className="value">{formatLastSeen(device.last_seen)}</span>
                    </div>
                </div>
            </div>

            <div className="card-footer" onClick={() => navigate(`/devices/${device.id}`)}>
                <span>View Detailed Metrics</span>
                <ChevronRight size={16} />
            </div>

            <style>{`
        .spectacular-device-card {
          padding: 0;
          display: flex;
          flex-direction: column;
          cursor: pointer;
          min-height: 240px;
        }

        .card-header {
          padding: 1rem 1.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .status-badge {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.25rem 0.6rem;
          border-radius: 20px;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.05em;
        }

        .status-badge.online {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent-primary);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-badge.offline {
          background: rgba(239, 68, 68, 0.1);
          color: var(--accent-error);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .pulse-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 8px currentColor;
        }

        .online .pulse-dot {
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.2); }
          100% { opacity: 1; transform: scale(1); }
        }

        .card-actions {
          display: flex;
          gap: 0.5rem;
        }

        .icon-action {
          background: transparent;
          border: none;
          color: var(--text-dim);
          padding: 4px;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .icon-action:hover {
          color: var(--text-main);
          background: rgba(255, 255, 255, 0.05);
        }

        .icon-action.delete:hover {
          color: var(--accent-error);
          background: rgba(239, 68, 68, 0.1);
        }

        .card-body {
          flex: 1;
          padding: 0 1.25rem 1.25rem;
        }

        .primary-info {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .device-icon-wrapper {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .glow-green { color: var(--accent-primary); box-shadow: var(--glow-green); }
        .glow-red { color: var(--accent-error); box-shadow: var(--glow-red); }

        .hostname {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--text-main);
        }

        .os-tag {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .details-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .detail-item.full-width {
          grid-column: span 2;
          margin-top: 0.5rem;
          padding-top: 0.75rem;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
        }

        .detail-item .icon {
          color: var(--text-dim);
          margin-bottom: 0.25rem;
        }

        .detail-item .label {
          font-size: 0.65rem;
          color: var(--text-dim);
          text-transform: uppercase;
          letter-spacing: 0.02em;
        }

        .detail-item .value {
          font-size: 0.85rem;
          color: var(--text-muted);
          font-weight: 500;
        }

        .card-footer {
          padding: 0.8rem 1.25rem;
          background: rgba(255, 255, 255, 0.02);
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.8rem;
          color: var(--accent-secondary);
          font-weight: 500;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          transition: all 0.2s;
        }

        .spectacular-device-card:hover .card-footer {
          background: rgba(14, 165, 233, 0.05);
          color: var(--text-main);
        }
      `}</style>
        </div>
    );
};

export default DeviceCard;
