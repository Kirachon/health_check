import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class APIClient {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: API_BASE_URL,
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
                            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                                refresh_token: refreshToken,
                            });

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
    async queryMetrics(query: string, start?: string, end?: string) {
        const vmUrl = import.meta.env.VITE_VM_URL || 'http://localhost:8428';
        const response = await axios.get(`${vmUrl}/api/v1/query`, {
            params: { query, time: end || new Date().toISOString() },
        });
        return response.data;
    }

    async queryRangeMetrics(query: string, start: string, end: string, step = '30s') {
        const vmUrl = import.meta.env.VITE_VM_URL || 'http://localhost:8428';
        const response = await axios.get(`${vmUrl}/api/v1/query_range`, {
            params: { query, start, end, step },
        });
        return response.data;
    }
}

export const apiClient = new APIClient();
