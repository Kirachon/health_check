import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  Zap,
  Plus,
  Search,
  Edit2,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  Mail,
  Terminal,
  Globe
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

interface Action {
  id: string;
  name: string;
  action_type: string;
  conditions: string | null;
  enabled: boolean;
  operation_count: number;
  created_at: string;
  updated_at: string;
}

interface ActionFormData {
  name: string;
  action_type: string;
  conditions: string;
}

const ACTION_TYPES = ['notification', 'remediation', 'script'];

const Actions: React.FC = () => {
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingAction, setEditingAction] = useState<Action | null>(null);
  const [formData, setFormData] = useState<ActionFormData>({ name: '', action_type: 'notification', conditions: '' });
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const fetchActions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.listActions({ search: searchTerm || undefined });
      setActions(response.actions);
    } catch (err) {
      setError('Failed to load actions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    const debounce = setTimeout(fetchActions, 300);
    return () => clearTimeout(debounce);
  }, [fetchActions]);

  const handleOpenCreate = () => {
    setEditingAction(null);
    setFormData({ name: '', action_type: 'notification', conditions: '' });
    setShowModal(true);
  };

  const handleOpenEdit = (action: Action) => {
    setEditingAction(action);
    setFormData({
      name: action.name,
      action_type: action.action_type,
      conditions: action.conditions || ''
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;

    setSaving(true);
    try {
      if (editingAction) {
        await apiClient.updateAction(editingAction.id, {
          name: formData.name,
          action_type: formData.action_type,
          conditions: formData.conditions || undefined
        });
      } else {
        await apiClient.createAction({
          name: formData.name,
          action_type: formData.action_type,
          conditions: formData.conditions || undefined
        });
      }
      setShowModal(false);
      fetchActions();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to save action'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.deleteAction(id);
      setDeleteId(null);
      fetchActions();
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to delete action'));
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'notification': return <Mail size={16} />;
      case 'remediation': return <Terminal size={16} />;
      case 'script': return <Globe size={16} />;
      default: return <Zap size={16} />;
    }
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      notification: 'blue', remediation: 'amber', script: 'green'
    };
    return colors[type] || 'slate';
  };

  return (
    <div className="enterprise-container">
      <header className="page-header">
        <div className="page-title-group">
          <h1>Actions</h1>
          <p className="page-description">Configure automated responses to triggered alerts including notifications and remediations.</p>
        </div>
        <button className="primary-btn" onClick={handleOpenCreate}>
          <Plus size={18} />
          Create Action
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
            placeholder="Search actions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="glass-table-container">
        {loading ? (
          <div className="loading-state">
            <Loader2 size={24} className="spin" />
            <span>Loading actions...</span>
          </div>
        ) : actions.length === 0 ? (
          <div className="empty-state">
            <Zap size={48} className="empty-icon" />
            <h3>No actions found</h3>
            <p>Create your first action to automate alert responses.</p>
            <button className="primary-btn small" onClick={handleOpenCreate}>
              <Plus size={16} /> Create Action
            </button>
          </div>
        ) : (
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Name</th>
                <th>Type</th>
                <th>Operations</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((action) => (
                <tr key={action.id} className={!action.enabled ? 'disabled-row' : ''}>
                  <td>
                    <span className={`status-dot ${action.enabled ? 'active' : 'inactive'}`}></span>
                  </td>
                  <td>
                    <div className="action-name-cell">
                      <Zap size={18} className="mr-3 text-blue" />
                      <strong>{action.name}</strong>
                    </div>
                  </td>
                  <td>
                    <span className={`badge badge-${getTypeColor(action.action_type)}`}>
                      {getTypeIcon(action.action_type)}
                      <span className="ml-1">{action.action_type}</span>
                    </span>
                  </td>
                  <td>
                    <span className="operation-count">{action.operation_count} steps</span>
                  </td>
                  <td className="text-right">
                    <div className="action-buttons">
                      <button className="icon-btn" title="Edit" onClick={() => handleOpenEdit(action)}>
                        <Edit2 size={16} />
                      </button>
                      <button className="icon-btn delete" title="Delete" onClick={() => setDeleteId(action.id)}>
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
          <div className="modal glass" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>{editingAction ? 'Edit Action' : 'Create Action'}</h2>
              <button className="icon-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Notify OpsGenie on Disaster"
                />
              </div>
              <div className="form-group">
                <label>Type</label>
                <select
                  value={formData.action_type}
                  onChange={(e) => setFormData({ ...formData, action_type: e.target.value })}
                >
                  {ACTION_TYPES.map(t => (
                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Conditions (JSON)</label>
                <textarea
                  value={formData.conditions}
                  onChange={(e) => setFormData({ ...formData, conditions: e.target.value })}
                  placeholder='{"severity": ["disaster", "high"]}'
                  rows={3}
                />
              </div>
            </div>
            <footer className="modal-footer">
              <button className="secondary-btn" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={handleSave} disabled={saving || !formData.name.trim()}>
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
              <h2>Delete Action</h2>
            </header>
            <div className="modal-body">
              <p>Are you sure you want to delete this action? All associated operations will also be deleted.</p>
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
        .text-blue { color: var(--accent-secondary); }
        .mr-3 { margin-right: 0.75rem; }
        .ml-1 { margin-left: 0.25rem; }

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

        .status-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
        }
        .status-dot.active { background: var(--accent-primary); box-shadow: var(--glow-green); }
        .status-dot.inactive { background: var(--text-dim); }

        .action-name-cell { display: flex; align-items: center; }
        .operation-count { color: var(--text-dim); }

        .badge { display: inline-flex; align-items: center; }

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

export default Actions;
