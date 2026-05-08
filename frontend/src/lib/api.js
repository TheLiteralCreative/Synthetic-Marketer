// Lightweight API client. Uses relative URLs — Vite dev proxies /api to the
// backend at :8000, and in production FastAPI serves both API and static.

async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    const err = new Error(`API ${res.status}: ${path}`);
    err.detail = detail;
    err.status = res.status;
    throw err;
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  ping: () => request('/ping'),
  getSettings: () => request('/settings'),
  putSettings: (payload) => request('/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  }),
};
