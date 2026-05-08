import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';

const MODELS = [
  { id: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5 — fastest, cheapest' },
  { id: 'claude-sonnet-4-6',         label: 'Sonnet 4.6 — balanced' },
  { id: 'claude-opus-4-7',           label: 'Opus 4.7 — deepest analysis' },
];

export default function NewAudit() {
  const navigate = useNavigate();
  const [ping, setPing] = useState(null);
  const [pingErr, setPingErr] = useState(null);
  const [url, setUrl] = useState('');
  const [brand, setBrand] = useState('');
  const [model, setModel] = useState('claude-haiku-4-5-20251001');
  const [skipPsi, setSkipPsi] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.ping().then(setPing).catch(setPingErr);
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!url) return;
    setSubmitting(true);
    setErr(null);
    try {
      const result = await api.createAudit({
        url: url.trim(),
        brand: brand.trim() || null,
        model,
        skip_psi: skipPsi,
      });
      navigate(`/audits/${result.job_id}`, { state: { binName: result.bin_name, model } });
    } catch (e) {
      setErr(e.detail?.detail || e.message);
      setSubmitting(false);
    }
  };

  const ready = ping?.ready;

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Run a new audit</h2>
      <p className="muted">
        Fetches the site, runs the 8-phase pipeline (5 parallel subagents → audit
        → companion reports → PDFs), and produces a project bin in 5–15 minutes.
      </p>

      {pingErr && (
        <div className="card" style={{ borderColor: 'var(--color-danger)', marginBottom: '1.5rem' }}>
          <strong style={{ color: 'var(--color-danger)' }}>Backend unreachable.</strong>{' '}
          <span className="muted">{pingErr.message}</span>
        </div>
      )}
      {ping && !ready && (
        <div className="card" style={{ borderColor: 'var(--color-warning)', marginBottom: '1.5rem' }}>
          <strong style={{ color: 'var(--color-warning)' }}>API key not configured.</strong>{' '}
          <span className="muted">
            Set your Anthropic API key in <a href="/settings">Settings</a> before running an audit.
          </span>
        </div>
      )}

      <form onSubmit={submit} className="card" style={{ display: 'grid', gap: '1.25rem' }}>
        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
            Target URL <span style={{ color: 'var(--color-danger)' }}>*</span>
          </label>
          <input
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            disabled={submitting}
            autoFocus
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
            Brand name <span className="muted">(optional — auto-derived from URL)</span>
          </label>
          <input
            type="text"
            placeholder="(auto)"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            disabled={submitting}
          />
          <p className="muted" style={{ margin: '0.25rem 0 0', fontSize: '0.85em' }}>
            Used for the bin name: <code>Synth-mkt_{'{Brand}'}_{'{date}'}/</code>
          </p>
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
            Model
          </label>
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={submitting}>
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              style={{ width: 'auto' }}
              checked={skipPsi}
              onChange={(e) => setSkipPsi(e.target.checked)}
              disabled={submitting}
            />
            <span>Skip PageSpeed Insights (faster, no Core Web Vitals data)</span>
          </label>
        </div>

        {err && (
          <div style={{ color: 'var(--color-danger)', fontSize: '0.9em' }}>
            <strong>Failed to start:</strong> {err}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
          <button type="submit" className="primary" disabled={!ready || submitting || !url}>
            {submitting ? 'Starting…' : 'Run audit ▶'}
          </button>
          <span className="muted" style={{ fontSize: '0.9em' }}>
            Estimated time: 5–15 min
          </span>
        </div>
      </form>
    </>
  );
}
