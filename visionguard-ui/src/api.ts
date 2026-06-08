const LOCAL_API_BASE_URL = 'http://localhost:8000';
const PRODUCTION_API_BASE_URL = 'https://d2brdeqy144bwg.cloudfront.net/visionguard';

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? PRODUCTION_API_BASE_URL : LOCAL_API_BASE_URL);

function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  let basePath = '';

  try {
    basePath = new URL(BASE_URL).pathname.replace(/\/+$/, '');
  } catch {
    basePath = '';
  }

  const pathForBase =
    basePath && normalizedPath.startsWith(`${basePath}/`)
      ? normalizedPath.slice(basePath.length)
      : normalizedPath;

  return `${BASE_URL.replace(/\/+$/, '')}${pathForBase}`;
}

type Envelope<T> = {
  data: T;
  meta: { requestId: string; generatedAt: string };
  error: null | { code: string; message: string; statusCode: number };
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(buildApiUrl(path), {
    headers: isFormData ? init?.headers : { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  const envelope = (await response.json()) as Envelope<T>;
  if (!response.ok || envelope.error) {
    throw new Error(envelope.error?.message || `Request failed: ${response.status}`);
  }
  return envelope.data;
}

export const api = {
  getDashboard: () => request<any>('/visionguard/dashboard/overview'),
  exportDashboard: () => request<any>('/visionguard/dashboard/export', { method: 'POST', body: JSON.stringify({ format: 'pdf' }) }),
  getClaims: (params = '') => request<any>(`/visionguard/claims${params}`),
  retrainClaimsModel: () => request<any>('/visionguard/claims/retrain', { method: 'POST' }),
  getLatestClaimsRetrain: () => request<any>('/visionguard/claims/retrain/latest'),
  syncRetrainClaims: () => request<any>('/visionguard/claims/retrain', { method: 'POST' }),
  getLatestSyncRetrain: () => request<any>('/visionguard/claims/retrain/latest'),
  getClaim: (id: string) => request<any>(`/visionguard/claims/${id}`),
  flagClaim: (id: string) => request<any>(`/visionguard/claims/${id}/flag-siu`, { method: 'POST' }),
  getProviders: (params = '') => request<any>(`/visionguard/providers${params}`),
  getProvider: (id: string) => request<any>(`/visionguard/providers/${id}`),
  getSystemStatus: () => request<any>('/visionguard/system/status'),
  getNotifications: () => request<any>('/visionguard/notifications'),
  markNotificationRead: (id: string) => request<any>(`/visionguard/notifications/${id}/read`, { method: 'POST' }),
  createScoringJob: (payload: any) => request<any>('/visionguard/scoring/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  createScoringJobFromFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<any>('/visionguard/scoring/jobs', { method: 'POST', body: formData });
  },
  getScoringJob: (id: string) => request<any>(`/visionguard/scoring/jobs/${id}`),
  getScoringResult: (id: string) => request<any>(`/visionguard/scoring/jobs/${id}/result`),
  assignScoringJob: (id: string) => request<any>(`/visionguard/scoring/jobs/${id}/assign-siu`, { method: 'POST' }),
};
