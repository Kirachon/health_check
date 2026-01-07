import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import DeviceCard from '../components/DeviceCard';
import '../styles/Dashboard.css';

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
    const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all');
    const { logout } = useAuth();
    const navigate = useNavigate();

    const fetchDevices = async () => {
        try {
            const params = filter !== 'all' ? { status: filter } : {};
            const data = await apiClient.listDevices(params);
            setDevices(data.devices);
        } catch (error) {
            console.error('Failed to fetch devices:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDevices();
        // Auto-refresh every 30 seconds
        const interval = setInterval(fetchDevices, 30000);
        return () => clearInterval(interval);
    }, [filter]);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const handleDeleteDevice = async (deviceId: string) => {
        if (window.confirm('Are you sure you want to delete this device?')) {
            try {
                await apiClient.deleteDevice(deviceId);
                fetchDevices();
            } catch (error) {
                console.error('Failed to delete device:', error);
            }
        }
    };

    const filteredCount = {
        all: devices.length,
        online: devices.filter(d => d.status === 'online').length,
        offline: devices.filter(d => d.status === 'offline').length,
    };

    return (
        <div className="dashboard-container">
            <header className="dashboard-header">
                <h1>Health Monitor Dashboard</h1>
                <button onClick={handleLogout} className="logout-button">
                    Logout
                </button>
            </header>

            <div className="dashboard-stats">
                <div className="stat-card">
                    <h3>Total Devices</h3>
                    <p className="stat-value">{filteredCount.all}</p>
                </div>
                <div className="stat-card online">
                    <h3>Online</h3>
                    <p className="stat-value">{filteredCount.online}</p>
                </div>
                <div className="stat-card offline">
                    <h3>Offline</h3>
                    <p className="stat-value">{filteredCount.offline}</p>
                </div>
            </div>

            <div className="filter-controls">
                <button
                    className={filter === 'all' ? 'active' : ''}
                    onClick={() => setFilter('all')}
                >
                    All Devices
                </button>
                <button
                    className={filter === 'online' ? 'active' : ''}
                    onClick={() => setFilter('online')}
                >
                    Online Only
                </button>
                <button
                    className={filter === 'offline' ? 'active' : ''}
                    onClick={() => setFilter('offline')}
                >
                    Offline Only
                </button>
            </div>

            {loading ? (
                <div className="loading">Loading devices...</div>
            ) : devices.length === 0 ? (
                <div className="empty-state">
                    <h3>No devices found</h3>
                    <p>Register a device using the agent to get started</p>
                </div>
            ) : (
                <div className="devices-grid">
                    {devices.map((device) => (
                        <DeviceCard
                            key={device.id}
                            device={device}
                            onDelete={() => handleDeleteDevice(device.id)}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default Dashboard;
