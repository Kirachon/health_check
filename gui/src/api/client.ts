import axios from 'axios';
import type { AxiosInstance } from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1';
export const REQUEST_TIMEOUT_MS = 15000;

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
        if (refreshToken) {
            await this.client.post('/auth/logout', { refresh_token: refreshToken });
        }
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
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
}

export const apiClient = new APIClient();
