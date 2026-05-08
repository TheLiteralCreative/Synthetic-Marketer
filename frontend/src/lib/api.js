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
 *
 * IMPORTANT: When a `done` or `error` event arrives, this function closes the
 * EventSource so the browser doesn't auto-reconnect. Without this, the server
 * keeps replaying the event log on every reconnect — historically caused the
 * cost meter to inflate without bound.
 */
export function subscribeToAudit(jobId, onEvent, onError) {
  const url = `/api/audits/${jobId}/stream`;
  const source = new EventSource(url);
  let closed = false;

  const KINDS = ['phase', 'subagent', 'log', 'cost', 'done', 'error'];
  const handlers = {};

  for (const kind of KINDS) {
    handlers[kind] = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent({ kind, ...data });
        // Terminal events: close the connection ourselves so EventSource
        // doesn't auto-reconnect into a replay loop.
        if (kind === 'done' || kind === 'error') {
          closed = true;
          source.close();
        }
      } catch (err) {
        // ignore parse errors
      }
    };
    source.addEventListener(kind, handlers[kind]);
  }

  source.onerror = (e) => {
    if (!closed && source.readyState === EventSource.CLOSED && onError) {
      onError(e);
    }
  };

  return () => {
    closed = true;
    for (const kind of KINDS) {
      source.removeEventListener(kind, handlers[kind]);
    }
    source.close();
  };
}
