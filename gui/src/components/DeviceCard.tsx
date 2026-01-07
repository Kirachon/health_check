import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/DeviceCard.css';

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

    const getStatusColor = (status: string) => {
        return status === 'online' ? '#10b981' : '#ef4444';
    };

    const formatLastSeen = (lastSeen: string | null) => {
        if (!lastSeen) return 'Never';
        const date = new Date(lastSeen);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return `${Math.floor(diffMins / 1440)}d ago`;
    };

    return (
        <div className="device-card">
            <div className="device-header">
                <div className="device-status">
                    <span
                        className="status-indicator"
                        style={{ backgroundColor: getStatusColor(device.status) }}
                    />
                    <span className="status-text">{device.status}</span>
                </div>
                <button onClick={onDelete} className="delete-button" title="Delete device">
                    ×
                </button>
            </div>

            <h3 className="device-hostname">{device.hostname}</h3>

            <div className="device-details">
                <div className="detail-row">
                    <span className="detail-label">IP:</span>
                    <span className="detail-value">{device.ip}</span>
                </div>
                <div className="detail-row">
                    <span className="detail-label">OS:</span>
                    <span className="detail-value">{device.os || 'Unknown'}</span>
                </div>
                <div className="detail-row">
                    <span className="detail-label">Last Seen:</span>
                    <span className="detail-value">{formatLastSeen(device.last_seen)}</span>
                </div>
            </div>

            <button
                onClick={() => navigate(`/devices/${device.id}`)}
                className="view-details-button"
            >
                View Metrics
            </button>
        </div>
    );
};

export default DeviceCard;
