import axios from 'axios';

import { clearTokens, getAccessToken } from './authStorage';

const runtimeApiUrl =
  (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.VITE_API_URL ||
  "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: runtimeApiUrl,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      clearTokens();
      window.location.href = '/';
    }
    return Promise.reject(error);
  },
);

export default api;
