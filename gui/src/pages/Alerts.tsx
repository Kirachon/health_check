import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { AlertCircle, AlertTriangle, CheckCircle, Loader2, RefreshCw, X } from 'lucide-react';
import { apiClient } from '../api/client';

const getErrorMessage = (err: unknown, fallback: string) => {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    return detail || fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
};

interface AlertEvent {
  id: string;
  trigger_id: string;
  trigger_name?: string | null;
  device_id?: string | null;
  status: string;
  value?: number | null;
  message?: string | null;
  acknowledged: boolean;
  acknowledged_at?: string | null;
  created_at: string;
}

interface AlertListResponse {
  events: AlertEvent[];
  total: number;
  limit: number;
  offset: number;
}

type StatusFilter = 'all' | 'PROBLEM' | 'OK';
type AckFilter = 'all' | 'acknowledged' | 'unacknowledged';

const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [ackFilter, setAckFilter] = useState<AckFilter>('all');

  const [showAckModal, setShowAckModal] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<AlertEvent | null>(null);
  const [ackMessage, setAckMessage] = useState('');
  const [ackSaving, setAckSaving] = useState(false);

  const fetchAlerts = useCallback(
    async (showLoading = true) => {
      try {
        if (showLoading) {
          setLoading(true);
        }
        setError(null);
        const params: { status?: string; acknowledged?: boolean; limit?: number; offset?: number } = {
          limit: 50,
          offset: 0,
        };
        if (statusFilter !== 'all') {
          params.status = statusFilter;
        }
        if (ackFilter !== 'all') {
          params.acknowledged = ackFilter === 'acknowledged';
        }
        const response = (await apiClient.listAlerts(params)) as AlertListResponse;
        setAlerts(response.events || []);
        setTotal(response.total || 0);
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to load alerts'));
      } finally {
        if (showLoading) {
          setLoading(false);
        }
      }
    },
    [statusFilter, ackFilter]
  );

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAlerts(false);
    setRefreshing(false);
  };

  const handleOpenAcknowledge = (alert: AlertEvent) => {
    setSelectedAlert(alert);
    setAckMessage('');
    setShowAckModal(true);
  };

  const handleAcknowledge = async () => {
    if (!selectedAlert) return;
    setAckSaving(true);
    try {
      await apiClient.acknowledgeAlert(selectedAlert.id, ackMessage.trim() ? { message: ackMessage.trim() } : {});
      setShowAckModal(false);
      setSelectedAlert(null);
      setAckMessage('');
      await fetchAlerts(false);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to acknowledge alert'));
    } finally {
      setAckSaving(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const normalized = status?.toUpperCase();
    if (normalized === 'PROBLEM') return 'badge-red';
    if (normalized === 'OK') return 'badge-green';
    return 'badge-slate';
  };

  return (
    <div className="enterprise-container">
      <header className="page-header">
        <div className="page-title-group">
          <h1>Alerts</h1>
          <p className="page-description">View and acknowledge alert events from monitored devices.</p>
        </div>
        <button className="icon-btn glass" onClick={handleRefresh} title="Refresh">
          <RefreshCw size={18} className={refreshing ? 'spin' : ''} />
        </button>
      </header>

      {error && (
        <div className="error-banner glass mb-4">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button onClick={() => setError(null)}><X size={16} /></button>
        </div>
      )}

      <div className="table-controls glass mb-4">
        <div className="filter-group glass">
          <button className={statusFilter === 'all' ? 'active' : ''} onClick={() => setStatusFilter('all')}>All</button>
          <button className={statusFilter === 'PROBLEM' ? 'active' : ''} onClick={() => setStatusFilter('PROBLEM')}>Problem</button>
          <button className={statusFilter === 'OK' ? 'active' : ''} onClick={() => setStatusFilter('OK')}>OK</button>
        </div>
        <div className="filter-group glass">
          <button className={ackFilter === 'all' ? 'active' : ''} onClick={() => setAckFilter('all')}>All</button>
          <button className={ackFilter === 'unacknowledged' ? 'active' : ''} onClick={() => setAckFilter('unacknowledged')}>Unacknowledged</button>
          <button className={ackFilter === 'acknowledged' ? 'active' : ''} onClick={() => setAckFilter('acknowledged')}>Acknowledged</button>
        </div>
        <div className="table-meta">
          <span>{total} total</span>
        </div>
      </div>

      <div className="glass-table-container">
        {loading ? (
          <div className="loading-state">
            <Loader2 size={24} className="spin" />
            <span>Loading alerts...</span>
          </div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">
            <AlertTriangle size={48} className="empty-icon" />
            <h3>No alerts found</h3>
            <p>Alerts will appear here when triggers fire.</p>
          </div>
        ) : (
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Trigger</th>
                <th>Device</th>
                <th>Message</th>
                <th>Created</th>
                <th>Ack</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} className={alert.acknowledged ? 'disabled-row' : ''}>
                  <td>
                    <span className={`badge ${getStatusBadge(alert.status)}`}>{alert.status}</span>
                  </td>
                  <td>
                    <strong>{alert.trigger_name || 'Unknown Trigger'}</strong>
                  </td>
                  <td>
                    <span className="muted-text">{alert.device_id || 'N/A'}</span>
                  </td>
                  <td className="message-cell">{alert.message || 'No message'}</td>
                  <td>{new Date(alert.created_at).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${alert.acknowledged ? 'badge-green' : 'badge-amber'}`}>
                      {alert.acknowledged ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td className="text-right">
                    {!alert.acknowledged && (
                      <button className="primary-btn small" onClick={() => handleOpenAcknowledge(alert)}>
                        <CheckCircle size={16} />
                        Acknowledge
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showAckModal && selectedAlert && (
        <div className="modal-overlay" onClick={() => setShowAckModal(false)}>
          <div className="modal glass" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>Acknowledge Alert</h2>
              <button className="icon-btn" onClick={() => setShowAckModal(false)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              <p className="modal-subtitle">
                {selectedAlert.trigger_name || 'Unknown Trigger'}
              </p>
              <div className="form-group">
                <label>Message (optional)</label>
                <textarea
                  rows={3}
                  value={ackMessage}
                  onChange={(e) => setAckMessage(e.target.value)}
                  placeholder="Add a note about this acknowledgment..."
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="secondary-btn" onClick={() => setShowAckModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={handleAcknowledge} disabled={ackSaving}>
                {ackSaving ? 'Saving...' : 'Acknowledge'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .error-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          border-radius: 8px;
          background: rgba(239, 68, 68, 0.15);
          border: 1px solid rgba(239, 68, 68, 0.3);
          color: #fca5a5;
        }
        .error-banner button { background: none; border: none; color: inherit; cursor: pointer; margin-left: auto; }

        .table-controls {
          display: flex;
          gap: 1rem;
          padding: 1rem;
          border-radius: 12px;
          align-items: center;
          justify-content: space-between;
          flex-wrap: wrap;
        }
        .table-meta { color: var(--text-dim); font-size: 0.85rem; }

        .filter-group.glass {
          display: flex;
          padding: 4px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          gap: 4px;
        }
        .filter-group button {
          background: transparent;
          border: none;
          padding: 0.4rem 1rem;
          font-size: 0.85rem;
          color: var(--text-muted);
          border-radius: 6px;
          cursor: pointer;
        }
        .filter-group button:hover { background: rgba(255, 255, 255, 0.05); color: var(--text-main); }
        .filter-group button.active { background: var(--bg-slate); color: var(--text-main); border: 1px solid rgba(255, 255, 255, 0.1); }

        .loading-state, .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem 2rem;
          color: var(--text-dim);
          gap: 1rem;
        }
        .empty-icon { opacity: 0.3; }
        .empty-state h3 { margin: 0; color: var(--text-main); }
        .empty-state p { margin: 0; }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        .disabled-row { opacity: 0.5; }
        .message-cell { max-width: 420px; }
        .muted-text { color: var(--text-dim); }

        .icon-btn.glass {
          width: 36px;
          height: 36px;
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
        }

        .primary-btn.small { padding: 0.5rem 1rem; font-size: 0.875rem; display: inline-flex; gap: 0.4rem; align-items: center; }
        .secondary-btn {
          background: rgba(255,255,255,0.1);
          color: var(--text-main);
          border: var(--glass-border);
          padding: 0.75rem 1.25rem;
          font-weight: 500;
          cursor: pointer;
        }
        .secondary-btn:hover { background: rgba(255,255,255,0.15); }

        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }
        .modal {
          width: 100%;
          max-width: 520px;
          border-radius: 16px;
          overflow: hidden;
        }
        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1.25rem 1.5rem;
          border-bottom: var(--glass-border);
        }
        .modal-header h2 { margin: 0; font-size: 1.125rem; }
        .modal-body { padding: 1.5rem; }
        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
          padding: 1rem 1.5rem;
          border-top: var(--glass-border);
        }
        .modal-subtitle { margin: 0 0 1rem 0; color: var(--text-dim); }
        .form-group { margin-bottom: 1.25rem; }
        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: var(--text-muted);
        }
        .form-group textarea {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: var(--glass-border);
          border-radius: 8px;
          padding: 0.75rem 1rem;
          color: var(--text-main);
          outline: none;
          resize: vertical;
        }
        .form-group textarea:focus { border-color: var(--accent-secondary); }
      `}</style>
    </div>
  );
};

export default Alerts;
