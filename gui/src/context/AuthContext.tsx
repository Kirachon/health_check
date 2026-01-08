import { useState, type ReactNode } from 'react';
import { apiClient } from '../api/client';
import { AuthContext } from './auth';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(localStorage.getItem('access_token')));
    const [loading] = useState(false);

    const login = async (username: string, password: string) => {
        const data = await apiClient.login(username, password);
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        setIsAuthenticated(true);
    };

    const logout = async () => {
        // Transition UI immediately; server-side logout is best-effort.
        setIsAuthenticated(false);
        void apiClient.logout().catch((error) => console.warn('Logout failed:', error));
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};
