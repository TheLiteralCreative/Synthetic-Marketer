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
  createAudit: (payload) => request('/audits', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getAudit: (jobId) => request(`/audits/${jobId}`),
  cancelAudit: (jobId) => request(`/audits/${jobId}/cancel`, { method: 'POST' }),
  listAudits: () => request('/audits'),
};

/**
 * Subscribe to a job's SSE progress stream.
 * Returns an unsubscribe function.
 *
 * onEvent receives parsed event objects: { kind, phase, status, detail, ... }
 */
export function subscribeToAudit(jobId, onEvent, onError) {
  const url = `/api/audits/${jobId}/stream`;
  const source = new EventSource(url);

  // The backend uses sse-starlette's typed events: phase, subagent, log,
  // cost, done, error. EventSource fires named-event listeners separately
  // from the default 'message' listener.
  const KINDS = ['phase', 'subagent', 'log', 'cost', 'done', 'error'];
  const handlers = {};

  for (const kind of KINDS) {
    handlers[kind] = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent({ kind, ...data });
      } catch (err) {
        // ignore parse errors
      }
    };
    source.addEventListener(kind, handlers[kind]);
  }

  source.onerror = (e) => {
    if (source.readyState === EventSource.CLOSED && onError) {
      onError(e);
    }
  };

  return () => {
    for (const kind of KINDS) {
      source.removeEventListener(kind, handlers[kind]);
    }
    source.close();
  };
}
