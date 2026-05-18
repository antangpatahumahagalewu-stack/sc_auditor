const API_BASE = '';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => null);
    throw new Error(body?.meta?.error || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export interface ApiResponse<T = any> {
  data: T;
  meta: { status: string; timestamp: string; total?: number; [key: string]: any };
}

export interface Audit {
  audit_id: string;
  program?: string;
  contract?: string;
  chain?: string;
  state: string;
  priority?: number;
  findings_count?: number;
  critical_count?: number;
  high_count?: number;
  medium_count?: number;
  low_count?: number;
  duration_seconds?: number;
  created_at?: string;
  steps?: any[];
  error?: string;
}

export interface DaemonState {
  status: 'stopped' | 'running' | 'paused' | 'error';
  started_at?: string;
  stopped_at?: string;
  last_run_at?: string;
  next_run_at?: string;
  total_contracts_audited: number;
  total_cycles_completed: number;
  last_error?: string;
}

export interface Program {
  slug: string;
  name?: string;
  max_bounty?: string;
  chains?: string[];
  status?: string;
}

export interface MetricsSummary {
  total_audits: number;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  true_positives: number;
  false_positives: number;
  true_positive_rate: number;
  precision: number;
  recall: number;
  f1_score: number;
  per_tool?: Record<string, any>;
}

export interface PipelineStats {
  total_audits: number;
  completed: number;
  failed: number;
  in_progress: number;
  [key: string]: any;
}

// ── API methods ──

export const api = {
  // Config
  getConfig: () => request<ApiResponse<Record<string, any>>>('/api/config'),
  setConfigKey: (key: string, value: any) =>
    request<ApiResponse>(`/api/config/${key}`, { method: 'PUT', body: JSON.stringify({ value }) }),
  setBulkConfig: (config: Record<string, any>) =>
    request<ApiResponse>('/api/config/bulk', { method: 'PUT', body: JSON.stringify({ config }) }),

  // Audits
  getAudits: (params?: { state?: string; program?: string; chain?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set('state', params.state);
    if (params?.program) qs.set('program', params.program);
    if (params?.chain) qs.set('chain', params.chain);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    const q = qs.toString();
    return request<ApiResponse<Audit[]>>(`/api/audits${q ? '?' + q : ''}`);
  },
  getAudit: (id: string) => request<ApiResponse<Audit>>(`/api/audits/${id}`),
  startAudit: (body: { chain: string; address: string; program?: string; priority?: number }) =>
    request<ApiResponse>('/api/audit', { method: 'POST', body: JSON.stringify(body) }),
  retryAudit: (id: string) =>
    request<ApiResponse>(`/api/audits/${id}/retry`, { method: 'POST' }),

  // Daemon
  getDaemonStatus: () => request<ApiResponse<DaemonState>>('/api/daemon/status'),
  daemonStart: () => request<ApiResponse>('/api/daemon/start', { method: 'POST' }),
  daemonStop: () => request<ApiResponse>('/api/daemon/stop', { method: 'POST' }),
  daemonSync: () => request<ApiResponse>('/api/daemon/sync', { method: 'POST' }),

  // Programs
  getPrograms: (params?: { search?: string; chain?: string }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.chain) qs.set('chain', params.chain);
    const q = qs.toString();
    return request<ApiResponse<Program[]>>(`/api/programs${q ? '?' + q : ''}`);
  },
  getProgram: (slug: string) => request<ApiResponse<Program>>(`/api/programs/${slug}`),

  // Stats & Metrics
  getStats: () => request<ApiResponse<PipelineStats>>('/api/stats'),
  getMetrics: () => request<ApiResponse<MetricsSummary>>('/api/metrics'),

  // Feedback
  getFeedback: () => request<ApiResponse<any[]>>('/api/feedback'),
  submitFeedback: (body: { finding_id: string; feedback: string; status: string }) =>
    request<ApiResponse>('/api/feedback', { method: 'POST', body: JSON.stringify(body) }),

  // Notifications
  testNotification: (channel: string) =>
    request<ApiResponse>('/api/notifications/test', { method: 'POST', body: JSON.stringify({ channel }) }),

  // Reports
  generateReport: (auditId: string, format = 'immunefi') =>
    request<ApiResponse>('/api/reports/generate', { method: 'POST', body: JSON.stringify({ audit_id: auditId, format }) }),

  // Queue
  getQueue: () => request<ApiResponse>('/api/queue'),
  addToQueue: (body: { contract_id: string; chain: string; address: string; program?: string; priority_score?: number }) =>
    request<ApiResponse>('/api/queue', { method: 'POST', body: JSON.stringify(body) }),
};
