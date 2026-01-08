import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
    Activity,
    AlertTriangle,
    Layers,
    FileCode,
    Cpu,
    BellRing,
    Map,
    Server,
    RefreshCw,
    ShieldCheck,
    X
} from 'lucide-react';
import { apiClient, API_BASE_URL } from '../api/client';

const getErrorMessage = (err: unknown, fallback: string) => {
    if (axios.isAxiosError(err)) {
        const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
        return detail || fallback;
    }
    if (err instanceof Error && err.message) return err.message;
    return fallback;
};

const formatNumber = (value: number) => new Intl.NumberFormat().format(value);

const SystemInfo: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [deviceCounts, setDeviceCounts] = useState({ total: 0, online: 0, offline: 0 });
    const [alertCounts, setAlertCounts] = useState({ total: 0, problem: 0, ok: 0, unacknowledged: 0 });
    const [templateCount, setTemplateCount] = useState(0);
    const [triggerCount, setTriggerCount] = useState(0);
    const [actionCount, setActionCount] = useState(0);
    const [mapCount, setMapCount] = useState(0);
    const [hostGroupCount, setHostGroupCount] = useState(0);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

    const fetchAll = useCallback(async (showLoading = true) => {
        try {
            if (showLoading) setLoading(true);
            setError(null);

            const [
                devicesAll,
                devicesOnline,
                devicesOffline,
                alertSummary,
                templates,
                triggers,
                actions,
                maps,
                hostGroups
            ] = await Promise.all([
                apiClient.listDevices({ limit: 1 }),
                apiClient.listDevices({ status: 'online', limit: 1 }),
                apiClient.listDevices({ status: 'offline', limit: 1 }),
                apiClient.getAlertCounts(),
                apiClient.listTemplates({ limit: 1 }),
                apiClient.listTriggers({ limit: 1 }),
                apiClient.listActions({ limit: 1 }),
                apiClient.listMaps(),
                apiClient.listHostGroups({ limit: 1 })
            ]);

            setDeviceCounts({
                total: devicesAll?.total ?? 0,
                online: devicesOnline?.total ?? 0,
                offline: devicesOffline?.total ?? 0
            });
            setAlertCounts({
                total: alertSummary?.total ?? 0,
                problem: alertSummary?.problem ?? 0,
                ok: alertSummary?.ok ?? 0,
                unacknowledged: alertSummary?.unacknowledged ?? 0
            });
            setTemplateCount(templates?.total ?? 0);
            setTriggerCount(triggers?.total ?? 0);
            setActionCount(actions?.total ?? 0);
            setMapCount(Array.isArray(maps) ? maps.length : 0);
            setHostGroupCount(hostGroups?.total ?? 0);
            setLastRefresh(new Date());
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to load system overview.'));
        } finally {
            if (showLoading) setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchAll(false);
        setRefreshing(false);
    };

    const healthScore = useMemo(() => {
        if (deviceCounts.total === 0) return 100;
        return Math.round((deviceCounts.online / deviceCounts.total) * 100);
    }, [deviceCounts]);

    return (
        <div className="enterprise-container">
            <header className="page-header">
                <div className="page-title-group">
                    <h1>System Information</h1>
                    <p className="page-description">
                        Internal-only operational overview. No cloud or external connections are used.
                    </p>
                </div>
                <button className="icon-btn glass" onClick={handleRefresh} title="Refresh">
                    <RefreshCw size={18} className={refreshing ? 'spin' : ''} />
                </button>
            </header>

            {error && (
                <div className="error-banner glass mb-4">
                    <AlertTriangle size={18} />
                    <span>{error}</span>
                    <button onClick={() => setError(null)}><X size={16} /></button>
                </div>
            )}

            <section className="system-kpis">
                <div className="kpi-card glass">
                    <div className="kpi-icon green">
                        <ShieldCheck size={28} />
                    </div>
                    <div>
                        <div className="kpi-label">System Health</div>
                        <div className="kpi-value">{healthScore}%</div>
                        <div className="kpi-subtext">{formatNumber(deviceCounts.online)} online of {formatNumber(deviceCounts.total)}</div>
                    </div>
                </div>
                <div className="kpi-card glass">
                    <div className="kpi-icon blue">
                        <Server size={28} />
                    </div>
                    <div>
                        <div className="kpi-label">Devices</div>
                        <div className="kpi-value">{formatNumber(deviceCounts.total)}</div>
                        <div className="kpi-subtext">{formatNumber(deviceCounts.offline)} offline</div>
                    </div>
                </div>
                <div className="kpi-card glass">
                    <div className="kpi-icon red">
                        <AlertTriangle size={28} />
                    </div>
                    <div>
                        <div className="kpi-label">Alerts</div>
                        <div className="kpi-value">{formatNumber(alertCounts.problem)}</div>
                        <div className="kpi-subtext">{formatNumber(alertCounts.unacknowledged)} unacknowledged</div>
                    </div>
                </div>
            </section>

            <section className="system-grid">
                <div className="system-panel glass">
                    <div className="panel-title">
                        <Activity size={18} />
                        Monitoring Inventory
                    </div>
                    <div className="panel-grid">
                        <div className="panel-item">
                            <span className="panel-label">Host Groups</span>
                            <span className="panel-value">{formatNumber(hostGroupCount)}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Templates</span>
                            <span className="panel-value">{formatNumber(templateCount)}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Triggers</span>
                            <span className="panel-value">{formatNumber(triggerCount)}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Actions</span>
                            <span className="panel-value">{formatNumber(actionCount)}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Maps</span>
                            <span className="panel-value">{formatNumber(mapCount)}</span>
                        </div>
                    </div>
                </div>

                <div className="system-panel glass">
                    <div className="panel-title">
                        <Layers size={18} />
                        Internal Endpoints
                    </div>
                    <div className="panel-grid">
                        <div className="panel-item">
                            <span className="panel-label">API Base URL</span>
                            <span className="panel-value mono">{API_BASE_URL}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Metrics Endpoint</span>
                            <span className="panel-value mono">{import.meta.env.VITE_VM_URL || 'http://localhost:9090'}</span>
                        </div>
                        <div className="panel-item">
                            <span className="panel-label">Last Refresh</span>
                            <span className="panel-value">{lastRefresh ? lastRefresh.toLocaleString() : '—'}</span>
                        </div>
                    </div>
                </div>

                <div className="system-panel glass">
                    <div className="panel-title">
                        <FileCode size={18} />
                        Components in Use
                    </div>
                    <div className="tag-grid">
                        <span className="tag-chip"><Server size={14} />FastAPI</span>
                        <span className="tag-chip"><Cpu size={14} />Agent</span>
                        <span className="tag-chip"><BellRing size={14} />Alerting</span>
                        <span className="tag-chip"><Map size={14} />Topology</span>
                    </div>
                </div>
            </section>

            {loading && (
                <div className="loading-state glass">
                    <Activity size={18} className="spin" />
                    <span>Loading system overview...</span>
                </div>
            )}

            <style>{`
        .system-kpis {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .kpi-card {
          display: flex;
          gap: 1rem;
          align-items: center;
          padding: 1.5rem;
          border-radius: 16px;
        }

        .kpi-icon {
          width: 54px;
          height: 54px;
          display: grid;
          place-items: center;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.06);
        }

        .kpi-icon.green { color: var(--accent-primary); box-shadow: var(--glow-green); }
        .kpi-icon.blue { color: var(--accent-secondary); box-shadow: var(--glow-blue); }
        .kpi-icon.red { color: var(--accent-error); box-shadow: var(--glow-red); }

        .kpi-label {
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--text-muted);
        }

        .kpi-value {
          font-size: 1.8rem;
          font-weight: 600;
        }

        .kpi-subtext {
          color: var(--text-muted);
          margin-top: 0.2rem;
        }

        .system-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 1.5rem;
        }

        .system-panel {
          padding: 1.5rem;
          border-radius: 16px;
        }

        .panel-title {
          display: flex;
          align-items: center;
          gap: 0.6rem;
          font-weight: 600;
          margin-bottom: 1.25rem;
        }

        .panel-grid {
          display: grid;
          gap: 0.9rem;
        }

        .panel-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
        }

        .panel-label {
          color: var(--text-muted);
        }

        .panel-value {
          font-weight: 600;
        }

        .panel-value.mono {
          font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
          font-size: 0.85rem;
          word-break: break-all;
        }

        .tag-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
        }

        .tag-chip {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.4rem 0.7rem;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          color: var(--text-main);
          font-size: 0.85rem;
        }

        .loading-state {
          margin-top: 1.5rem;
          display: inline-flex;
          align-items: center;
          gap: 0.6rem;
          padding: 0.75rem 1rem;
          border-radius: 12px;
        }

        .spin {
          animation: spin 1.2s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
        </div>
    );
};

export default SystemInfo;
