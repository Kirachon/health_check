import axios from 'axios';
import type { AxiosInstance } from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';
export const REQUEST_TIMEOUT_MS = 15000;

type MaintenanceScopeType = 'all' | 'device' | 'hostgroup';

export interface MaintenanceWindowUpsert {
    name: string;
    description?: string | null;
    start_time: string;
    end_time: string;
    recurrence?: string | null;
    scope_type: MaintenanceScopeType;
    device_id?: string | null;
    hostgroup_id?: string | null;
    collect_data: boolean;
}

class APIClient {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
            timeout: REQUEST_TIMEOUT_MS,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Add auth token to requests
        this.client.interceptors.request.use((config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });

        // Handle token refresh on 401
        this.client.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        const refreshToken = localStorage.getItem('refresh_token');
                        if (refreshToken) {
                            const response = await axios.post(
                                `${API_BASE_URL}/auth/refresh`,
                                { refresh_token: refreshToken },
                                { timeout: REQUEST_TIMEOUT_MS }
                            );

                            const { access_token, refresh_token: newRefreshToken } = response.data;
                            localStorage.setItem('access_token', access_token);
                            localStorage.setItem('refresh_token', newRefreshToken);

                            originalRequest.headers.Authorization = `Bearer ${access_token}`;
                            return this.client(originalRequest);
                        }
                    } catch (refreshError) {
                        // Refresh failed, logout
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    // Auth endpoints
    async login(username: string, password: string) {
        const response = await this.client.post('/auth/login', { username, password });
        return response.data;
    }

    async logout() {
        const refreshToken = localStorage.getItem('refresh_token');

        // Always clear local auth immediately so the UI can transition without waiting.
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // Best-effort server-side logout (optional; may fail if backend is down).
        try {
            if (refreshToken) {
                await this.client.post('/auth/logout', { refresh_token: refreshToken });
            }
        } catch (error) {
            // Local auth has already been cleared; keep this best-effort but observable.
            console.warn('Server logout failed:', error);
        }
    }

    // Device endpoints
    async listDevices(params?: { skip?: number; limit?: number; status?: string }) {
        const response = await this.client.get('/devices', { params });
        return response.data;
    }

    async getDevice(deviceId: string) {
        const response = await this.client.get(`/devices/${deviceId}`);
        return response.data;
    }

    async deleteDevice(deviceId: string) {
        await this.client.delete(`/devices/${deviceId}`);
    }

    // VictoriaMetrics query
    async queryMetrics(query: string, _start?: string, end?: string) {
        const vmUrl = import.meta.env.VITE_VM_URL || 'http://localhost:9090';
        const response = await axios.get(`${vmUrl}/api/v1/query`, {
            timeout: REQUEST_TIMEOUT_MS,
            params: { query, time: end || new Date().toISOString() },
        });
        return response.data;
    }

    async queryRangeMetrics(query: string, start: string, end: string, step = '30s') {
        const vmUrl = import.meta.env.VITE_VM_URL || 'http://localhost:9090';
        const response = await axios.get(`${vmUrl}/api/v1/query_range`, {
            timeout: REQUEST_TIMEOUT_MS,
            params: { query, start, end, step },
        });
        return response.data;
    }

    // Host Groups endpoints
    async listHostGroups(params?: { skip?: number; limit?: number; search?: string }) {
        const response = await this.client.get('/hostgroups', { params });
        return response.data;
    }

    async getHostGroup(id: string) {
        const response = await this.client.get(`/hostgroups/${id}`);
        return response.data;
    }

    async createHostGroup(data: { name: string; description?: string }) {
        const response = await this.client.post('/hostgroups', data);
        return response.data;
    }

    async updateHostGroup(id: string, data: { name?: string; description?: string }) {
        const response = await this.client.put(`/hostgroups/${id}`, data);
        return response.data;
    }

    async deleteHostGroup(id: string) {
        await this.client.delete(`/hostgroups/${id}`);
    }

    // Templates endpoints
    async listTemplates(params?: { skip?: number; limit?: number; search?: string; template_type?: string }) {
        const response = await this.client.get('/templates', { params });
        return response.data;
    }

    async getTemplate(id: string) {
        const response = await this.client.get(`/templates/${id}`);
        return response.data;
    }

    async createTemplate(data: { name: string; description?: string; template_type?: string }) {
        const response = await this.client.post('/templates', data);
        return response.data;
    }

    async updateTemplate(id: string, data: { name?: string; description?: string; template_type?: string }) {
        const response = await this.client.put(`/templates/${id}`, data);
        return response.data;
    }

    async deleteTemplate(id: string) {
        await this.client.delete(`/templates/${id}`);
    }

    async createTemplateItem(templateId: string, data: { name: string; key: string; value_type?: string; units?: string; update_interval?: number }) {
        const response = await this.client.post(`/templates/${templateId}/items`, data);
        return response.data;
    }

    async deleteTemplateItem(templateId: string, itemId: string) {
        await this.client.delete(`/templates/${templateId}/items/${itemId}`);
    }

    // Triggers endpoints
    async listTriggers(params?: { skip?: number; limit?: number; search?: string; severity?: string; enabled?: boolean; template_id?: string }) {
        const response = await this.client.get('/triggers', { params });
        return response.data;
    }

    async getTrigger(id: string) {
        const response = await this.client.get(`/triggers/${id}`);
        return response.data;
    }

    async createTrigger(data: { name: string; expression: string; severity?: string; description?: string; template_id?: string; enabled?: boolean }) {
        const response = await this.client.post('/triggers', data);
        return response.data;
    }

    async updateTrigger(id: string, data: { name?: string; expression?: string; severity?: string; description?: string; enabled?: boolean }) {
        const response = await this.client.put(`/triggers/${id}`, data);
        return response.data;
    }

    async deleteTrigger(id: string) {
        await this.client.delete(`/triggers/${id}`);
    }

    async toggleTrigger(id: string) {
        const response = await this.client.post(`/triggers/${id}/toggle`);
        return response.data;
    }

    // Alerts endpoints
    async listAlerts(params?: { status?: string; acknowledged?: boolean; limit?: number; offset?: number; trigger_id?: string }) {
        const response = await this.client.get('/alerts', { params });
        return response.data;
    }

    async acknowledgeAlert(id: string, data?: { message?: string }) {
        const response = await this.client.post(`/alerts/${id}/acknowledge`, data || {});
        return response.data;
    }

    async getAlertCounts() {
        const response = await this.client.get('/alerts/summary/counts');
        return response.data;
    }

    // Actions endpoints
    async listActions(params?: { skip?: number; limit?: number; search?: string; action_type?: string; enabled?: boolean }) {
        const response = await this.client.get('/actions', { params });
        return response.data;
    }

    async getAction(id: string) {
        const response = await this.client.get(`/actions/${id}`);
        return response.data;
    }

    async createAction(data: { name: string; action_type?: string; conditions?: string; enabled?: boolean }) {
        const response = await this.client.post('/actions', data);
        return response.data;
    }

    async updateAction(id: string, data: { name?: string; action_type?: string; conditions?: string; enabled?: boolean }) {
        const response = await this.client.put(`/actions/${id}`, data);
        return response.data;
    }

    async deleteAction(id: string) {
        await this.client.delete(`/actions/${id}`);
    }

    async createActionOperation(actionId: string, data: { operation_type: string; step_number?: number; parameters?: string }) {
        const response = await this.client.post(`/actions/${actionId}/operations`, data);
        return response.data;
    }

    async deleteActionOperation(actionId: string, operationId: string) {
        await this.client.delete(`/actions/${actionId}/operations/${operationId}`);
    }

    // Users endpoints (admin only)
    async listUsers(params?: { search?: string; role?: string; limit?: number; offset?: number }) {
        const response = await this.client.get('/users', { params });
        return response.data;
    }

    async getUser(id: string) {
        const response = await this.client.get(`/users/${id}`);
        return response.data;
    }

    async createUser(data: { username: string; password: string; role?: string }) {
        const response = await this.client.post('/users', data);
        return response.data;
    }

    async updateUser(id: string, data: { role?: string }) {
        const response = await this.client.put(`/users/${id}`, data);
        return response.data;
    }

    async deleteUser(id: string) {
        await this.client.delete(`/users/${id}`);
    }

    async resetUserPassword(id: string, password: string) {
        await this.client.post(`/users/${id}/reset-password`, { password });
    }

    // Maps endpoints
    async listMaps() {
        const response = await this.client.get('/maps');
        return response.data;
    }

    async getMap(id: string) {
        const response = await this.client.get(`/maps/${id}`);
        return response.data;
    }

    async getMapStatus(id: string) {
        const response = await this.client.get(`/maps/${id}/status`);
        return response.data;
    }

    // Maintenance endpoints
    async listMaintenanceWindows() {
        const response = await this.client.get('/maintenance');
        return response.data;
    }

    async createMaintenanceWindow(data: MaintenanceWindowUpsert) {
        const response = await this.client.post('/maintenance', data);
        return response.data;
    }

    async updateMaintenanceWindow(id: string, data: MaintenanceWindowUpsert) {
        const response = await this.client.put(`/maintenance/${id}`, data);
        return response.data;
    }

    async deleteMaintenanceWindow(id: string) {
        await this.client.delete(`/maintenance/${id}`);
    }

    async deactivateMaintenanceWindow(id: string) {
        await this.client.post(`/maintenance/${id}/deactivate`);
    }

    async createMap(data: { name: string; description?: string; width?: number; height?: number; background_image?: string }) {
        const response = await this.client.post('/maps', data);
        return response.data;
    }

    async updateMap(id: string, data: { name?: string; description?: string; width?: number; height?: number; background_image?: string }) {
        const response = await this.client.put(`/maps/${id}`, data);
        return response.data;
    }

    async deleteMap(id: string) {
        await this.client.delete(`/maps/${id}`);
    }

    async addMapElement(mapId: string, data: { element_type: string; device_id?: string; hostgroup_id?: string; label?: string; x: number; y: number; icon?: string }) {
        const response = await this.client.post(`/maps/${mapId}/elements`, data);
        return response.data;
    }

    async updateMapElement(mapId: string, elementId: string, data: { x?: number; y?: number; label?: string }) {
        const response = await this.client.put(`/maps/${mapId}/elements/${elementId}`, data);
        return response.data;
    }

    async deleteMapElement(mapId: string, elementId: string) {
        await this.client.delete(`/maps/${mapId}/elements/${elementId}`);
    }

    async addMapLink(mapId: string, data: { source_element_id: string; target_element_id: string; link_type?: string }) {
        const response = await this.client.post(`/maps/${mapId}/links`, data);
        return response.data;
    }

    async deleteMapLink(mapId: string, linkId: string) {
        await this.client.delete(`/maps/${mapId}/links/${linkId}`);
    }

    // Discovery endpoints
    async listDiscoveryJobs(params?: { skip?: number; limit?: number; status_filter?: string }) {
        const response = await this.client.get('/discovery', { params });
        return response.data;
    }

    async getDiscoveryJob(jobId: string) {
        const response = await this.client.get(`/discovery/${jobId}`);
        return response.data;
    }

    async createDiscoveryJob(data: {
        name: string;
        description?: string;
        ip_ranges: string;
        scan_icmp?: boolean;
        scan_snmp?: boolean;
        snmp_community?: string;
        snmp_version?: string;
        scan_ports?: string | null;
        schedule_type?: string;
        schedule_cron?: string | null;
        auto_add_devices?: boolean;
        auto_add_hostgroup_id?: string | null;
    }) {
        const response = await this.client.post('/discovery', data);
        return response.data;
    }

    async runDiscoveryJob(jobId: string) {
        const response = await this.client.post(`/discovery/${jobId}/run`);
        return response.data;
    }

    async deleteDiscoveryJob(jobId: string) {
        await this.client.delete(`/discovery/${jobId}`);
    }

    async getDiscoveryResults(jobId: string, params?: { status_filter?: string }) {
        const response = await this.client.get(`/discovery/${jobId}/results`, { params });
        return response.data;
    }

    async addDiscoveredDevices(jobId: string, data: { result_ids: string[]; hostgroup_id?: string | null }) {
        const response = await this.client.post(`/discovery/${jobId}/add-devices`, data);
        return response.data;
    }
}

export const apiClient = new APIClient();
