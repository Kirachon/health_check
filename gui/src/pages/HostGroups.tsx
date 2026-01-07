import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
    Layers,
    Plus,
    Search,
    Server,
    Edit2,
    Trash2,
    X,
    Loader2,
    AlertCircle
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

interface HostGroup {
    id: string;
    name: string;
    description: string | null;
    device_count: number;
    created_at: string;
    updated_at: string;
}

interface HostGroupFormData {
    name: string;
    description: string;
}

const HostGroups: React.FC = () => {
    const [groups, setGroups] = useState<HostGroup[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingGroup, setEditingGroup] = useState<HostGroup | null>(null);
    const [formData, setFormData] = useState<HostGroupFormData>({ name: '', description: '' });
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);

    const fetchGroups = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiClient.listHostGroups({ search: searchTerm || undefined });
            setGroups(response.host_groups);
        } catch (err) {
            setError('Failed to load host groups');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [searchTerm]);

    useEffect(() => {
        const debounce = setTimeout(fetchGroups, 300);
        return () => clearTimeout(debounce);
    }, [fetchGroups]);

    const handleOpenCreate = () => {
        setEditingGroup(null);
        setFormData({ name: '', description: '' });
        setShowModal(true);
    };

    const handleOpenEdit = (group: HostGroup) => {
        setEditingGroup(group);
        setFormData({ name: group.name, description: group.description || '' });
        setShowModal(true);
    };

    const handleSave = async () => {
        if (!formData.name.trim()) return;

        setSaving(true);
        try {
            if (editingGroup) {
                await apiClient.updateHostGroup(editingGroup.id, {
                    name: formData.name,
                    description: formData.description || undefined
                });
            } else {
                await apiClient.createHostGroup({
                    name: formData.name,
                    description: formData.description || undefined
                });
            }
            setShowModal(false);
            fetchGroups();
        } catch (err: unknown) {
            setError(getErrorMessage(err, 'Failed to save host group'));
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await apiClient.deleteHostGroup(id);
            setDeleteId(null);
            fetchGroups();
        } catch (err: unknown) {
            setError(getErrorMessage(err, 'Failed to delete host group'));
        }
    };

    return (
        <div className="enterprise-container">
            <header className="page-header">
                <div className="page-title-group">
                    <h1>Host Groups</h1>
                    <p className="page-description">Organize monitored resources into logical collections for policy application and access control.</p>
                </div>
                <button className="primary-btn" onClick={handleOpenCreate}>
                    <Plus size={18} />
                    Create Group
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
                        placeholder="Search host groups..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="glass-table-container">
                {loading ? (
                    <div className="loading-state">
                        <Loader2 size={24} className="spin" />
                        <span>Loading host groups...</span>
                    </div>
                ) : groups.length === 0 ? (
                    <div className="empty-state">
                        <Layers size={48} className="empty-icon" />
                        <h3>No host groups found</h3>
                        <p>Create your first host group to organize your monitored devices.</p>
                        <button className="primary-btn small" onClick={handleOpenCreate}>
                            <Plus size={16} /> Create Group
                        </button>
                    </div>
                ) : (
                    <table className="enterprise-table">
                        <thead>
                            <tr>
                                <th>Group Name</th>
                                <th>Description</th>
                                <th>Host Count</th>
                                <th className="text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {groups.map((group) => (
                                <tr key={group.id}>
                                    <td>
                                        <div className="group-name-cell">
                                            <Layers size={18} className="mr-3 text-blue" />
                                            <strong>{group.name}</strong>
                                        </div>
                                    </td>
                                    <td className="text-dim">{group.description || '—'}</td>
                                    <td>
                                        <div className="host-count-cell">
                                            <Server size={14} className="mr-2 text-dim" />
                                            {group.device_count} Hosts
                                        </div>
                                    </td>
                                    <td className="text-right">
                                        <div className="action-buttons">
                                            <button className="icon-btn" title="Edit" onClick={() => handleOpenEdit(group)}>
                                                <Edit2 size={16} />
                                            </button>
                                            <button className="icon-btn delete" title="Delete" onClick={() => setDeleteId(group.id)}>
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
                            <h2>{editingGroup ? 'Edit Host Group' : 'Create Host Group'}</h2>
                            <button className="icon-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
                        </header>
                        <div className="modal-body">
                            <div className="form-group">
                                <label>Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    placeholder="e.g., Linux Production Servers"
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Optional description..."
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
                            <h2>Delete Host Group</h2>
                        </header>
                        <div className="modal-body">
                            <p>Are you sure you want to delete this host group? This action cannot be undone.</p>
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
        .text-dim { color: var(--text-dim); }
        .mr-2 { margin-right: 0.5rem; }
        .mr-3 { margin-right: 0.75rem; }

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

        .group-name-cell, .host-count-cell { display: flex; align-items: center; }

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
        .form-group input, .form-group textarea {
          width: 100%;
          background: rgba(255, 255, 255, 0.05);
          border: var(--glass-border);
          border-radius: 8px;
          padding: 0.75rem 1rem;
          color: var(--text-main);
          outline: none;
          resize: vertical;
        }
        .form-group input:focus, .form-group textarea:focus { border-color: var(--accent-secondary); }
      `}</style>
        </div>
    );
};

export default HostGroups;
