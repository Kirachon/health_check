import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import {
  Play,
  Plus,
  Search,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  Server
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

interface DiscoveryJob {
  id: string;
  name: string;
  description?: string | null;
  ip_ranges: string;
  scan_icmp: boolean;
  scan_snmp: boolean;
  scan_ports?: string | null;
  schedule_type: string;
  schedule_cron?: string | null;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  progress_percent: number;
  error_message?: string | null;
  auto_add_devices: boolean;
  auto_add_hostgroup_id?: string | null;
  created_at: string;
  results_count: number;
}

interface DiscoveryResult {
  id: string;
  ip_address: string;
  hostname?: string | null;
  mac_address?: string | null;
  icmp_reachable?: boolean | null;
  icmp_latency_ms?: number | null;
  snmp_reachable?: boolean | null;
  open_ports?: string | null;
  status: string;
  device_id?: string | null;
  discovered_at: string;
}

interface HostGroup {
  id: string;
  name: string;
}

interface JobFormData {
  name: string;
  description: string;
  ip_ranges: string;
  scan_icmp: boolean;
  scan_snmp: boolean;
  scan_ports: string;
  schedule_type: string;
  schedule_cron: string;
  auto_add_devices: boolean;
  auto_add_hostgroup_id: string;
}

const Discovery: React.FC = () => {
  const [jobs, setJobs] = useState<DiscoveryJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const [formData, setFormData] = useState<JobFormData>({
    name: '',
    description: '',
    ip_ranges: '',
    scan_icmp: true,
    scan_snmp: false,
    scan_ports: '',
    schedule_type: 'manual',
    schedule_cron: '',
    auto_add_devices: false,
    auto_add_hostgroup_id: '',
  });

  const [hostGroups, setHostGroups] = useState<HostGroup[]>([]);
  const [resultsModalJob, setResultsModalJob] = useState<DiscoveryJob | null>(null);
  const [results, setResults] = useState<DiscoveryResult[]>([]);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [addingDevices, setAddingDevices] = useState(false);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.listDiscoveryJobs();
      const list = response.jobs || [];
      const filtered = searchTerm
        ? list.filter((job: DiscoveryJob) => job.name.toLowerCase().includes(searchTerm.toLowerCase()))
        : list;
      setJobs(filtered);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load discovery jobs'));
    } finally {
      setLoading(false);
    }
  }, [searchTerm]);

  useEffect(() => {
    const debounce = setTimeout(fetchJobs, 300);
    return () => clearTimeout(debounce);
  }, [fetchJobs]);

  const loadHostGroups = useCallback(async () => {
    try {
      const response = await apiClient.listHostGroups({ limit: 200 });
      setHostGroups(response.host_groups || []);
    } catch (err) {
      console.error('Failed to load host groups', err);
    }
  }, []);

  useEffect(() => {
    loadHostGroups();
  }, [loadHostGroups]);

  const handleOpenCreate = () => {
    setFormData({
      name: '',
      description: '',
      ip_ranges: '',
      scan_icmp: true,
      scan_snmp: false,
      scan_ports: '',
      schedule_type: 'manual',
      schedule_cron: '',
      auto_add_devices: false,
      auto_add_hostgroup_id: '',
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim() || !formData.ip_ranges.trim()) return;
    setSaving(true);
    try {
      await apiClient.createDiscoveryJob({
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        ip_ranges: formData.ip_ranges.trim(),
        scan_icmp: formData.scan_icmp,
        scan_snmp: formData.scan_snmp,
        scan_ports: formData.scan_ports.trim() || undefined,
        schedule_type: formData.schedule_type,
        schedule_cron: formData.schedule_cron.trim() || undefined,
        auto_add_devices: formData.auto_add_devices,
        auto_add_hostgroup_id: formData.auto_add_hostgroup_id || undefined,
      });
      setShowModal(false);
      fetchJobs();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create discovery job'));
    } finally {
      setSaving(false);
    }
  };

  const handleRun = async (jobId: string) => {
    try {
      await apiClient.runDiscoveryJob(jobId);
      fetchJobs();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to start discovery job'));
    }
  };

  const handleDelete = async (jobId: string) => {
    try {
      await apiClient.deleteDiscoveryJob(jobId);
      setDeleteId(null);
      fetchJobs();
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to delete discovery job'));
    }
  };

  const openResults = async (job: DiscoveryJob) => {
    setResultsModalJob(job);
    setResults([]);
    setResultsLoading(true);
    try {
      const data = await apiClient.getDiscoveryResults(job.id);
      setResults(data || []);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load discovery results'));
    } finally {
      setResultsLoading(false);
    }
  };

  const addNewDevices = async () => {
    if (!resultsModalJob) return;
    const newIds = results.filter(r => r.status === 'new').map(r => r.id);
    if (newIds.length === 0) return;
    setAddingDevices(true);
    try {
      await apiClient.addDiscoveredDevices(resultsModalJob.id, {
        result_ids: newIds,
        hostgroup_id: formData.auto_add_hostgroup_id || undefined,
      });
      await openResults(resultsModalJob);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to add discovered devices'));
    } finally {
      setAddingDevices(false);
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return '—';
    return new Date(value).toLocaleString();
  };

  return (
    <div className="enterprise-container">
      <header className="page-header">
        <div className="page-title-group">
          <h1>Network Discovery</h1>
          <p className="page-description">Scan internal IP ranges and onboard discovered devices.</p>
        </div>
        <button className="primary-btn" onClick={handleOpenCreate}>
          <Plus size={18} />
          Create Job
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
            placeholder="Search discovery jobs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="glass-table-container">
        {loading ? (
          <div className="loading-state">
            <Loader2 size={24} className="spin" />
            <span>Loading discovery jobs...</span>
          </div>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <Server size={48} className="empty-icon" />
            <h3>No discovery jobs found</h3>
            <p>Create a job to scan your internal network.</p>
            <button className="primary-btn small" onClick={handleOpenCreate}>
              <Plus size={16} /> Create Job
            </button>
          </div>
        ) : (
          <table className="enterprise-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>IP Ranges</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Results</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className={job.status === 'failed' ? 'disabled-row' : ''}>
                  <td>
                    <strong>{job.name}</strong>
                    {job.description && <div className="muted-text">{job.description}</div>}
                  </td>
                  <td className="ip-cell">{job.ip_ranges}</td>
                  <td>
                    <span className={`badge ${job.status === 'running' ? 'badge-amber' : job.status === 'completed' ? 'badge-green' : 'badge-slate'}`}>
                      {job.status}
                    </span>
                  </td>
                  <td>{job.progress_percent || 0}%</td>
                  <td>{job.results_count}</td>
                  <td>{formatDate(job.created_at)}</td>
                  <td className="text-right">
                    <div className="action-buttons">
                      <button className="icon-btn" title="Run" onClick={() => handleRun(job.id)}>
                        <Play size={16} />
                      </button>
                      <button className="icon-btn" title="Results" onClick={() => openResults(job)}>
                        <Search size={16} />
                      </button>
                      <button className="icon-btn delete" title="Delete" onClick={() => setDeleteId(job.id)}>
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

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal glass wide" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>Create Discovery Job</h2>
              <button className="icon-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              <div className="form-group">
                <label>Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Core network scan"
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optional description"
                />
              </div>
              <div className="form-group">
                <label>IP Ranges (CIDR, comma-separated) *</label>
                <input
                  type="text"
                  value={formData.ip_ranges}
                  onChange={(e) => setFormData({ ...formData, ip_ranges: e.target.value })}
                  placeholder="e.g., 192.168.1.0/24,10.0.0.0/16"
                />
              </div>
              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Scan Ports</label>
                  <input
                    type="text"
                    value={formData.scan_ports}
                    onChange={(e) => setFormData({ ...formData, scan_ports: e.target.value })}
                    placeholder="e.g., 22,80,443"
                  />
                </div>
                <div className="form-group flex-1">
                  <label>Schedule</label>
                  <select
                    value={formData.schedule_type}
                    onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                  >
                    <option value="manual">Manual</option>
                    <option value="cron">Cron</option>
                  </select>
                </div>
              </div>
              {formData.schedule_type === 'cron' && (
                <div className="form-group">
                  <label>Cron Expression</label>
                  <input
                    type="text"
                    value={formData.schedule_cron}
                    onChange={(e) => setFormData({ ...formData, schedule_cron: e.target.value })}
                    placeholder="e.g., 0 2 * * 0"
                  />
                </div>
              )}
              <div className="form-row">
                <div className="form-group flex-1 checkbox-row">
                  <input
                    id="scanIcmp"
                    type="checkbox"
                    checked={formData.scan_icmp}
                    onChange={(e) => setFormData({ ...formData, scan_icmp: e.target.checked })}
                  />
                  <label htmlFor="scanIcmp">ICMP (ping) sweep</label>
                </div>
                <div className="form-group flex-1 checkbox-row">
                  <input
                    id="scanSnmp"
                    type="checkbox"
                    checked={formData.scan_snmp}
                    onChange={(e) => setFormData({ ...formData, scan_snmp: e.target.checked })}
                  />
                  <label htmlFor="scanSnmp">SNMP scan</label>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group flex-1 checkbox-row">
                  <input
                    id="autoAdd"
                    type="checkbox"
                    checked={formData.auto_add_devices}
                    onChange={(e) => setFormData({ ...formData, auto_add_devices: e.target.checked })}
                  />
                  <label htmlFor="autoAdd">Auto-add devices</label>
                </div>
                <div className="form-group flex-1">
                  <label>Auto-add Host Group</label>
                  <select
                    value={formData.auto_add_hostgroup_id}
                    onChange={(e) => setFormData({ ...formData, auto_add_hostgroup_id: e.target.value })}
                    disabled={!formData.auto_add_devices}
                  >
                    <option value="">None</option>
                    {hostGroups.map((hg) => (
                      <option key={hg.id} value={hg.id}>{hg.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="secondary-btn" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="primary-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteId && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal glass small" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>Delete Job</h2>
              <button className="icon-btn" onClick={() => setDeleteId(null)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              <p>Delete this discovery job? Results will be removed.</p>
            </div>
            <div className="modal-footer">
              <button className="secondary-btn" onClick={() => setDeleteId(null)}>Cancel</button>
              <button className="danger-btn" onClick={() => handleDelete(deleteId)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {resultsModalJob && (
        <div className="modal-overlay" onClick={() => setResultsModalJob(null)}>
          <div className="modal glass wide" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <h2>Discovery Results</h2>
              <button className="icon-btn" onClick={() => setResultsModalJob(null)}><X size={20} /></button>
            </header>
            <div className="modal-body">
              {resultsLoading ? (
                <div className="loading-state">
                  <Loader2 size={24} className="spin" />
                  <span>Loading results...</span>
                </div>
              ) : results.length === 0 ? (
                <div className="empty-state">
                  <Server size={48} className="empty-icon" />
                  <h3>No results yet</h3>
                  <p>Run the job to discover devices.</p>
                </div>
              ) : (
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      <th>IP</th>
                      <th>Hostname</th>
                      <th>Status</th>
                      <th>ICMP</th>
                      <th>Latency</th>
                      <th>Ports</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => (
                      <tr key={r.id} className={r.status !== 'new' ? 'disabled-row' : ''}>
                        <td>{r.ip_address}</td>
                        <td>{r.hostname || '—'}</td>
                        <td><span className={`badge ${r.status === 'new' ? 'badge-amber' : 'badge-slate'}`}>{r.status}</span></td>
                        <td>{r.icmp_reachable ? 'Yes' : 'No'}</td>
                        <td>{r.icmp_latency_ms != null ? `${r.icmp_latency_ms} ms` : '—'}</td>
                        <td>{r.open_ports || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="modal-footer">
              <button className="secondary-btn" onClick={() => setResultsModalJob(null)}>Close</button>
              <button className="primary-btn" onClick={addNewDevices} disabled={addingDevices || results.length === 0}>
                {addingDevices ? 'Adding...' : 'Add New Devices'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
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

        .disabled-row { opacity: 0.5; }
        .muted-text { color: var(--text-dim); font-size: 0.85rem; }
        .ip-cell { font-family: 'Fira Code', monospace; font-size: 0.85rem; color: var(--text-muted); }
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
          max-width: 520px;
          border-radius: 16px;
          overflow: hidden;
        }
        .modal.wide { max-width: 760px; }
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
        .checkbox-row { display: flex; align-items: center; gap: 0.5rem; }

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
      `}</style>
    </div>
  );
};

export default Discovery;
