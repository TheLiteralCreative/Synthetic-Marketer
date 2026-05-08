const SUBAGENT_LABEL = {
  content: 'Content & Messaging',
  conversion: 'Conversion Optimization',
  seo: 'SEO & Discoverability',
  competitive: 'Competitive Positioning',
  brand_growth: 'Brand & Trust + Growth',
};

const ICON = {
  waiting: '⏸',
  running: '⏳',
  done: '✓',
  failed: '✗',
};

const COLOR = {
  waiting: 'var(--color-text-muted)',
  running: 'var(--color-accent)',
  done: 'var(--color-success)',
  failed: 'var(--color-danger)',
};

export default function SubagentList({ subagents }) {
  const order = Object.keys(SUBAGENT_LABEL);
  return (
    <ul className="subagent-list" style={{ listStyle: 'none', padding: '0.5rem 0 0 2.5rem', margin: 0 }}>
      {order.map((id) => {
        const s = subagents[id] || { status: 'running' };
        return (
          <li key={id} className="subagent-row" style={{ display: 'flex', gap: '0.75rem', padding: '0.2rem 0', fontSize: '0.92em' }}>
            <span style={{ color: COLOR[s.status], width: '1.2em' }}>
              {ICON[s.status]}
            </span>
            <span className="muted mono" style={{ width: '8em' }}>
              {id}
            </span>
            <span>{SUBAGENT_LABEL[id]}</span>
            {s.detail && <span className="muted">— {s.detail}</span>}
          </li>
        );
      })}
    </ul>
  );
}
