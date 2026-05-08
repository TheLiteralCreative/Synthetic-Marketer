export default function CostMeter({ tokensIn, tokensOut, costUsd, model }) {
  const fmt = (n) => (n || 0).toLocaleString();
  return (
    <div className="cost-meter card" style={{ padding: '0.75rem 1rem' }}>
      <div className="muted" style={{ fontSize: '0.8em', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Running cost
      </div>
      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.4rem', alignItems: 'baseline' }}>
        <div>
          <div className="mono" style={{ fontSize: '1.4em', fontWeight: 600, color: 'var(--color-primary)' }}>
            ${(costUsd || 0).toFixed(4)}
          </div>
          <div className="muted" style={{ fontSize: '0.8em' }}>USD</div>
        </div>
        <div>
          <div className="mono" style={{ fontSize: '1em' }}>
            {fmt(tokensIn)} <span className="muted">in</span>
          </div>
          <div className="mono" style={{ fontSize: '1em' }}>
            {fmt(tokensOut)} <span className="muted">out</span>
          </div>
        </div>
        {model && (
          <div className="muted mono" style={{ fontSize: '0.85em', marginLeft: 'auto' }}>
            {model}
          </div>
        )}
      </div>
    </div>
  );
}
