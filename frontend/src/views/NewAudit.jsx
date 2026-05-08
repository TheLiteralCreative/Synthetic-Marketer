import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function NewAudit() {
  const [ping, setPing] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api.ping()
      .then((data) => { if (!cancelled) setPing(data); })
      .catch((e) => { if (!cancelled) setErr(e); });
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Run a new audit</h2>
      <p className="muted">
        B1 foundation — backend wiring smoke test. The audit form lands in B3.
      </p>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>Backend status</h3>
        {err && (
          <p style={{ color: 'var(--color-danger)' }}>
            Backend unreachable: <code>{err.message}</code>
          </p>
        )}
        {ping && (
          <dl style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '0.5rem 1rem', margin: 0 }}>
            <dt className="muted">Service</dt>
            <dd style={{ margin: 0 }} className="mono">{ping.name}</dd>
            <dt className="muted">Version</dt>
            <dd style={{ margin: 0 }} className="mono">{ping.version}</dd>
            <dt className="muted">Status</dt>
            <dd style={{ margin: 0 }} className="mono">
              <span style={{ color: 'var(--color-success)' }}>{ping.status}</span>
            </dd>
            <dt className="muted">API key configured</dt>
            <dd style={{ margin: 0 }} className="mono">
              {ping.ready
                ? <span style={{ color: 'var(--color-success)' }}>yes</span>
                : <span style={{ color: 'var(--color-warning)' }}>no — set in Settings</span>}
            </dd>
          </dl>
        )}
        {!ping && !err && <p className="muted">Pinging backend...</p>}
      </div>

      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>What's next</h3>
        <ul style={{ marginBottom: 0 }}>
          <li><strong>B2</strong> — Pipeline runner with Claude Agent SDK + progress streaming</li>
          <li><strong>B3</strong> — This page becomes the actual New Audit form</li>
          <li><strong>B4</strong> — All Audits list + Audit Detail view</li>
          <li><strong>B5</strong> — Polish, design-system match to PDFs, demo</li>
        </ul>
      </div>
    </>
  );
}
