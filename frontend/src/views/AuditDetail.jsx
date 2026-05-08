import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ScoreGauge from '../components/ScoreGauge.jsx';
import CategoryBars from '../components/CategoryBars.jsx';
import DeliverableList from '../components/DeliverableList.jsx';

const QA_BADGE = {
  ready:    { text: '✅ Ready to ship',  color: 'var(--color-success)' },
  warnings: { text: '⚠️ Review first',   color: 'var(--color-warning)' },
  critical: { text: '🛑 Do not ship',    color: 'var(--color-danger)' },
  unknown:  { text: 'QA unknown',         color: 'var(--color-text-muted)' },
};

const SEV_COLOR = {
  Critical: 'var(--color-critical)',
  High: 'var(--color-high)',
  Medium: 'var(--color-medium)',
  Low: 'var(--color-low)',
};


export default function AuditDetail() {
  const { binName } = useParams();
  const [meta, setMeta] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);
  const [toast, setToast] = useState(null);

  const load = () => {
    setErr(null);
    fetch(`/api/bins/${encodeURIComponent(binName)}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(await r.text());
        return r.json();
      })
      .then(setMeta)
      .catch(setErr);
  };

  useEffect(load, [binName]);

  const callOp = async (label, fn) => {
    setBusy(label);
    try {
      await fn();
      setToast(`${label} ✓`);
      setTimeout(() => setToast(null), 2500);
    } catch (e) {
      setToast(`${label} failed: ${e.message}`);
      setTimeout(() => setToast(null), 4000);
    } finally {
      setBusy(null);
    }
  };

  const openFolder = () => callOp('Open folder', async () => {
    const r = await fetch(`/api/bins/${encodeURIComponent(binName)}/open`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: 'folder' }),
    });
    if (!r.ok) throw new Error(await r.text());
  });

  const openInApp = (filename) => callOp(`Open ${filename}`, async () => {
    const r = await fetch(`/api/bins/${encodeURIComponent(binName)}/open`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: filename }),
    });
    if (!r.ok) throw new Error(await r.text());
  });

  const rerender = () => callOp('Re-render PDFs', async () => {
    const r = await fetch(`/api/bins/${encodeURIComponent(binName)}/rerender`, {
      method: 'POST',
    });
    if (!r.ok) throw new Error(await r.text());
    load();
  });

  if (err) {
    return (
      <>
        <h2>Audit detail</h2>
        <p style={{ color: 'var(--color-danger)' }}>
          Couldn't load bin: <code>{err.message}</code>
        </p>
        <Link to="/all">← Back to all audits</Link>
      </>
    );
  }
  if (!meta) return <p className="muted">Loading…</p>;

  const qa = meta.qa ? QA_BADGE[meta.qa.status] || QA_BADGE.unknown : QA_BADGE.unknown;

  return (
    <>
      {toast && (
        <div className="toast" style={{
          position: 'fixed', top: '1rem', right: '1rem',
          background: 'var(--color-primary)', color: 'white',
          padding: '0.6rem 1rem', borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow-md)', zIndex: 100, fontSize: '0.9em',
        }}>
          {toast}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <h2 style={{ margin: 0 }}>{meta.name}</h2>
        <span style={{
          display: 'inline-block', padding: '0.15rem 0.6rem',
          background: qa.color, color: 'white',
          borderRadius: 'var(--radius)', fontSize: '0.8em',
          fontWeight: 600,
        }}>
          {qa.text}
        </span>
      </div>
      <p className="muted" style={{ margin: '0 0 1.5rem 0' }}>
        {meta.url && <a href={meta.url} target="_blank" rel="noreferrer">{meta.url}</a>}
        {meta.date && <> · {meta.date}</>}
        {meta.business_type && <> · <span style={{ fontSize: '0.92em' }}>{meta.business_type}</span></>}
      </p>

      <div className="audit-detail-grid">
        {/* Left column: gauge + categories */}
        <div className="card">
          <div style={{ display: 'flex', gap: '2rem', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
            <ScoreGauge score={meta.score} grade={meta.grade} />
            <div style={{ flex: 1, minWidth: '300px' }}>
              <h3 style={{ marginTop: 0, marginBottom: '0.75rem' }}>Score breakdown</h3>
              <CategoryBars categories={meta.categories} />
            </div>
          </div>
        </div>

        {/* Right column: actions + QA */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="card">
            <h4 style={{ marginTop: 0, marginBottom: '0.75rem' }}>Actions</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button onClick={openFolder} disabled={busy != null}>
                📂 Open bin folder
              </button>
              <button onClick={rerender} disabled={busy != null}>
                🔄 {busy === 'Re-render PDFs' ? 'Rendering…' : 'Re-render PDFs'}
              </button>
              <Link to="/all" style={{
                textAlign: 'center', padding: '0.5rem', borderRadius: 'var(--radius)',
                border: '1px solid var(--color-border)', textDecoration: 'none',
                color: 'var(--color-text)', fontSize: '0.9em',
              }}>
                ← All audits
              </Link>
            </div>
          </div>

          {meta.qa && meta.qa.status !== 'ready' && (
            <div className="card" style={{ borderColor: qa.color }}>
              <h4 style={{ marginTop: 0, color: qa.color }}>QA status</h4>
              <div className="muted" style={{ fontSize: '0.9em' }}>
                {meta.qa.critical} critical · {meta.qa.warnings} warnings
              </div>
              <p style={{ fontSize: '0.85em', marginTop: '0.5rem', marginBottom: 0 }}>
                See <code>_QA-REPORT.md</code> for details (in extras below).
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Top findings */}
      {meta.findings.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0 }}>Top findings ({meta.findings.length})</h3>
          <ul className="findings-list">
            {meta.findings.map((f, i) => (
              <li key={i} className="findings-row">
                <span className="findings-sev mono" style={{ color: SEV_COLOR[f.severity] || 'var(--color-text-muted)' }}>
                  {f.severity}
                </span>
                <span className="findings-text">{f.finding}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Deliverables */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h3 style={{ marginTop: 0 }}>Deliverables</h3>
        <DeliverableList
          binName={meta.name}
          deliverables={meta.deliverables}
          extras={meta.extras}
          onOpenInApp={openInApp}
        />
      </div>
    </>
  );
}
