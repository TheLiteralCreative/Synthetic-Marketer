import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { colorForScore } from '../components/ScoreGauge.jsx';

const API_LIST_URL = '/api/bins';

const QA_BADGE = {
  ready:    { text: 'ready',    color: 'var(--color-success)' },
  warnings: { text: 'warnings', color: 'var(--color-warning)' },
  critical: { text: 'critical', color: 'var(--color-danger)' },
};

function formatDate(timestamp) {
  if (!timestamp) return '—';
  const d = new Date(timestamp * 1000);
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}


export default function AllAudits() {
  const [bins, setBins] = useState(null);
  const [outputFolder, setOutputFolder] = useState(null);
  const [err, setErr] = useState(null);
  const [sort, setSort] = useState({ key: 'modified', dir: 'desc' });

  useEffect(() => {
    fetch(API_LIST_URL)
      .then((r) => r.json())
      .then((d) => {
        setBins(d.bins);
        setOutputFolder(d.output_folder);
      })
      .catch(setErr);
  }, []);

  if (err) {
    return (
      <>
        <h2 style={{ marginTop: 0 }}>All audits</h2>
        <p style={{ color: 'var(--color-danger)' }}>Couldn't load: {err.message}</p>
      </>
    );
  }
  if (bins == null) return <p className="muted">Loading…</p>;

  const sorted = [...bins].sort((a, b) => {
    const av = a[sort.key];
    const bv = b[sort.key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  const setSortBy = (key) => {
    setSort(sort.key === key
      ? { key, dir: sort.dir === 'asc' ? 'desc' : 'asc' }
      : { key, dir: key === 'name' ? 'asc' : 'desc' }
    );
  };

  const SortHeader = ({ k, label, align = 'left' }) => (
    <th
      onClick={() => setSortBy(k)}
      style={{ cursor: 'pointer', textAlign: align, userSelect: 'none' }}
    >
      {label}
      {sort.key === k && (
        <span className="muted" style={{ marginLeft: 4 }}>
          {sort.dir === 'asc' ? '↑' : '↓'}
        </span>
      )}
    </th>
  );

  return (
    <>
      <h2 style={{ marginTop: 0 }}>All audits</h2>
      <p className="muted">
        Project bins in <code>{outputFolder}</code> — {bins.length} total.
      </p>

      {bins.length === 0 ? (
        <div className="card">
          <p className="muted" style={{ margin: 0 }}>
            No audits yet. <Link to="/new">Run your first one →</Link>
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="audits-table">
            <thead>
              <tr>
                <SortHeader k="name" label="Bin" />
                <SortHeader k="score" label="Score" align="right" />
                <SortHeader k="qa" label="QA" align="center" />
                <th>URL</th>
                <SortHeader k="modified" label="Date" />
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((b) => {
                const qa = QA_BADGE[b.qa];
                const color = colorForScore(b.score);
                return (
                  <tr key={b.name}>
                    <td>
                      <Link to={`/audits/bin/${encodeURIComponent(b.name)}`}>
                        <span className="mono" style={{ fontSize: '0.92em' }}>{b.name}</span>
                      </Link>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="mono" style={{ color, fontWeight: 600, fontSize: '1.05em' }}>
                        {b.score ?? '—'}
                      </span>
                      <span className="muted mono" style={{ fontSize: '0.8em' }}>
                        {b.grade !== '?' ? ` ${b.grade}` : ''}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      {qa ? (
                        <span style={{
                          display: 'inline-block',
                          padding: '0.1rem 0.5rem',
                          borderRadius: 'var(--radius)',
                          background: qa.color,
                          color: 'white',
                          fontSize: '0.75em',
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                        }}>
                          {qa.text}
                        </span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td className="muted mono" style={{ fontSize: '0.85em' }}>
                      {b.url ? new URL(b.url).hostname : '—'}
                    </td>
                    <td className="muted" style={{ fontSize: '0.85em' }}>
                      {formatDate(b.modified)}
                    </td>
                    <td>
                      <Link
                        to={`/audits/bin/${encodeURIComponent(b.name)}`}
                        style={{ fontSize: '0.85em' }}
                      >
                        Open →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
