import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { clearLegacySharedTokens, clearTokens, getAccessToken, getRefreshToken, storeTokens } from '../utils/authStorage';
import type { AuthResponse, LoginPayload, RegisterPayload, RegisterResponse, User } from '../types/auth';

interface AuthContextType {
  user: User | null;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    clearLegacySharedTokens();
    const token = getAccessToken();
    if (!token) {
      setLoading(false);
      return;
    }

    api.get('/auth/me')
      .then((response) => setUser(response.data))
      .catch(() => {
        clearTokens();
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (payload: LoginPayload) => {
    const response = await api.post<AuthResponse>('/auth/login', payload);
    storeTokens(response.data.access_token, response.data.refresh_token);
    const profile = await api.get('/auth/me');
    setUser(profile.data);
    navigate(profile.data.role_name === 'SentinelAI Administrator' ? '/dashboard' : '/employee', { replace: true });
  };

  const register = async (payload: RegisterPayload) => {
    const response = await api.post<RegisterResponse>('/auth/register', payload);
    if (response.data.status === 'active' && response.data.access_token && response.data.refresh_token) {
      storeTokens(response.data.access_token, response.data.refresh_token);
      const profile = await api.get('/auth/me');
      setUser(profile.data);
      navigate('/employee', { replace: true });
    }
    return response.data;
  };

  const logout = async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) await api.post('/auth/logout', { refresh_token: refreshToken });
    } finally {
      clearTokens();
      setUser(null);
      navigate('/', { replace: true });
    }
  };

  const value = useMemo(() => ({ user, login, register, logout, loading }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
