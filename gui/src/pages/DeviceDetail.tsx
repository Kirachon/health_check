import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { apiClient } from '../api/client';
import '../styles/DeviceDetail.css';

interface Device {
    id: string;
    hostname: string;
    ip: string;
    os: string;
    status: string;
    last_seen: string | null;
}

const DeviceDetail: React.FC = () => {
    const { deviceId } = useParams<{ deviceId: string }>();
    const [device, setDevice] = useState<Device | null>(null);
    const [cpuData, setCpuData] = useState<any[]>([]);
    const [memoryData, setMemoryData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        if (!deviceId) return;

        const fetchData = async () => {
            try {
                // Fetch device details
                const deviceData = await apiClient.getDevice(deviceId);
                setDevice(deviceData);

                // Fetch metrics (last hour)
                const end = new Date().toISOString();
                const start = new Date(Date.now() - 3600000).toISOString();

                // CPU metrics
                try {
                    const cpuResponse = await apiClient.queryRangeMetrics(
                        `cpu_percent{device_id="${deviceId}"}`,
                        start,
                        end
                    );
                    if (cpuResponse.data?.result?.[0]?.values) {
                        const formatted = cpuResponse.data.result[0].values.map(([timestamp, value]: [number, string]) => ({
                            time: new Date(timestamp * 1000).toLocaleTimeString(),
                            value: parseFloat(value),
                        }));
                        setCpuData(formatted);
                    }
                } catch (err) {
                    console.warn('No CPU data available yet');
                }

                // Memory metrics
                try {
                    const memResponse = await apiClient.queryRangeMetrics(
                        `memory_percent{device_id="${deviceId}"}`,
                        start,
                        end
                    );
                    if (memResponse.data?.result?.[0]?.values) {
                        const formatted = memResponse.data.result[0].values.map(([timestamp, value]: [number, string]) => ({
                            time: new Date(timestamp * 1000).toLocaleTimeString(),
                            value: parseFloat(value),
                        }));
                        setMemoryData(formatted);
                    }
                } catch (err) {
                    console.warn('No memory data available yet');
                }
            } catch (error) {
                console.error('Failed to fetch device data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, [deviceId]);

    if (loading) {
        return <div className="loading">Loading device details...</div>;
    }

    if (!device) {
        return <div className="error">Device not found</div>;
    }

    return (
        <div className="device-detail-container">
            <header className="detail-header">
                <button onClick={() => navigate('/dashboard')} className="back-button">
                    ← Back to Dashboard
                </button>
                <h1>{device.hostname}</h1>
            </header>

            <div className="device-info-panel">
                <div className="info-item">
                    <span className="info-label">Status:</span>
                    <span className={`status-badge ${device.status}`}>{device.status}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">IP Address:</span>
                    <span>{device.ip}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">Operating System:</span>
                    <span>{device.os}</span>
                </div>
            </div>

            <div className="charts-container">
                <div className="chart-card">
                    <h3>CPU Usage (%)</h3>
                    {cpuData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={cpuData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="value" stroke="#8b5cf6" name="CPU %" />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="no-data">No CPU data available yet</div>
                    )}
                </div>

                <div className="chart-card">
                    <h3>Memory Usage (%)</h3>
                    {memoryData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={memoryData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="value" stroke="#10b981" name="Memory %" />
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="no-data">No memory data available yet</div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DeviceDetail;
