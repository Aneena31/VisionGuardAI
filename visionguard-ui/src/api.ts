const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

type Envelope<T> = {
  data: T;
  meta: { requestId: string; generatedAt: string };
  error: null | { code: string; message: string; statusCode: number };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const envelope = (await response.json()) as Envelope<T>;
  if (!response.ok || envelope.error) {
    throw new Error(envelope.error?.message || `Request failed: ${response.status}`);
  }
  return envelope.data;
}

export const api = {
  getDashboard: () => request<any>('/api/dashboard/overview'),
  exportDashboard: () => request<any>('/api/dashboard/export', { method: 'POST', body: JSON.stringify({ format: 'pdf' }) }),
  getClaims: (params = '') => request<any>(`/api/claims${params}`),
  getClaim: (id: string) => request<any>(`/api/claims/${id}`),
  flagClaim: (id: string) => request<any>(`/api/claims/${id}/flag-siu`, { method: 'POST' }),
  getProviders: (params = '') => request<any>(`/api/providers${params}`),
  getProvider: (id: string) => request<any>(`/api/providers/${id}`),
  getSystemStatus: () => request<any>('/api/system/status'),
  getNotifications: () => request<any>('/api/notifications'),
  markNotificationRead: (id: string) => request<any>(`/api/notifications/${id}/read`, { method: 'POST' }),
  createScoringJob: (payload: any) => request<any>('/api/scoring/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  getScoringJob: (id: string) => request<any>(`/api/scoring/jobs/${id}`),
  getScoringResult: (id: string) => request<any>(`/api/scoring/jobs/${id}/result`),
  assignScoringJob: (id: string) => request<any>(`/api/scoring/jobs/${id}/assign-siu`, { method: 'POST' }),
};
