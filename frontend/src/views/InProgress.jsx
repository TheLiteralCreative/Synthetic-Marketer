import { useEffect, useReducer, useRef } from 'react';
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom';
import { api, subscribeToAudit } from '../lib/api.js';
import PhaseTimeline from '../components/PhaseTimeline.jsx';
import CostMeter from '../components/CostMeter.jsx';
import LogStream from '../components/LogStream.jsx';

const initialState = {
  phases: {},        // { 1: { status, detail, startedAt, finishedAt }, ... }
  subagents: {},     // { 'content': { status, detail }, ... }
  log: [],           // [{ time, text }]
  cost: { tokensIn: 0, tokensOut: 0, costUsd: 0 },
  status: 'connecting',  // connecting | running | done | failed | cancelled
  score: null,
  error: null,
  finalDetail: null,
  startedAt: Date.now(),
  finishedAt: null,
};

function reducer(state, ev) {
  const t = new Date().toLocaleTimeString();
  switch (ev.kind) {
    case 'phase': {
      const num = ev.phase;
      const prev = state.phases[num] || {};
      const next = {
        ...state.phases,
        [num]: {
          ...prev,
          status: ev.status,
          detail: ev.detail || prev.detail,
          startedAt: ev.status === 'running' ? Date.now() : prev.startedAt,
          finishedAt: ev.status === 'done' || ev.status === 'failed' ? Date.now() : prev.finishedAt,
        },
      };
      return {
        ...state,
        phases: next,
        status: state.status === 'connecting' ? 'running' : state.status,
        log: [...state.log, { time: t, text: `Phase ${num} ${ev.status}${ev.detail ? ': ' + ev.detail : ''}` }].slice(-200),
      };
    }
    case 'subagent': {
      const id = ev.subagent_id;
      return {
        ...state,
        subagents: { ...state.subagents, [id]: { status: ev.status, detail: ev.detail } },
        log: [...state.log, { time: t, text: `[subagent ${id}] ${ev.status}${ev.detail ? ': ' + ev.detail : ''}` }].slice(-200),
      };
    }
    case 'cost': {
      return {
        ...state,
        cost: {
          tokensIn: state.cost.tokensIn + (ev.cost_tokens_in || 0),
          tokensOut: state.cost.tokensOut + (ev.cost_tokens_out || 0),
          costUsd: state.cost.costUsd + (ev.cost_usd || 0),
        },
      };
    }
    case 'log': {
      const text = ev.detail || '';
      if (text === 'heartbeat') return state;
      return {
        ...state,
        log: [...state.log, { time: t, text }].slice(-200),
      };
    }
    case 'done': {
      return {
        ...state,
        status: 'done',
        score: ev.score,
        finishedAt: Date.now(),
        log: [...state.log, { time: t, text: `Audit complete. Score: ${ev.score}/100` }].slice(-200),
      };
    }
    case 'error': {
      return {
        ...state,
        status: 'failed',
        error: ev.error,
        finishedAt: Date.now(),
        log: [...state.log, { time: t, text: `ERROR: ${ev.error}` }].slice(-200),
      };
    }
    default:
      return state;
  }
}

export default function InProgress() {
  const { jobId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const binName = location.state?.binName;
  const model = location.state?.model;

  const [state, dispatch] = useReducer(reducer, initialState);
  const unsubRef = useRef(null);

  useEffect(() => {
    unsubRef.current = subscribeToAudit(
      jobId,
      (event) => dispatch(event),
      () => dispatch({ kind: 'log', detail: 'connection lost — reconnecting…' }),
    );
    return () => {
      if (unsubRef.current) unsubRef.current();
    };
  }, [jobId]);

  const cancel = async () => {
    if (!confirm('Cancel this audit? Already-completed phases will keep their output.')) return;
    try {
      await api.cancelAudit(jobId);
    } catch (e) {
      alert(`Cancel failed: ${e.message}`);
    }
  };

  const elapsed = ((state.finishedAt || Date.now()) - state.startedAt) / 1000;
  const isRunning = state.status === 'running' || state.status === 'connecting';
  const isDone = state.status === 'done';
  const isFailed = state.status === 'failed' || state.status === 'cancelled';

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '1rem', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0 }}>
          {isRunning && '⏳ '}
          {isDone && '✅ '}
          {isFailed && '✗ '}
          Audit {state.status}
        </h2>
        {binName && <span className="muted mono">{binName}</span>}
        <span className="muted mono" style={{ marginLeft: 'auto' }}>
          {elapsed.toFixed(0)}s elapsed
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1.5rem', alignItems: 'start' }}>
        <div className="card">
          <PhaseTimeline phases={state.phases} subagents={state.subagents} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <CostMeter
            tokensIn={state.cost.tokensIn}
            tokensOut={state.cost.tokensOut}
            costUsd={state.cost.costUsd}
            model={model}
          />

          {isRunning && (
            <button onClick={cancel} style={{ borderColor: 'var(--color-danger)', color: 'var(--color-danger)' }}>
              ✕ Cancel audit
            </button>
          )}

          {isDone && (
            <div className="card" style={{ borderColor: 'var(--color-success)' }}>
              <div className="muted" style={{ fontSize: '0.8em', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Final score
              </div>
              <div className="mono" style={{ fontSize: '2.4em', fontWeight: 700, color: 'var(--color-primary)' }}>
                {state.score ?? '—'}
                <span className="muted" style={{ fontSize: '0.5em', fontWeight: 400 }}> /100</span>
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {binName && (
                  <Link to={`/audits/bin/${encodeURIComponent(binName)}`} className="primary" style={{
                    display: 'block', textAlign: 'center', textDecoration: 'none',
                    background: 'var(--color-primary)', color: 'white',
                    padding: '0.5rem 1rem', borderRadius: 'var(--radius)',
                  }}>
                    Open audit detail →
                  </Link>
                )}
                <button onClick={() => navigate('/all')}>All audits</button>
                <button onClick={() => navigate('/new')}>New audit</button>
              </div>
            </div>
          )}

          {isFailed && (
            <div className="card" style={{ borderColor: 'var(--color-danger)' }}>
              <div style={{ color: 'var(--color-danger)', fontWeight: 600 }}>
                Audit {state.status === 'cancelled' ? 'cancelled' : 'failed'}
              </div>
              {state.error && (
                <div className="mono" style={{ fontSize: '0.85em', marginTop: '0.5rem', color: 'var(--color-text-muted)' }}>
                  {state.error}
                </div>
              )}
              <button onClick={() => navigate('/new')} style={{ marginTop: '0.75rem' }}>
                ← Back to New audit
              </button>
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <LogStream entries={state.log} />
      </div>
    </>
  );
}
