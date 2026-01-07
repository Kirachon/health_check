import React, { useState } from 'react';
import {
    Plus,
    Search,
    ShieldCheck,
    Lock,
    User,
    Edit2,
    Trash2,
    ShieldHalf
} from 'lucide-react';

interface UserRecord {
    id: string;
    username: string;
    email: string;
    role: 'admin' | 'sre' | 'viewer';
    status: 'active' | 'suspended';
    lastLogin: string;
}

const mockUsers: UserRecord[] = [
    { id: '1', username: 'admin', email: 'admin@monitor.io', role: 'admin', status: 'active', lastLogin: '10 mins ago' },
    { id: '2', username: 'jdoe_sre', email: 'john@monitor.io', role: 'sre', status: 'active', lastLogin: '2 hours ago' },
    { id: '3', username: 'auditor_01', email: 'security@monitor.io', role: 'viewer', status: 'active', lastLogin: '1 day ago' },
    { id: '4', username: 'intern_dev', email: 'dev@monitor.io', role: 'viewer', status: 'suspended', lastLogin: '1 week ago' },
    { id: '5', username: 'global_sre', email: 'sre@monitor.io', role: 'sre', status: 'active', lastLogin: '3 hours ago' },
];

const UserManagement: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');

    const filteredUsers = mockUsers.filter(u =>
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="enterprise-container">
            <header className="page-header">
                <div className="page-title-group">
                    <h1>User Management</h1>
                    <p className="page-description">Manage user accounts, roles, and access permissions for the health monitoring system.</p>
                </div>
                <button className="primary-btn">
                    <Plus size={18} />
                    Add User
                </button>
            </header>

            <div className="table-controls glass mb-4">
                <div className="search-box">
                    <Search size={18} className="search-icon" />
                    <input
                        type="text"
                        placeholder="Search users or emails..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="glass-table-container">
                <table className="enterprise-table">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Role</th>
                            <th>Email</th>
                            <th>Status</th>
                            <th>Last Login</th>
                            <th className="text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredUsers.map((user) => (
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
                                <td className="text-muted">{user.email}</td>
                                <td>
                                    <span className={`badge ${user.status === 'active' ? 'badge-green' : 'badge-slate'}`}>
                                        {user.status}
                                    </span>
                                </td>
                                <td className="text-muted text-sm">{user.lastLogin}</td>
                                <td className="text-right">
                                    <div className="action-buttons">
                                        <button className="icon-btn" title="Edit Permissions"><Edit2 size={16} /></button>
                                        <button className="icon-btn delete" title="Delete User"><Trash2 size={16} /></button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

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
        }

        .primary-btn:hover {
          background: #059669;
          box-shadow: var(--glow-green);
        }

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
          transition: border-color 0.2s;
        }

        .search-box input:focus {
          border-color: var(--accent-secondary);
        }

        .user-info-cell, .role-cell {
          display: flex;
          align-items: center;
        }

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

        .action-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 0.5rem;
        }

        .icon-btn {
          padding: 0.4rem;
          background: transparent;
          border: none;
          color: var(--text-muted);
          border-radius: 6px;
        }

        .icon-btn:hover {
          background: rgba(255, 255, 255, 0.1);
          color: var(--text-main);
        }

        .icon-btn.delete:hover {
          color: var(--accent-error);
          background: rgba(239, 68, 68, 0.1);
        }
      `}</style>
        </div>
    );
};

export default UserManagement;
