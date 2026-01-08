import React, { useState, useEffect } from 'react';
import {
    Clock, Plus, Calendar, Trash2, Edit, Power, PowerOff,
    Server, Layers, Globe, CheckCircle, AlertTriangle
} from 'lucide-react';
import api from '../services/api';
import '../styles/Maintenance.css';

interface MaintenanceWindow {
    id: string;
    name: string;
    description: string | null;
    start_time: string;
    end_time: string;
    recurrence: string | null;
    scope_type: 'all' | 'device' | 'hostgroup';
    device_id: string | null;
    hostgroup_id: string | null;
    collect_data: boolean;
    active: boolean;
    created_by: string | null;
    created_at: string;
    updated_at: string;
    is_active_now: boolean;
    scope_name: string | null;
}

interface Device {
    id: string;
    hostname: string;
}

interface HostGroup {
    id: string;
    name: string;
}

const Maintenance: React.FC = () => {
    const [windows, setWindows] = useState<MaintenanceWindow[]>([]);
    const [devices, setDevices] = useState<Device[]>([]);
    const [hostgroups, setHostgroups] = useState<HostGroup[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingWindow, setEditingWindow] = useState<MaintenanceWindow | null>(null);

    // Form state
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        start_time: '',
        end_time: '',
        recurrence: '',
        scope_type: 'all' as 'all' | 'device' | 'hostgroup',
        device_id: '',
        hostgroup_id: '',
        collect_data: true
    });

    const fetchData = async () => {
        try {
            setLoading(true);
            const [windowsRes, devicesRes, hostgroupsRes] = await Promise.all([
                api.get('/maintenance'),
                api.get('/devices'),
                api.get('/hostgroups')
            ]);
            setWindows(windowsRes.data);
            setDevices(devicesRes.data);
            setHostgroups(hostgroupsRes.data);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const resetForm = () => {
        setFormData({
            name: '',
            description: '',
            start_time: '',
            end_time: '',
            recurrence: '',
            scope_type: 'all',
            device_id: '',
            hostgroup_id: '',
            collect_data: true
        });
        setEditingWindow(null);
    };

    const openCreateModal = () => {
        resetForm();
        // Set default times to now and +2 hours
        const now = new Date();
        const later = new Date(now.getTime() + 2 * 60 * 60 * 1000);
        setFormData(prev => ({
            ...prev,
            start_time: now.toISOString().slice(0, 16),
            end_time: later.toISOString().slice(0, 16)
        }));
        setShowModal(true);
    };

    const openEditModal = (window: MaintenanceWindow) => {
        setEditingWindow(window);
        setFormData({
            name: window.name,
            description: window.description || '',
            start_time: window.start_time.slice(0, 16),
            end_time: window.end_time.slice(0, 16),
            recurrence: window.recurrence || '',
            scope_type: window.scope_type,
            device_id: window.device_id || '',
            hostgroup_id: window.hostgroup_id || '',
            collect_data: window.collect_data
        });
        setShowModal(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const payload = {
                ...formData,
                device_id: formData.scope_type === 'device' ? formData.device_id : null,
                hostgroup_id: formData.scope_type === 'hostgroup' ? formData.hostgroup_id : null,
                recurrence: formData.recurrence || null
            };

            if (editingWindow) {
                await api.put(`/maintenance/${editingWindow.id}`, payload);
            } else {
                await api.post('/maintenance', payload);
            }

            setShowModal(false);
            resetForm();
            fetchData();
        } catch (error) {
            console.error('Failed to save maintenance window:', error);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm('Are you sure you want to delete this maintenance window?')) return;
        try {
            await api.delete(`/maintenance/${id}`);
            fetchData();
        } catch (error) {
            console.error('Failed to delete:', error);
        }
    };

    const handleDeactivate = async (id: string) => {
        try {
            await api.post(`/maintenance/${id}/deactivate`);
            fetchData();
        } catch (error) {
            console.error('Failed to deactivate:', error);
        }
    };

    const getScopeIcon = (scope: string) => {
        switch (scope) {
            case 'device': return <Server size={16} />;
            case 'hostgroup': return <Layers size={16} />;
            default: return <Globe size={16} />;
        }
    };

    const formatDateTime = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    const activeWindows = windows.filter(w => w.is_active_now);
    const upcomingWindows = windows.filter(w => !w.is_active_now && w.active);
    const inactiveWindows = windows.filter(w => !w.active);

    if (loading) {
        return <div className="maintenance-loading">Loading...</div>;
    }

    return (
        <div className="maintenance-page">
            <div className="maintenance-header">
                <div className="header-content">
                    <Clock size={32} className="header-icon" />
                    <div>
                        <h1>Maintenance Windows</h1>
                        <p>Schedule downtime to suppress alerts during planned maintenance</p>
                    </div>
                </div>
                <button className="btn-primary" onClick={openCreateModal}>
                    <Plus size={20} />
                    New Window
                </button>
            </div>

            {/* Active Now Section */}
            {activeWindows.length > 0 && (
                <div className="section active-section">
                    <h2><Power size={20} /> Currently Active</h2>
                    <div className="window-grid">
                        {activeWindows.map(window => (
                            <div key={window.id} className="window-card active-card">
                                <div className="card-header">
                                    <div className="card-title">
                                        <CheckCircle size={18} className="status-icon active" />
                                        {window.name}
                                    </div>
                                    <div className="card-actions">
                                        <button onClick={() => handleDeactivate(window.id)} title="End Maintenance">
                                            <PowerOff size={16} />
                                        </button>
                                    </div>
                                </div>
                                <div className="card-body">
                                    <div className="scope-badge">
                                        {getScopeIcon(window.scope_type)}
                                        {window.scope_name || window.scope_type}
                                    </div>
                                    <div className="time-range">
                                        <Calendar size={14} />
                                        {formatDateTime(window.start_time)} - {formatDateTime(window.end_time)}
                                    </div>
                                    {window.recurrence && (
                                        <div className="recurrence-badge">
                                            Recurring: {window.recurrence}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upcoming Section */}
            <div className="section">
                <h2><Calendar size={20} /> Scheduled Windows</h2>
                {upcomingWindows.length === 0 ? (
                    <div className="empty-state">
                        <Clock size={48} />
                        <p>No upcoming maintenance windows scheduled</p>
                    </div>
                ) : (
                    <div className="window-grid">
                        {upcomingWindows.map(window => (
                            <div key={window.id} className="window-card">
                                <div className="card-header">
                                    <div className="card-title">{window.name}</div>
                                    <div className="card-actions">
                                        <button onClick={() => openEditModal(window)} title="Edit">
                                            <Edit size={16} />
                                        </button>
                                        <button onClick={() => handleDelete(window.id)} title="Delete" className="delete-btn">
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>
                                <div className="card-body">
                                    {window.description && (
                                        <p className="description">{window.description}</p>
                                    )}
                                    <div className="scope-badge">
                                        {getScopeIcon(window.scope_type)}
                                        {window.scope_name || window.scope_type}
                                    </div>
                                    <div className="time-range">
                                        <Calendar size={14} />
                                        {formatDateTime(window.start_time)} - {formatDateTime(window.end_time)}
                                    </div>
                                    {window.recurrence && (
                                        <div className="recurrence-badge">
                                            Recurring: {window.recurrence}
                                        </div>
                                    )}
                                    {!window.collect_data && (
                                        <div className="no-data-badge">
                                            <AlertTriangle size={14} />
                                            No data collection
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Inactive Section */}
            {inactiveWindows.length > 0 && (
                <div className="section inactive-section">
                    <h2><PowerOff size={20} /> Inactive / Past Windows</h2>
                    <div className="window-list">
                        {inactiveWindows.slice(0, 10).map(window => (
                            <div key={window.id} className="window-row">
                                <span className="name">{window.name}</span>
                                <span className="scope">{window.scope_name || window.scope_type}</span>
                                <span className="time">{formatDateTime(window.end_time)}</span>
                                <button onClick={() => handleDelete(window.id)} className="delete-btn">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Modal */}
            {showModal && (
                <div className="modal-overlay" onClick={() => setShowModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2>{editingWindow ? 'Edit' : 'New'} Maintenance Window</h2>
                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label>Name *</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                                    required
                                    placeholder="e.g., Weekly Server Maintenance"
                                />
                            </div>

                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={formData.description}
                                    onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                                    placeholder="Optional description"
                                    rows={2}
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label>Start Time *</label>
                                    <input
                                        type="datetime-local"
                                        value={formData.start_time}
                                        onChange={e => setFormData(prev => ({ ...prev, start_time: e.target.value }))}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label>End Time *</label>
                                    <input
                                        type="datetime-local"
                                        value={formData.end_time}
                                        onChange={e => setFormData(prev => ({ ...prev, end_time: e.target.value }))}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Recurrence (Cron Expression)</label>
                                <input
                                    type="text"
                                    value={formData.recurrence}
                                    onChange={e => setFormData(prev => ({ ...prev, recurrence: e.target.value }))}
                                    placeholder="e.g., 0 2 * * 0 (Sundays at 2 AM) - Leave empty for one-time"
                                />
                            </div>

                            <div className="form-group">
                                <label>Scope *</label>
                                <select
                                    value={formData.scope_type}
                                    onChange={e => setFormData(prev => ({
                                        ...prev,
                                        scope_type: e.target.value as 'all' | 'device' | 'hostgroup',
                                        device_id: '',
                                        hostgroup_id: ''
                                    }))}
                                >
                                    <option value="all">All Devices</option>
                                    <option value="device">Specific Device</option>
                                    <option value="hostgroup">Host Group</option>
                                </select>
                            </div>

                            {formData.scope_type === 'device' && (
                                <div className="form-group">
                                    <label>Device *</label>
                                    <select
                                        value={formData.device_id}
                                        onChange={e => setFormData(prev => ({ ...prev, device_id: e.target.value }))}
                                        required
                                    >
                                        <option value="">Select a device...</option>
                                        {devices.map(d => (
                                            <option key={d.id} value={d.id}>{d.hostname}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {formData.scope_type === 'hostgroup' && (
                                <div className="form-group">
                                    <label>Host Group *</label>
                                    <select
                                        value={formData.hostgroup_id}
                                        onChange={e => setFormData(prev => ({ ...prev, hostgroup_id: e.target.value }))}
                                        required
                                    >
                                        <option value="">Select a host group...</option>
                                        {hostgroups.map(hg => (
                                            <option key={hg.id} value={hg.id}>{hg.name}</option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            <div className="form-group checkbox-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        checked={formData.collect_data}
                                        onChange={e => setFormData(prev => ({ ...prev, collect_data: e.target.checked }))}
                                    />
                                    Continue collecting data during maintenance
                                </label>
                                <small>When disabled, no metrics will be recorded during this window</small>
                            </div>

                            <div className="modal-actions">
                                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn-primary">
                                    {editingWindow ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Maintenance;
