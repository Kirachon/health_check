import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  AlertTriangle,
  Plus,
  Search,
  Edit2,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  ToggleLeft,
  ToggleRight
} from 'lucide-react';
import { apiClient } from '../api/client';

const getErrorMessage = (err: unknown, fallback: string) => {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    return detail || fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
};

interface Trigger {
  id: string;
  name: string;
  expression: string;
  severity: string;
  description: string | null;
  enabled: boolean;
  template_id: string | null;
  template_name: string | null;
  created_at: string;
  updated_at: string;
}

interface TriggerFormData {
  name: string;
  expression: string;
  severity: string;
  description: string;
}

const SEVERITIES = ['disaster', 'high', 'average', 'warning', 'info'];

const Triggers: React.FC = () => {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<Trigger | null>(null);
  const [formData, setFormData] = useState<TriggerFormData>({ name: '', expression: '', severity: 'average', description: '' });
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const fetchTriggers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.listTriggers({ search: searchTerm || undefined });
      setTriggers(response.triggers);
    } catch (err) {
      setError('Failed to load triggers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    const debounce = setTimeout(fetchTriggers, 300);
    return () => clearTimeout(debounce);
  }, [fetchTriggers]);

  const handleOpenCreate = () => {
    setEditingTrigger(null);
    setFormData({ name: '', expression: '', severity: 'average', description: '' });
    setShowModal(true);
  };

  const handleOpenEdit = (trigger: Trigger) => {
    setEditingTrigger(trigger);
    setFormData({
      name: trigger.name,
      expression: trigger.expression,
      severity: trigger.severity,
      description: trigger.description || ''
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim() || !formData.expression.trim()) return;

    setSaving(true);
    try {
      if (editingTrigger) {
        await apiClient.updateTrigger(editingTrigger.id, formData);
      } else {
        await apiClient.createTrigger(formData);
      }
      setShowModal(false);
      fetchTriggers();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to save trigger'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.deleteTrigger(id);
      setDeleteId(null);
      fetchTriggers();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to delete trigger'));
    }
  };

  const handleToggle = async (trigger: Trigger) => {
    try {
      await apiClient.toggleTrigger(trigger.id);
      fetchTriggers();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to toggle trigger'));
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      disaster: 'red', high: 'amber', average: 'amber', warning: 'blue', info: 'slate'
    };
    return colors[severity] || 'slate';
  };

  return (
    <div className="enterprise-container">
      <header className="page-header">
        <div className="page-title-group">
          <h1>Triggers</h1>
          <p className="page-description">Define alert conditions and thresholds for your monitored metrics.</p>
        </div>
        <button className="primary-btn" onClick={handleOpenCreate}>
          <Plus size={18} />
          Create Trigger
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
        <div className="search-box">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            placeholder="Search triggers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="glass-table-container">
        {loading ? (
          <div className="loading-state">
            <Loader2 size={24} className="spin" />
            <span>Loading triggers...</span>
          </div>
        ) : triggers.length === 0 ? (
          <div className="empty-state">
            <AlertTriangle size={48} className="empty-icon" />
            <h3>No triggers found</h3>
            <p>Create your first trigger to start monitoring thresholds.</p>
            <button className="primary-btn small" onClick={handleOpenCreate}>
              <Plus size={16} /> Create Trigger
            </button>
          </div>
        ) : (
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Severity</th>
                <th>Name</th>
                <th>Expression</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {triggers.map((trigger) => (
                <tr key={trigger.id} className={!trigger.enabled ? 'disabled-row' : ''}>
                  <td>
                    <button
                      className={`toggle-btn ${trigger.enabled ? 'active' : ''}`}
                      onClick={() => handleToggle(trigger)}
                      title={trigger.enabled ? 'Disable' : 'Enable'}
                    >
                      {trigger.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                    </button>
                  </td>
                  <td>
                    <span className={`severity-indicator severity-${getSeverityColor(trigger.severity)}`}>
                      {trigger.severity}
                    </span>
                  </td>
                  <td>
                    <div className="trigger-name-cell">
                      <strong>{trigger.name}</strong>
                      {trigger.template_name && (
                        <span className="template-tag">{trigger.template_name}</span>
                      )}
                    </div>
                  </td>
                  <td className="expression-cell">
                    <code>{trigger.expression}</code>
                  </td>
                  <td className="text-right">
                    <div className="action-buttons">
                      <button className="icon-btn" title="Edit" onClick={() => handleOpenEdit(trigger)}>
                        <Edit2 size={16} />
                      </button>
                      <button className="icon-btn delete" title="Delete" onClick={() => setDeleteId(trigger.id)}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal glass wide" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>{editingTrigger ? 'Edit Trigger' : 'Create Trigger'}</h2>
              <button className="icon-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              <div className="form-row">
                <div className="form-group flex-2">
                  <label>Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., High CPU Usage on {HOST.NAME}"
                  />
                </div>
                <div className="form-group flex-1">
                  <label>Severity</label>
                  <select
                    value={formData.severity}
                    onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                  >
                    {SEVERITIES.map(s => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Expression *</label>
                <input
                  type="text"
                  value={formData.expression}
                  onChange={(e) => setFormData({ ...formData, expression: e.target.value })}
                  placeholder="e.g., {host:cpu.load}>80"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optional description..."
                  rows={2}
                />
              </div>
            </div>
            <footer className="modal-footer">
              <button className="secondary-btn" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={handleSave} disabled={saving || !formData.name.trim() || !formData.expression.trim()}>
                {saving ? <><Loader2 size={16} className="spin" /> Saving...</> : 'Save'}
              </button>
            </footer>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteId && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal glass small" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>Delete Trigger</h2>
            </header>
            <div className="modal-body">
              <p>Are you sure you want to delete this trigger?</p>
            </div>
            <footer className="modal-footer">
              <button className="secondary-btn" onClick={() => setDeleteId(null)}>Cancel</button>
              <button className="danger-btn" onClick={() => handleDelete(deleteId)}>Delete</button>
            </footer>
          </div>
        </div>
      )}

      <style>{`
        .mb-4 { margin-bottom: 2rem; }
        .text-right { text-align: right; }
        .text-dim { color: var(--text-dim); }

        .primary-btn {
          background: var(--accent-primary);
          color: white;
          border: none;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.25rem;
          font-weight: 600;
          cursor: pointer;
        }
        .primary-btn:hover { background: #059669; box-shadow: var(--glow-green); }
        .primary-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .primary-btn.small { padding: 0.5rem 1rem; font-size: 0.875rem; }

        .secondary-btn {
          background: rgba(255,255,255,0.1);
          color: var(--text-main);
          border: var(--glass-border);
          padding: 0.75rem 1.25rem;
          font-weight: 500;
          cursor: pointer;
        }
        .secondary-btn:hover { background: rgba(255,255,255,0.15); }

        .danger-btn {
          background: var(--accent-error);
          color: white;
          border: none;
          padding: 0.75rem 1.25rem;
          font-weight: 600;
          cursor: pointer;
        }
        .danger-btn:hover { background: #dc2626; }

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
        }

        .search-box {
          position: relative;
          flex: 1;
        }
        .search-icon {
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--text-dim);
        }
        .search-box input {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: var(--glass-border);
          border-radius: 8px;
          padding: 0.6rem 1rem 0.6rem 2.5rem;
          color: var(--text-main);
          outline: none;
        }
        .search-box input:focus { border-color: var(--accent-secondary); }

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

        .toggle-btn {
          background: none;
          border: none;
          color: var(--text-dim);
          cursor: pointer;
          padding: 0.25rem;
        }
        .toggle-btn.active { color: var(--accent-primary); }
        .toggle-btn:hover { color: var(--text-main); }

        .trigger-name-cell { display: flex; flex-direction: column; gap: 0.25rem; }
        .template-tag { font-size: 0.75rem; color: var(--text-dim); }

        .expression-cell code {
          font-family: 'Fira Code', monospace;
          font-size: 0.8rem;
          background: rgba(255, 255, 255, 0.05);
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          color: var(--accent-secondary);
        }

        .action-buttons { display: flex; justify-content: flex-end; gap: 0.5rem; }

        .icon-btn {
          padding: 0.4rem;
          background: transparent;
          border: none;
          color: var(--text-muted);
          border-radius: 6px;
          cursor: pointer;
        }
        .icon-btn:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-main); }
        .icon-btn.delete:hover { color: var(--accent-error); background: rgba(239, 68, 68, 0.1); }

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
          max-width: 480px;
          border-radius: 16px;
          overflow: hidden;
        }
        .modal.wide { max-width: 600px; }
        .modal.small { max-width: 360px; }

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

        .form-row { display: flex; gap: 1rem; }
        .flex-1 { flex: 1; }
        .flex-2 { flex: 2; }

        .form-group { margin-bottom: 1.25rem; }
        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          color: var(--text-muted);
        }
        .form-group input, .form-group textarea, .form-group select {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: var(--glass-border);
          border-radius: 8px;
          padding: 0.75rem 1rem;
          color: var(--text-main);
          outline: none;
          resize: vertical;
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus { border-color: var(--accent-secondary); }
      `}</style>
    </div>
  );
};

export default Triggers;
