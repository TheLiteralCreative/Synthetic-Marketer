import SubagentList from './SubagentList.jsx';

const PHASES = [
  { num: 1, name: 'Discovery', detail: 'Site crawl, schema validation, PageSpeed Insights' },
  { num: 2, name: '5 audit subagents', detail: 'Content / Conversion / SEO / Competitive / Brand+Growth' },
  { num: 3, name: 'Aggregate audit', detail: 'Synthesize MARKETING-AUDIT.md from subagent outputs' },
  { num: 4, name: 'Companion reports', detail: 'COMPETITOR-REPORT + ADS-AUDIENCE in parallel' },
  { num: 5, name: 'Standard deliverables', detail: 'Brief / Walkthrough / Roadmap / Glossary' },
  { num: 6, name: 'QA pass', detail: '10 mechanical checks for ship-readiness' },
  { num: 7, name: 'Dashboard PDF', detail: 'Score gauge, bar chart, findings table' },
  { num: 8, name: 'Human-friendly PDFs', detail: 'Per-markdown PDFs + bundled FULL-REPORT.pdf' },
];

const STATUS_ICON = {
  waiting: '⏸',
  running: '⏳',
  done: '✓',
  failed: '✗',
};

const STATUS_COLOR = {
  waiting: 'var(--color-text-muted)',
  running: 'var(--color-accent)',
  done: 'var(--color-success)',
  failed: 'var(--color-danger)',
};

export default function PhaseTimeline({ phases, subagents }) {
  return (
    <ol className="phase-timeline" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {PHASES.map(({ num, name, detail }) => {
        const state = phases[num] || { status: 'waiting' };
        const status = state.status || 'waiting';
        const startedAt = state.startedAt;
        const finishedAt = state.finishedAt;
        const elapsed = startedAt
          ? ((finishedAt || Date.now()) - startedAt) / 1000
          : null;

        return (
          <li key={num} className="phase-row" data-status={status}>
            <div className="phase-row-main">
              <span
                className="phase-icon"
                style={{
                  color: STATUS_COLOR[status],
                  animation: status === 'running' ? 'pulse 1.5s ease-in-out infinite' : 'none',
                }}
              >
                {STATUS_ICON[status]}
              </span>
              <span className="phase-num muted mono">P{num}</span>
              <span className="phase-name">{name}</span>
              <span className="phase-detail muted">{state.detail || detail}</span>
              {elapsed !== null && (
                <span className="phase-elapsed muted mono">{elapsed.toFixed(1)}s</span>
              )}
            </div>
            {num === 2 && subagents && Object.keys(subagents).length > 0 && (
              <SubagentList subagents={subagents} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
