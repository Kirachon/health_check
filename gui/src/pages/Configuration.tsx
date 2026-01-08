import React, { useMemo } from 'react';
import {
    Settings,
    ShieldCheck,
    Server,
    BellRing,
    KeyRound,
    Database,
    Network,
    Info,
    FileText
} from 'lucide-react';
import { API_BASE_URL } from '../api/client';

const Configuration: React.FC = () => {
    const apiUrl = API_BASE_URL;
    const vmUrl = import.meta.env.VITE_VM_URL || 'http://localhost:9090';

    const internalNotice = useMemo(() => {
        return 'Internal-only deployment: all services are confined to server or department networks. No cloud or external connections are required.';
    }, []);

    return (
        <div className="enterprise-container">
            <header className="page-header">
                <div className="page-title-group">
                    <h1>Global Configuration</h1>
                    <p className="page-description">{internalNotice}</p>
                </div>
            </header>

            <section className="config-grid">
                <div className="config-card glass">
                    <div className="config-card-header">
                        <ShieldCheck size={20} />
                        Security & Access
                    </div>
                    <div className="config-item">
                        <span className="label">Auth Mode</span>
                        <span className="value">JWT (local)</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Admin Provisioning</span>
                        <span className="value mono">scripts/create_admin.py</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Token Storage</span>
                        <span className="value">Local browser storage</span>
                    </div>
                </div>

                <div className="config-card glass">
                    <div className="config-card-header">
                        <Server size={20} />
                        Core Services
                    </div>
                    <div className="config-item">
                        <span className="label">API Base URL</span>
                        <span className="value mono">{apiUrl}</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Metrics Store</span>
                        <span className="value mono">{vmUrl}</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Alert Webhook</span>
                        <span className="value mono">{apiUrl.replace('/api/v1', '')}/api/v1/alerts/webhook</span>
                    </div>
                </div>

                <div className="config-card glass">
                    <div className="config-card-header">
                        <BellRing size={20} />
                        Alerting (Internal)
                    </div>
                    <div className="config-item">
                        <span className="label">Routing</span>
                        <span className="value">Email + Webhook (internal)</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Email Provider</span>
                        <span className="value">Internal SMTP</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Cloud Connectors</span>
                        <span className="value muted">Disabled</span>
                    </div>
                </div>

                <div className="config-card glass">
                    <div className="config-card-header">
                        <Database size={20} />
                        Data & Retention
                    </div>
                    <div className="config-item">
                        <span className="label">PostgreSQL</span>
                        <span className="value">15 (local container)</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Alert Retention</span>
                        <span className="value">Configurable via env</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Backups</span>
                        <span className="value muted">Schedule internally</span>
                    </div>
                </div>

                <div className="config-card glass">
                    <div className="config-card-header">
                        <Network size={20} />
                        Network Scope
                    </div>
                    <div className="config-item">
                        <span className="label">Discovery Scope</span>
                        <span className="value">Server & department subnets only</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Outbound Traffic</span>
                        <span className="value muted">Restricted</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Remote Agents</span>
                        <span className="value">Only internal LAN/VPN</span>
                    </div>
                </div>

                <div className="config-card glass">
                    <div className="config-card-header">
                        <Info size={20} />
                        Where to Configure
                    </div>
                    <div className="config-item">
                        <span className="label">Server Settings</span>
                        <span className="value mono">server/.env</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Alerting Docs</span>
                        <span className="value mono">config/ALERTING.md</span>
                    </div>
                    <div className="config-item">
                        <span className="label">Compose Stack</span>
                        <span className="value mono">docker-compose.yml</span>
                    </div>
                </div>
            </section>

            <section className="config-footer glass">
                <div className="footer-item">
                    <KeyRound size={16} />
                    Rotate credentials before distribution.
                </div>
                <div className="footer-item">
                    <FileText size={16} />
                    Update environment defaults for internal networks only.
                </div>
            </section>

            <style>{`
        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1.5rem;
        }

        .config-card {
          padding: 1.5rem;
          border-radius: 16px;
          display: grid;
          gap: 0.9rem;
        }

        .config-card-header {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          font-weight: 600;
        }

        .config-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
        }

        .label {
          color: var(--text-muted);
        }

        .value {
          font-weight: 600;
          text-align: right;
        }

        .value.mono {
          font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.85rem;
          word-break: break-all;
        }

        .value.muted {
          color: var(--text-muted);
          font-weight: 500;
        }

        .config-footer {
          margin-top: 2rem;
          padding: 1rem 1.5rem;
          border-radius: 14px;
          display: flex;
          flex-wrap: wrap;
          gap: 1.5rem;
          align-items: center;
        }

        .footer-item {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          color: var(--text-muted);
        }
      `}</style>
        </div>
    );
};

export default Configuration;
