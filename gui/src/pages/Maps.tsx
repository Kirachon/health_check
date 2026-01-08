import React, { useState, useEffect, useCallback } from 'react';
import {
    ReactFlow,
    Controls,
    Background,
    useNodesState,
    useEdgesState,
    addEdge,
    MarkerType,
    applyNodeChanges,
    applyEdgeChanges
} from '@xyflow/react';
import type { Connection, Edge, Node, NodeChange, EdgeChange } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
    Plus,
    Server
} from 'lucide-react';
import { apiClient } from '../api/client';

const formatAge = (seconds?: number | null) => {
    if (seconds === null || seconds === undefined) return 'last seen: —';
    if (seconds < 60) return `last seen: ${seconds}s ago`;
    if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainder = seconds % 60;
        return `last seen: ${minutes}m ${remainder}s ago`;
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `last seen: ${hours}h ${minutes}m ago`;
};

// Map Types
interface NetworkMap {
    id: string;
    name: string;
    description: string;
    width: number;
    height: number;
}

const Maps: React.FC = () => {
    // State
    const [maps, setMaps] = useState<NetworkMap[]>([]);
    const [selectedMap, setSelectedMap] = useState<string | null>(null);
    const [nodes, setNodes] = useNodesState<Node>([]);
    const [edges, setEdges] = useEdgesState<Edge>([]);
    const [_loading, setLoading] = useState(false);

    // Modal State
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newMapName, setNewMapName] = useState('');

    // Element Modal
    const [showElementModal, setShowElementModal] = useState(false);
    const [availableDevices, setAvailableDevices] = useState<any[]>([]);

    // Fetch Maps
    const fetchMaps = useCallback(async () => {
        try {
            const data = await apiClient.listMaps();
            setMaps(data);
            if (data.length > 0 && !selectedMap) {
                // Select first map by default
                setSelectedMap(data[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch maps", error);
        }
    }, [selectedMap]);

    // Fetch Status and Update Nodes
    const fetchStatus = useCallback(async () => {
        if (!selectedMap) return;
        try {
            const statusMap = await apiClient.getMapStatus(selectedMap);

            setNodes((nds) => nds.map((node) => {
                const status = statusMap[node.id];
                if (status) {
                    let borderColor = 'var(--border-color)';
                    if (status.status === 'online') borderColor = 'var(--success-color)';
                    if (status.status === 'offline') borderColor = 'var(--error-color)';

                    const baseLabel = (node.data as any)?.baseLabel || node.data?.label || 'Unknown';
                    const statusText = status.status ? String(status.status).toUpperCase() : 'UNKNOWN';
                    const ageText = formatAge(status.last_seen_age_seconds);
                    const statusColor = status.status === 'online'
                        ? 'var(--success-color)'
                        : status.status === 'offline'
                            ? 'var(--error-color)'
                            : 'var(--text-secondary)';

                    return {
                        ...node,
                        style: {
                            ...node.style,
                            border: `2px solid ${borderColor}`,
                        },
                        data: {
                            ...node.data,
                            baseLabel,
                            status,
                            label: (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <div style={{ fontWeight: 600 }}>{baseLabel}</div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                                        <span style={{ textTransform: 'uppercase', fontWeight: 600, color: statusColor }}>{statusText}</span>
                                        <span>{ageText}</span>
                                    </div>
                                </div>
                            )
                        }
                    };
                }
                return node;
            }));
        } catch (error) {
            console.error("Failed to fetch map status", error);
        }
    }, [selectedMap, setNodes]);

    // Fetch Map Details
    const fetchMapDetails = useCallback(async (mapId: string) => {
        setLoading(true);
        try {
            const mapData = await apiClient.getMap(mapId);

            // Convert elements to nodes
            const initialNodes: Node[] = mapData.elements.map((el: any) => ({
                id: el.id,
                type: 'default', // Using default node type for now
                data: {
                    label: el.label || el.device_name || 'Unknown',
                    baseLabel: el.label || el.device_name || 'Unknown',
                    device_id: el.device_id,
                    hostgroup_id: el.hostgroup_id
                },
                position: { x: el.x, y: el.y },
                style: {
                    background: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '10px',
                    width: el.width || 150,
                }
            }));

            // Convert links to edges
            const initialEdges: Edge[] = mapData.links.map((link: any) => ({
                id: link.id,
                source: link.source_element_id,
                target: link.target_element_id,
                label: link.label,
                type: 'smoothstep',
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                },
                style: { stroke: link.color || '#666' }
            }));

            setNodes(initialNodes);
            setEdges(initialEdges);

            // Initial status fetch
            setTimeout(fetchStatus, 500);

        } catch (error) {
            console.error("Failed to load map details", error);
        } finally {
            setLoading(false);
        }
    }, [setNodes, setEdges, fetchStatus]);

    // Initial Load
    useEffect(() => {
        fetchMaps();
    }, [fetchMaps]);

    // Load Map when Selected
    useEffect(() => {
        if (selectedMap) {
            fetchMapDetails(selectedMap);
        }
    }, [selectedMap, fetchMapDetails]);

    // Poll for status
    useEffect(() => {
        if (!selectedMap) return;
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [selectedMap, fetchStatus]);

    // Node Changes (Drag, Select)
    const onNodesChange = useCallback(
        (changes: NodeChange[]) => {
            setNodes((nds) => applyNodeChanges(changes, nds));
        },
        [setNodes]
    );

    const onNodeDragStop = useCallback(async (_event: React.MouseEvent, node: Node) => {
        if (selectedMap) {
            try {
                await apiClient.updateMapElement(selectedMap, node.id, {
                    x: Math.round(node.position.x),
                    y: Math.round(node.position.y)
                });
            } catch (err) {
                console.error("Failed to save node position", err);
            }
        }
    }, [selectedMap]);

    // Edge Changes
    const onEdgesChange = useCallback(
        (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
        [setEdges]
    );

    // Connect Nodes
    const onConnect = useCallback(
        async (params: Connection) => {
            if (!selectedMap) return;
            try {
                // Ensure source and target are strings
                if (!params.source || !params.target) return;

                const newLink = await apiClient.addMapLink(selectedMap, {
                    source_element_id: params.source,
                    target_element_id: params.target
                });

                const edge: Edge = {
                    id: newLink.id,
                    source: newLink.source_element_id,
                    target: newLink.target_element_id,
                    type: 'smoothstep',
                    markerEnd: { type: MarkerType.ArrowClosed }
                };

                setEdges((eds) => addEdge(edge, eds));
            } catch (err) {
                console.error("Failed to create link", err);
            }
        },
        [selectedMap, setEdges]
    );

    // Create New Map
    const handleCreateMap = async () => {
        if (!newMapName) return;
        try {
            const newMap = await apiClient.createMap({ name: newMapName });
            setMaps([...maps, newMap]);
            setSelectedMap(newMap.id);
            setShowCreateModal(false);
            setNewMapName('');
        } catch (err) {
            console.error("Failed to create map", err);
        }
    };

    // Add Device Node
    const handleAddDevice = async (deviceId: string) => {
        if (!selectedMap) return;
        try {
            const device = availableDevices.find(d => d.id === deviceId);
            const newElement = await apiClient.addMapElement(selectedMap, {
                element_type: 'device',
                device_id: deviceId,
                label: device?.hostname || 'Device',
                x: 100,
                y: 100,
                icon: 'server'
            });

            const newNode: Node = {
                id: newElement.id,
                position: { x: 100, y: 100 },
                data: { label: newElement.label, baseLabel: newElement.label, device_id: deviceId },
                style: {
                    background: 'var(--bg-card)',
                    color: 'var(--text-main)',
                    border: '1px solid var(--border-color)',
                    padding: '10px',
                    borderRadius: '8px',
                    width: 150
                }
            };
            setNodes((nds) => nds.concat(newNode));
            setShowElementModal(false);
        } catch (err) {
            console.error("Failed to add element", err);
        }
    };

    // Load devices for modal
    const loadDevices = async () => {
        try {
            const data = await apiClient.listDevices({ limit: 100 });
            setAvailableDevices(data.devices || []);
            setShowElementModal(true);
        } catch (err) {
            console.error("Failed to load devices", err);
        }
    };

    return (
        <div className="page-container" style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
            {/* Header / Toolbar */}
            <div className="page-header" style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <h1 className="page-title">Network Maps</h1>
                    <select
                        value={selectedMap || ''}
                        onChange={(e) => setSelectedMap(e.target.value)}
                        className="form-input"
                        style={{ minWidth: '200px' }}
                    >
                        {maps.map(m => (
                            <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                    </select>
                    <button className="btn btn-secondary" onClick={() => setShowCreateModal(true)}>
                        <Plus size={16} /> New Map
                    </button>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn btn-primary" onClick={loadDevices} disabled={!selectedMap}>
                        <Server size={16} /> Add Device
                    </button>
                </div>
            </div>

            {/* Map Canvas */}
            <div style={{ flex: 1, border: '1px solid var(--border-color)', borderRadius: '8px', background: 'var(--bg-card)' }}>
                {selectedMap ? (
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        onNodeDragStop={onNodeDragStop}
                        fitView
                        attributionPosition="bottom-right"
                    >
                        <Controls />
                        <Background color="#555" gap={16} />
                    </ReactFlow>
                ) : (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                        Select or create a map to get started
                    </div>
                )}
            </div>

            {/* Create Map Modal */}
            {showCreateModal && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <h2>Create New Map</h2>
                        <div className="form-group">
                            <label>Map Name</label>
                            <input
                                type="text"
                                className="form-input"
                                value={newMapName}
                                onChange={(e) => setNewMapName(e.target.value)}
                                placeholder="e.g. Core Network"
                            />
                        </div>
                        <div className="modal-actions">
                            <button className="btn btn-text" onClick={() => setShowCreateModal(false)}>Cancel</button>
                            <button className="btn btn-primary" onClick={handleCreateMap}>Create</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Add Element Modal */}
            {showElementModal && (
                <div className="modal-overlay">
                    <div className="modal-content" style={{ maxWidth: '500px' }}>
                        <h2>Add Device to Map</h2>
                        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Hostname</th>
                                        <th>IP</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {availableDevices.map(d => (
                                        <tr key={d.id}>
                                            <td>{d.hostname}</td>
                                            <td>{d.ip}</td>
                                            <td>
                                                <button
                                                    className="btn btn-sm btn-secondary"
                                                    onClick={() => handleAddDevice(d.id)}
                                                >
                                                    Add
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className="modal-actions" style={{ marginTop: '1rem' }}>
                            <button className="btn btn-text" onClick={() => setShowElementModal(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Maps;
