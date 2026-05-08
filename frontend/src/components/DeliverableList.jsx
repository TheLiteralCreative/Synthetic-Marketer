// File row for each deliverable — opens PDF inline (browser tab) by default,
// "Open in app" button hits the backend to launch the OS default viewer.

const ICON_BY_LABEL = {
  'Executive brief': '📋',
  'Walkthrough': '🧭',
  'Marketing audit': '📊',
  'Competitor report': '🎯',
  'Audience report': '👥',
  'Implementation roadmap': '🛠',
  'Glossary': '📖',
  'Dashboard PDF': '📈',
  'Full bundled report': '📚',
  'Discovery digest': '🔍',
  'Discovery checklist': '✅',
  'QA report': '🛡',
};


function formatSize(kb) {
  if (kb == null) return '';
  if (kb < 1024) return `${kb} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}


export default function DeliverableList({ binName, deliverables, extras, onOpenInApp }) {
  return (
    <div className="deliverable-list">
      {deliverables.map((d) => {
        const icon = ICON_BY_LABEL[d.label] || '📄';
        const pdfHref = d.pdf ? `/api/bins/${binName}/file/${encodeURIComponent(d.pdf)}` : null;
        const mdHref = d.md ? `/api/bins/${binName}/file/${encodeURIComponent(d.md)}` : null;
        return (
          <div key={d.label} className="deliverable-row">
            <span className="deliverable-icon">{icon}</span>
            <div className="deliverable-meta">
              <div className="deliverable-name">{d.label}</div>
              <div className="muted deliverable-blurb">{d.blurb}</div>
            </div>
            <div className="deliverable-actions">
              {d.size_kb != null && (
                <span className="muted mono deliverable-size">
                  {formatSize(d.size_kb)}
                </span>
              )}
              {pdfHref && (
                <a href={pdfHref} target="_blank" rel="noreferrer" className="link-button">
                  Open PDF
                </a>
              )}
              {d.pdf && (
                <button
                  type="button"
                  onClick={() => onOpenInApp(d.pdf)}
                  className="link-button-secondary"
                  title="Open in your OS default viewer (e.g. Preview)"
                >
                  ↗
                </button>
              )}
              {!pdfHref && mdHref && (
                <a href={mdHref} target="_blank" rel="noreferrer" className="link-button">
                  Open MD
                </a>
              )}
            </div>
          </div>
        );
      })}

      {extras && extras.length > 0 && (
        <details style={{ marginTop: '1rem' }}>
          <summary className="muted" style={{ cursor: 'pointer', fontSize: '0.9em' }}>
            Extras ({extras.length}) — discovery digest, QA report, dashboard PDF, bundled report
          </summary>
          <div style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {extras.map((e) => {
              const href = `/api/bins/${binName}/file/${encodeURIComponent(e.name)}`;
              return (
                <div key={e.name} className="extra-row">
                  <span className="mono muted">{e.name}</span>
                  <span className="muted" style={{ fontSize: '0.8em' }}>{e.label}</span>
                  <span className="muted mono" style={{ fontSize: '0.8em' }}>{formatSize(e.size_kb)}</span>
                  <a href={href} target="_blank" rel="noreferrer" className="link-button-secondary">
                    Open
                  </a>
                </div>
              );
            })}
          </div>
        </details>
      )}
    </div>
  );
}
