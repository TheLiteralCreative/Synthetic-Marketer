import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [draft, setDraft] = useState({});
  const [savedAt, setSavedAt] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(setErr);
  }, []);

  if (err) {
    return (
      <>
        <h2>Settings</h2>
        <p style={{ color: 'var(--color-danger)' }}>
          Couldn't load settings: <code>{err.message}</code>
        </p>
      </>
    );
  }
  if (!settings) return <p className="muted">Loading...</p>;

  const update = (key, value) => setDraft({ ...draft, [key]: value });
  const isDirty = Object.keys(draft).length > 0;

  const save = async () => {
    try {
      const next = await api.putSettings(draft);
      setSettings(next);
      setDraft({});
      setSavedAt(Date.now());
    } catch (e) {
      setErr(e);
    }
  };

  return (
    <>
      <h2 style={{ marginTop: 0 }}>Settings</h2>
      <p className="muted">
        Stored locally at <code>data/settings.json</code>. API keys are never
        committed to the repo (the file is gitignored).
      </p>

      <div className="card" style={{ marginTop: '1.5rem', display: 'grid', gap: '1.25rem' }}>
        <Field
          label="Anthropic API key"
          hint="Used by the audit pipeline to drive Claude subagents. Required to run audits."
          value={draft.anthropic_api_key ?? ''}
          placeholder={settings.anthropic_api_key || 'sk-ant-...'}
          onChange={(v) => update('anthropic_api_key', v)}
          isPassword
        />
        <Field
          label="PageSpeed Insights API key"
          hint="Optional. Lifts the 429 rate limit on Lighthouse runs during discovery."
          value={draft.psi_api_key ?? ''}
          placeholder={settings.psi_api_key || '(none — anonymous PSI used, may rate-limit)'}
          onChange={(v) => update('psi_api_key', v)}
          isPassword
        />
        <Field
          label="Output folder"
          hint="Where new project bins are created."
          value={draft.output_folder ?? settings.output_folder}
          onChange={(v) => update('output_folder', v)}
        />
        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
            Theme
          </label>
          <select
            value={draft.theme ?? settings.theme}
            onChange={(e) => update('theme', e.target.value)}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              style={{ width: 'auto' }}
              checked={draft.track_costs ?? settings.track_costs}
              onChange={(e) => update('track_costs', e.target.checked)}
            />
            <span>Track API cost per audit</span>
          </label>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
          <button
            className="primary"
            disabled={!isDirty}
            onClick={save}
          >
            Save changes
          </button>
          {!isDirty && savedAt && (
            <span className="muted" style={{ fontSize: '0.9em' }}>
              Saved.
            </span>
          )}
        </div>
      </div>
    </>
  );
}

function Field({ label, hint, value, placeholder, onChange, isPassword }) {
  return (
    <div>
      <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.25rem' }}>
        {label}
      </label>
      {hint && (
        <p className="muted" style={{ margin: '0 0 0.5rem 0', fontSize: '0.9em' }}>
          {hint}
        </p>
      )}
      <input
        type={isPassword ? 'password' : 'text'}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
