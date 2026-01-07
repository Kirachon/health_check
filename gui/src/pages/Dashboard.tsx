import React, { useCallback, useEffect, useState } from 'react';
import {
    Server,
    Activity,
    AlertCircle,
    ShieldCheck,
    Clock,
    RefreshCw,
    Plus
} from 'lucide-react';
import { apiClient } from '../api/client';
import DeviceCard from '../components/DeviceCard';

type CssVarProperties = React.CSSProperties & Record<`--${string}`, string | number>;

interface Device {
    id: string;
    hostname: string;
    ip: string;
    os: string;
    status: string;
    last_seen: string | null;
    created_at: string;
}

const Dashboard: React.FC = () => {
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all');

    const fetchDevices = useCallback(async () => {
        try {
            const params = filter !== 'all' ? { status: filter } : {};
            const data = await apiClient.listDevices(params);
            setDevices(data.devices);
            setError(null);
        } catch (err) {
            console.error('Failed to fetch devices:', err);
            setError('Failed to load real-time device data.');
        } finally {
            setLoading(false);
        }
    }, [filter]);

    useEffect(() => {
        fetchDevices();
        const interval = setInterval(fetchDevices, 30000);
        return () => clearInterval(interval);
    }, [fetchDevices]);

    const handleDeleteDevice = async (deviceId: string) => {
        if (window.confirm('Confirm device removal from monitoring?')) {
            try {
                await apiClient.deleteDevice(deviceId);
                fetchDevices();
            } catch (error) {
                console.error('Failed to delete device:', error);
            }
        }
    };

    const stats = {
        total: devices.length,
        online: devices.filter(d => d.status === 'online').length,
        offline: devices.filter(d => d.status === 'offline').length,
    };

    const healthScore = stats.total > 0 ? Math.round((stats.online / stats.total) * 100) : 100;
    const healthRingStyle: CssVarProperties = { '--percent': healthScore };

    return (
        <div className="spectacular-dashboard">
            {/* Top Hero Widgets */}
            <section className="dashboard-grid">
                <div className="widget glass status-widget">
                    <div className="widget-icon green">
                        <ShieldCheck size={32} />
                    </div>
                    <div className="widget-content">
                        <div className="widget-label">System Integrity</div>
                        <div className="widget-value">{healthScore}% Healthy</div>
                        <div className="widget-sublabel">Across {stats.total} managed devices</div>
                    </div>
                    <div className="health-ring" style={healthRingStyle}>
                        <svg>
                            <circle cx="35" cy="35" r="30"></circle>
                            <circle
                                cx="35"
                                cy="35"
                                r="30"
                                style={{ strokeDashoffset: `calc(188 - (188 * ${healthScore}) / 100)` }}
                            ></circle>
                        </svg>
                    </div>
                </div>

                <div className="widget glass stat-mini">
                    <div className="mini-icon blue">
                        <Server size={20} />
                    </div>
                    <div className="mini-data">
                        <span className="mini-label">Online Nodes</span>
                        <span className="mini-value text-green">{stats.online}</span>
                    </div>
                </div>

                <div className="widget glass stat-mini">
                    <div className="mini-icon red">
                        <AlertCircle size={20} />
                    </div>
                    <div className="mini-data">
                        <span className="mini-label">Active Issues</span>
                        <span className="mini-value text-red">{stats.offline}</span>
                    </div>
                </div>

                <div className="widget glass stat-mini">
                    <div className="mini-icon amber">
                        <Clock size={20} />
                    </div>
                    <div className="mini-data">
                        <span className="mini-label">Monitoring Cycle</span>
                        <span className="mini-value">30s</span>
                    </div>
                </div>
            </section>

            {/* Main Content Area */}
            <section className="monitoring-section">
                <div className="section-header">
                    <div className="section-title">
                        <Activity size={18} className="text-secondary" />
                        <h2>Live Device Matrix</h2>
                    </div>

                    <div className="matrix-controls">
                        <div className="filter-group glass">
                            <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>All</button>
                            <button className={filter === 'online' ? 'active' : ''} onClick={() => setFilter('online')}>Online</button>
                            <button className={filter === 'offline' ? 'active' : ''} onClick={() => setFilter('offline')}>Offline</button>
                        </div>
                        <button className="icon-btn glass" onClick={() => fetchDevices()} title="Refresh Data">
                            <RefreshCw size={16} className={loading ? 'spinning' : ''} />
                        </button>
                    </div>
                </div>

                {error && <div className="alert glass error-alert">{error}</div>}

                {devices.length === 0 && !loading ? (
                    <div className="empty-widget glass">
                        <Plus size={48} className="text-dim" />
                        <h3>No Devices Registered</h3>
                        <p>Deploy the Health Agent to start streaming metrics.</p>
                    </div>
                ) : (
                    <div className="devices-matrix">
                        {devices.map((device) => (
                            <DeviceCard
                                key={device.id}
                                device={device}
                                onDelete={() => handleDeleteDevice(device.id)}
                            />
                        ))}
                    </div>
                )}
            </section>

            <style>{`
        .spectacular-dashboard {
          display: flex;
          flex-direction: column;
          gap: 2.5rem;
          color: var(--text-main);
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr;
          gap: 1.5rem;
        }

        .widget.glass {
          background: var(--bg-glass);
          backdrop-filter: var(--glass-blur);
          border: var(--glass-border);
          border-radius: 16px;
          padding: 1.5rem;
          display: flex;
          align-items: center;
          gap: 1.5rem;
          box-shadow: var(--glass-shadow);
          transition: transform 0.2s, border-color 0.2s;
        }

        .widget.glass:hover {
          border-color: rgba(255, 255, 255, 0.2);
          transform: translateY(-2px);
        }

        .status-widget {
          position: relative;
          overflow: hidden;
        }

        .widget-icon {
          width: 60px;
          height: 60px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .widget-icon.green {
          background: rgba(16, 185, 129, 0.1);
          color: var(--accent-primary);
          box-shadow: var(--glow-green);
        }

        .widget-label {
          color: var(--text-muted);
          font-size: 0.9rem;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .widget-value {
          font-size: 1.8rem;
          font-weight: 700;
          font-family: var(--font-display);
          margin: 0.25rem 0;
        }

        .widget-sublabel {
          color: var(--text-dim);
          font-size: 0.85rem;
        }

        .health-ring {
          margin-left: auto;
          position: relative;
          width: 70px;
          height: 70px;
        }

        .health-ring svg {
          width: 70px;
          height: 70px;
          transform: rotate(-90deg);
        }

        .health-ring circle {
          fill: none;
          stroke-width: 6;
          stroke-linecap: round;
        }

        .health-ring circle:nth-child(1) {
          stroke: rgba(255, 255, 255, 0.05);
        }

        .health-ring circle:nth-child(2) {
          stroke: var(--accent-primary);
          stroke-dasharray: 188;
          filter: drop-shadow(var(--glow-green));
          transition: stroke-dashoffset 0.5s ease;
        }

        .stat-mini {
          flex-direction: column !important;
          justify-content: center;
          gap: 0.75rem !important;
          text-align: center;
        }

        .mini-icon {
          width: 40px;
          height: 40px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .mini-icon.blue { background: rgba(14, 165, 233, 0.1); color: var(--accent-secondary); box-shadow: var(--glow-blue); }
        .mini-icon.red { background: rgba(239, 68, 68, 0.1); color: var(--accent-error); box-shadow: var(--glow-red); }
        .mini-icon.amber { background: rgba(245, 158, 11, 0.1); color: var(--accent-warning); }

        .mini-data {
          display: flex;
          flex-direction: column;
        }

        .mini-label {
          font-size: 0.75rem;
          color: var(--text-muted);
          font-weight: 500;
        }

        .mini-value {
          font-size: 1.25rem;
          font-weight: 700;
          font-family: var(--font-display);
        }

        .text-green { color: var(--accent-primary); }
        .text-red { color: var(--accent-error); }
        .text-secondary { color: var(--accent-secondary); }

        .monitoring-section {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .section-title h2 {
          margin: 0;
          font-size: 1.4rem;
        }

        .matrix-controls {
          display: flex;
          gap: 1rem;
        }

        .filter-group.glass {
          display: flex;
          padding: 4px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
        }

        .filter-group button {
          background: transparent;
          border: none;
          padding: 0.4rem 1rem;
          font-size: 0.85rem;
          color: var(--text-muted);
          border-radius: 6px;
        }

        .filter-group button:hover { background: rgba(255, 255, 255, 0.05); color: var(--text-main); }
        .filter-group button.active { background: var(--bg-slate); color: var(--text-main); border: 1px solid rgba(255, 255, 255, 0.1); }

        .icon-btn.glass {
          width: 36px;
          height: 36px;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
        }

        .spinning { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .devices-matrix {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1.5rem;
        }

        .empty-widget {
          height: 300px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          color: var(--text-muted);
        }

        .text-dim { color: var(--text-dim); }

        .alert.glass {
          padding: 1rem;
          border-radius: 12px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.2);
          color: var(--accent-error);
        }
      `}</style>
        </div>
    );
};

export default Dashboard;
