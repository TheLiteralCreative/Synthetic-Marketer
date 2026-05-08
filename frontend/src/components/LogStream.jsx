import { useEffect, useRef, useState } from 'react';

export default function LogStream({ entries }) {
  const [open, setOpen] = useState(false);
  const scrollerRef = useRef(null);

  useEffect(() => {
    if (open && scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [entries, open]);

  return (
    <div className="card" style={{ padding: 0 }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: '100%',
          textAlign: 'left',
          background: 'transparent',
          border: 'none',
          padding: '0.75rem 1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span style={{ fontSize: '0.8em' }}>{open ? '▼' : '▶'}</span>
        <span style={{ fontWeight: 600 }}>Live log</span>
        <span className="muted" style={{ fontSize: '0.85em' }}>
          ({entries.length} entries)
        </span>
      </button>
      {open && (
        <div
          ref={scrollerRef}
          className="mono"
          style={{
            padding: '0.5rem 1rem 1rem',
            fontSize: '0.85em',
            maxHeight: '240px',
            overflowY: 'auto',
            borderTop: '1px solid var(--color-border)',
            color: 'var(--color-text-muted)',
            lineHeight: 1.45,
          }}
        >
          {entries.length === 0 && (
            <div className="muted" style={{ fontStyle: 'italic' }}>(no log entries yet)</div>
          )}
          {entries.map((e, i) => (
            <div key={i} style={{ display: 'flex', gap: '0.6rem' }}>
              <span style={{ opacity: 0.5, flexShrink: 0 }}>{e.time}</span>
              <span style={{ wordBreak: 'break-word' }}>{e.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
