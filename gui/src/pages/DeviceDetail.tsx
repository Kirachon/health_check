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

interface MetricPoint {
    time: string;
    value: number;
}

interface VmVectorSeries {
    metric?: Record<string, string>;
    value?: [number, string];
}

interface StorageRow {
    id: string;
    label: string;
    percent?: number;
    totalGb?: number;
    usedGb?: number;
    freeGb?: number;
    readMb?: number;
    writeMb?: number;
    readTimeMs?: number;
    writeTimeMs?: number;
    busyTimeMs?: number;
    busyPercentOfUptime?: number;
}

const formatDuration = (totalSeconds: number) => {
    const seconds = Math.max(0, Math.floor(totalSeconds));
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
};

const parseVmInstant = (series: VmVectorSeries | undefined) => {
    const raw = series?.value?.[1];
    const parsed = typeof raw === 'string' ? parseFloat(raw) : Number(raw);
    return Number.isFinite(parsed) ? parsed : undefined;
};

const storageLabelFromSuffix = (suffix: string) => {
    const trimmed = suffix.replace(/_+$/g, '');
    if (!trimmed) return '/';
    if (trimmed.startsWith('_')) return trimmed.replace(/_/g, '/');
    return trimmed;
};

const getStorageIndicator = (d: StorageRow) => {
    const hasCapacity = d.percent != null || d.totalGb != null || d.usedGb != null || d.freeGb != null;
    const hasIo =
        d.readMb != null ||
        d.writeMb != null ||
        d.busyTimeMs != null ||
        d.readTimeMs != null ||
        d.writeTimeMs != null;

    if (hasCapacity) return { color: '#10b981', label: 'Reporting (volume)' }; // green
    if (hasIo) return { color: '#f59e0b', label: 'Reporting (disk I/O only)' }; // amber
    return { color: '#ef4444', label: 'No data' }; // red
};

const formatLastSeen = (lastSeen: string | null) => {
    if (!lastSeen) return 'Never';
    const date = new Date(lastSeen);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return `${Math.floor(diffMins / 1440)}d ago`;
};

const DeviceDetail: React.FC = () => {
    const { deviceId } = useParams<{ deviceId: string }>();
    const [device, setDevice] = useState<Device | null>(null);
    const [cpuData, setCpuData] = useState<MetricPoint[]>([]);
    const [memoryData, setMemoryData] = useState<MetricPoint[]>([]);
    const [uptimeSeconds, setUptimeSeconds] = useState<number | null>(null);
    const [storage, setStorage] = useState<StorageRow[]>([]);
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
                let uptimeSecondsLocal: number | null = null;

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
                } catch {
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
                } catch {
                    console.warn('No memory data available yet');
                }

                // Uptime (latest)
                try {
                    const uptimeResponse = await apiClient.queryMetrics(
                        `system_uptime_seconds{device_id="${deviceId}"}`
                    );
                    const parsed = parseVmInstant(uptimeResponse.data?.result?.[0] as VmVectorSeries | undefined);
                    uptimeSecondsLocal = parsed ?? null;
                    setUptimeSeconds(uptimeSecondsLocal);
                } catch {
                    // Optional metric
                    uptimeSecondsLocal = null;
                    setUptimeSeconds(null);
                }

                // Storage usage (latest)
                try {
                    const [percentResp, totalResp, usedResp, freeResp, bytesReadResp, bytesWriteResp, ioReadResp, ioWriteResp, ioBusyResp] = await Promise.all([
                        apiClient.queryMetrics(`{__name__=~"disk_percent_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_total_gb_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_used_gb_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_free_gb_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_read_bytes_mb(_.*)?",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_write_bytes_mb(_.*)?",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_read_time_ms_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_write_time_ms_.*",device_id="${deviceId}"}`),
                        apiClient.queryMetrics(`{__name__=~"disk_busy_time_ms_.*",device_id="${deviceId}"}`),
                    ]);

                    const byId = new Map<string, StorageRow>();

                    const upsert = (id: string, patch: Partial<StorageRow>) => {
                        const existing = byId.get(id) ?? { id, label: storageLabelFromSuffix(id) };
                        byId.set(id, { ...existing, ...patch });
                    };

                    const handleSeries = (
                        response: { data?: { result?: VmVectorSeries[] } } | undefined,
                        prefix: string,
                        key: keyof Pick<StorageRow, 'percent' | 'totalGb' | 'usedGb' | 'freeGb'>
                    ) => {
                        const series = response?.data?.result ?? [];
                        for (const s of series) {
                            const name = s.metric?.__name__ ?? '';
                            if (!name.startsWith(prefix)) continue;
                            const suffix = name.slice(prefix.length);
                            const val = parseVmInstant(s);
                            if (val === undefined) continue;
                            upsert(suffix, { [key]: val } as Partial<StorageRow>);
                        }
                    };

                    handleSeries(percentResp, 'disk_percent_', 'percent');
                    handleSeries(totalResp, 'disk_total_gb_', 'totalGb');
                    handleSeries(usedResp, 'disk_used_gb_', 'usedGb');
                    handleSeries(freeResp, 'disk_free_gb_', 'freeGb');
                    handleSeries(bytesReadResp, 'disk_read_bytes_mb_', 'readMb');
                    handleSeries(bytesWriteResp, 'disk_write_bytes_mb_', 'writeMb');
                    handleSeries(ioReadResp, 'disk_read_time_ms_', 'readTimeMs');
                    handleSeries(ioWriteResp, 'disk_write_time_ms_', 'writeTimeMs');
                    handleSeries(ioBusyResp, 'disk_busy_time_ms_', 'busyTimeMs');

                    // Derive how much of the system uptime a disk has been "busy" (proxy for storage uptime/activity)
                    const uptimeMs = uptimeSecondsLocal == null ? undefined : uptimeSecondsLocal * 1000;
                    if (uptimeMs && uptimeMs > 0) {
                        for (const [id, row] of byId.entries()) {
                            if (row.busyTimeMs != null) {
                                byId.set(id, {
                                    ...row,
                                    busyPercentOfUptime: Math.min(100, Math.max(0, (row.busyTimeMs / uptimeMs) * 100)),
                                });
                            }
                        }
                    }

                    setStorage(Array.from(byId.values()).sort((a, b) => a.label.localeCompare(b.label)));
                } catch {
                    setStorage([]);
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
        return (
            <div className="device-detail-container">
                <div className="loading">Loading device details...</div>
            </div>
        );
    }

    if (!device) {
        return (
            <div className="device-detail-container">
                <div className="error">Device not found</div>
            </div>
        );
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
                    <span className={`device-status-badge ${device.status}`}>{device.status}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">Last Seen:</span>
                    <span>{formatLastSeen(device.last_seen)}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">IP Address:</span>
                    <span>{device.ip}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">Operating System:</span>
                    <span>{device.os}</span>
                </div>
                <div className="info-item">
                    <span className="info-label">Uptime:</span>
                    <span>{uptimeSeconds == null ? '—' : formatDuration(uptimeSeconds)}</span>
                </div>
            </div>

            <div className="charts-container">
                <div className="chart-card">
                    <h3>Storage</h3>
                    {storage.length > 0 ? (
                        <div className="device-info-panel">
                    {storage.map((d) => (
                        <div key={d.id} className="info-item">
                            {(() => {
                                const indicator = getStorageIndicator(d);
                                return (
                                    <span
                                        title={indicator.label}
                                        aria-label={indicator.label}
                                        style={{
                                            display: 'inline-block',
                                            width: 10,
                                            height: 10,
                                            borderRadius: 9999,
                                            backgroundColor: indicator.color,
                                            marginRight: 8,
                                            flex: '0 0 auto',
                                        }}
                                    />
                                );
                            })()}
                            <span className="info-label">{d.label}:</span>
                            <span>
                                {d.percent != null ? `${d.percent.toFixed(1)}%` : '—'}
                                {d.usedGb != null && d.totalGb != null
                                    ? ` (${d.usedGb.toFixed(1)} / ${d.totalGb.toFixed(1)} GB)`
                                            : ''}
                                        {d.freeGb != null ? `, free ${d.freeGb.toFixed(1)} GB` : ''}
                                    </span>
                                    {(d.readMb != null || d.writeMb != null) && (
                                        <span style={{ display: 'block', fontSize: '0.9em', opacity: 0.85 }}>
                                            Bytes since boot:
                                            {d.readMb != null ? ` read ${d.readMb.toFixed(0)} MB` : ''}
                                            {d.writeMb != null ? `, write ${d.writeMb.toFixed(0)} MB` : ''}
                                        </span>
                                    )}
                                    {(d.busyTimeMs != null || d.readTimeMs != null || d.writeTimeMs != null) && (
                                        <span style={{ display: 'block', fontSize: '0.9em', opacity: 0.85 }}>
                                            I/O time since boot:
                                            {d.busyTimeMs != null ? ` busy ${(d.busyTimeMs / 1000 / 60).toFixed(1)}m` : ''}
                                            {d.readTimeMs != null ? `, read ${(d.readTimeMs / 1000 / 60).toFixed(1)}m` : ''}
                                            {d.writeTimeMs != null ? `, write ${(d.writeTimeMs / 1000 / 60).toFixed(1)}m` : ''}
                                            {d.busyPercentOfUptime != null ? ` (${d.busyPercentOfUptime.toFixed(1)}% of uptime)` : ''}
                                        </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="no-data">No storage data available yet</div>
                    )}
                </div>
                <div className="chart-card">
                    <h3>CPU Usage (%)</h3>
                    {cpuData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={cpuData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)' }} />
                                <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)' }} />
                                <Tooltip
                                    contentStyle={{
                                        background: 'rgba(15, 23, 42, 0.92)',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        borderRadius: 8,
                                        color: 'var(--text-main)',
                                    }}
                                    labelStyle={{ color: 'var(--text-muted)' }}
                                />
                                <Legend wrapperStyle={{ color: 'var(--text-muted)' }} />
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
                                <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)' }} />
                                <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-muted)' }} />
                                <Tooltip
                                    contentStyle={{
                                        background: 'rgba(15, 23, 42, 0.92)',
                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                        borderRadius: 8,
                                        color: 'var(--text-main)',
                                    }}
                                    labelStyle={{ color: 'var(--text-muted)' }}
                                />
                                <Legend wrapperStyle={{ color: 'var(--text-muted)' }} />
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
