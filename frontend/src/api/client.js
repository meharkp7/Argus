const rawApiBase =
  import.meta.env.VITE_API_BASE_URL?.trim() ||
  '/api';
const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 60000);

function normalizeApiBase(value) {
  if (!value) return '/api';

  const trimmed = value.replace(/\/+$/, '');
  if (trimmed === '') return '/api';
  if (trimmed.endsWith('/api')) return trimmed;
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return `${trimmed}/api`;
  }
  return trimmed;
}

const API_BASE = normalizeApiBase(rawApiBase);

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
      signal: controller.signal,
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || `API error: ${res.status}`);
    }
    return res.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out while contacting the ARGUS backend.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  health: () => request('/health'),
  getAlerts: (limit = 20) => request(`/alerts/?limit=${limit}`),
  getAlert: (id) => request(`/alerts/${id}`),
  investigateAlert: (id, query) =>
    request(`/alerts/${id}/investigate`, {
      method: 'POST',
      body: JSON.stringify({ query, top_k: 5 }),
    }),
  triggerEmergency: (id, confirmed = false) =>
    request(`/alerts/${id}/emergency-response?operator_confirmed=${confirmed}`, {
      method: 'POST',
    }),
  getHeatmap: () => request('/heatmap/'),
  getPlantLayout: () => request('/heatmap/layout'),
  getPermits: () => request('/permits/'),
  preMortemPermit: (data) =>
    request('/permits/pre-mortem', { method: 'POST', body: JSON.stringify(data) }),
  submitPermit: (data) =>
    request('/permits/submit', { method: 'POST', body: JSON.stringify(data) }),
  submitFeedback: (data) =>
    request('/feedback/', { method: 'POST', body: JSON.stringify(data) }),
  getTrustMetrics: () => request('/feedback/metrics'),
  getThresholds: () => request('/feedback/thresholds'),
  ragQuery: (query, alertId = null) =>
    request('/rag/query', {
      method: 'POST',
      body: JSON.stringify({ query, alert_id: alertId, top_k: 5 }),
    }),
  complianceAudit: (documentText, frameworks) =>
    request('/compliance/audit', {
      method: 'POST',
      body: JSON.stringify({
        document_text: documentText,
        applicable_frameworks: frameworks,
      }),
    }),
  voiceReport: (transcript, language, zone) =>
    request('/voice/report', {
      method: 'POST',
      body: JSON.stringify({
        transcript,
        language,
        reporter_zone: zone,
      }),
    }),
  getSimulationState: () => request('/simulation/state'),
  controlSimulation: (action) =>
    request('/simulation/control', {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),
  stepSimulation: () => request('/simulation/step', { method: 'POST' }),
  getEvidence: (limit = 50) => request(`/evidence?limit=${limit}`),
  verifyEvidence: () => request('/evidence/verify'),
};
