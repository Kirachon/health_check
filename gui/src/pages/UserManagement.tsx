import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
    Plus,
    Search,
    ShieldCheck,
    Lock,
    User,
    Edit2,
    Trash2,
    ShieldHalf,
    X,
    Loader2,
    AlertCircle,
    Key
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

interface UserRecord {
    id: string;
    username: string;
    role: 'admin' | 'sre' | 'viewer';
    created_at: string;
    updated_at: string;
}

interface UserFormData {
    username: string;
    password: string;
    role: 'admin' | 'sre' | 'viewer';
}

const UserManagement: React.FC = () => {
    const [users, setUsers] = useState<UserRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
    const [formData, setFormData] = useState<UserFormData>({ username: '', password: '', role: 'viewer' });
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);
    const [resetPasswordId, setResetPasswordId] = useState<string | null>(null);
    const [newPassword, setNewPassword] = useState('');

    const fetchUsers = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiClient.listUsers({ search: searchTerm || undefined });
            setUsers(response.users);
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to load users'));
        } finally {
            setLoading(false);
        }
    }, [searchTerm]);

    useEffect(() => {
        const debounce = setTimeout(fetchUsers, 300);
        return () => clearTimeout(debounce);
    }, [fetchUsers]);

    const handleOpenCreate = () => {
        setEditingUser(null);
        setFormData({ username: '', password: '', role: 'viewer' });
        setShowModal(true);
    };

    const handleOpenEdit = (user: UserRecord) => {
        setEditingUser(user);
        setFormData({ username: user.username, password: '', role: user.role });
        setShowModal(true);
    };

    const handleSave = async () => {
        if (!formData.username.trim()) return;
        if (!editingUser && !formData.password.trim()) return;

        setSaving(true);
        try {
            if (editingUser) {
                await apiClient.updateUser(editingUser.id, { role: formData.role });
            } else {
                await apiClient.createUser({
                    username: formData.username,
                    password: formData.password,
                    role: formData.role
                });
            }
            setShowModal(false);
            fetchUsers();
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to save user'));
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await apiClient.deleteUser(id);
            setDeleteId(null);
            fetchUsers();
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to delete user'));
        }
    };

    const handleResetPassword = async () => {
        if (!resetPasswordId || !newPassword.trim()) return;
        try {
            await apiClient.resetUserPassword(resetPasswordId, newPassword);
            setResetPasswordId(null);
            setNewPassword('');
            setError(null);
        } catch (err) {
            setError(getErrorMessage(err, 'Failed to reset password'));
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <div className="enterprise-container">
            <header className="page-header">
                <div className="page-title-group">
                    <h1>User Management</h1>
                    <p className="page-description">Manage user accounts, roles, and access permissions for the health monitoring system.</p>
                </div>
                <button className="primary-btn" onClick={handleOpenCreate}>
                    <Plus size={18} />
                    Add User
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
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="glass-table-container">
                {loading ? (
                    <div className="loading-state">
                        <Loader2 size={24} className="spin" />
                        <span>Loading users...</span>
                    </div>
                ) : users.length === 0 ? (
                    <div className="empty-state">
                        <User size={48} className="empty-icon" />
                        <h3>No users found</h3>
                        <p>Create your first user to get started.</p>
                        <button className="primary-btn small" onClick={handleOpenCreate}>
                            <Plus size={16} /> Add User
                        </button>
                    </div>
                ) : (
                    <table className="enterprise-table">
                        <thead>
                            <tr>
                                <th>User</th>
                                <th>Role</th>
                                <th>Created</th>
                                <th className="text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((user) => (
                                <tr key={user.id}>
                                    <td>
                                        <div className="user-info-cell">
                                            <div className="avatar-placeholder">
                                                <User size={16} />
                                            </div>
                                            <strong>{user.username}</strong>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="role-cell">
                                            {user.role === 'admin' && <ShieldCheck size={16} className="mr-2 text-red" />}
                                            {user.role === 'sre' && <ShieldHalf size={16} className="mr-2 text-amber" />}
                                            {user.role === 'viewer' && <Lock size={16} className="mr-2 text-blue" />}
                                            <span className="capitalize">{user.role}</span>
                                        </div>
                                    </td>
                                    <td className="text-muted text-sm">{formatDate(user.created_at)}</td>
                                    <td className="text-right">
                                        <div className="action-buttons">
                                            <button className="icon-btn" title="Reset Password" onClick={() => setResetPasswordId(user.id)}>
                                                <Key size={16} />
                                            </button>
                                            <button className="icon-btn" title="Edit Role" onClick={() => handleOpenEdit(user)}>
                                                <Edit2 size={16} />
                                            </button>
                                            <button className="icon-btn delete" title="Delete User" onClick={() => setDeleteId(user.id)}>
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
                            <h2>{editingUser ? 'Edit User Role' : 'Create User'}</h2>
                            <button className="icon-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
                        </header>
                        <div className="modal-body">
                            {!editingUser && (
                                <>
                                    <div className="form-group">
                                        <label>Username *</label>
                                        <input
                                            type="text"
                                            value={formData.username}
                                            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                            placeholder="e.g., john_doe"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Password *</label>
                                        <input
                                            type="password"
                                            value={formData.password}
                                            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                            placeholder="Min 8 characters"
                                        />
                                    </div>
                                </>
                            )}
                            <div className="form-group">
                                <label>Role *</label>
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value as 'admin' | 'sre' | 'viewer' })}
                                >
                                    <option value="viewer">Viewer</option>
                                    <option value="sre">SRE</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                        </div>
                        <footer className="modal-footer">
                            <button className="secondary-btn" onClick={() => setShowModal(false)}>Cancel</button>
                            <button
                                className="primary-btn"
                                onClick={handleSave}
                                disabled={saving || !formData.username.trim() || (!editingUser && !formData.password.trim())}
                            >
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
                            <h2>Delete User</h2>
                        </header>
                        <div className="modal-body">
                            <p>Are you sure you want to delete this user? This action cannot be undone.</p>
                        </div>
                        <footer className="modal-footer">
                            <button className="secondary-btn" onClick={() => setDeleteId(null)}>Cancel</button>
                            <button className="danger-btn" onClick={() => handleDelete(deleteId)}>Delete</button>
                        </footer>
                    </div>
                </div>
            )}

            {/* Reset Password Modal */}
            {resetPasswordId && (
                <div className="modal-overlay" onClick={() => { setResetPasswordId(null); setNewPassword(''); }}>
                    <div className="modal glass small" onClick={(e) => e.stopPropagation()}>
                        <header className="modal-header">
                            <h2>Reset Password</h2>
                            <button className="icon-btn" onClick={() => { setResetPasswordId(null); setNewPassword(''); }}><X size={20} /></button>
                        </header>
                        <div className="modal-body">
                            <div className="form-group">
                                <label>New Password *</label>
                                <input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    placeholder="Min 8 characters"
                                />
                            </div>
                        </div>
                        <footer className="modal-footer">
                            <button className="secondary-btn" onClick={() => { setResetPasswordId(null); setNewPassword(''); }}>Cancel</button>
                            <button className="primary-btn" onClick={handleResetPassword} disabled={newPassword.length < 8}>
                                Reset Password
                            </button>
                        </footer>
                    </div>
                </div>
            )}

            <style>{`
        .mb-4 { margin-bottom: 2rem; }
        .mr-2 { margin-right: 0.5rem; }
        .text-right { text-align: right; }
        .capitalize { text-transform: capitalize; }
        .text-sm { font-size: 0.8rem; }
        .text-red { color: var(--accent-error); }
        .text-amber { color: var(--accent-warning); }
        .text-blue { color: var(--accent-secondary); }

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

        .search-box { position: relative; flex: 1; }
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

        .user-info-cell, .role-cell { display: flex; align-items: center; }

        .avatar-placeholder {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.05);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 0.75rem;
          color: var(--text-muted);
          border: var(--glass-border);
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
        }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus { border-color: var(--accent-secondary); }
      `}</style>
        </div>
    );
};

export default UserManagement;
