import { colorForScore } from './ScoreGauge.jsx';

export default function CategoryBars({ categories }) {
  if (!categories || categories.length === 0) {
    return <p className="muted">(category breakdown unavailable)</p>;
  }

  return (
    <div className="category-bars">
      {categories.map((c) => {
        const score = c.score;
        const color = colorForScore(score);
        const pct = Math.max(0, Math.min(100, score ?? 0));
        return (
          <div key={c.name} className="category-row">
            <div className="category-label">
              <span className="category-name">{c.name}</span>
              <span className="muted category-weight">{c.weight}%</span>
            </div>
            <div className="category-bar-track">
              <div
                className="category-bar-fill"
                style={{
                  width: `${pct}%`,
                  background: color,
                }}
              />
            </div>
            <div className="category-score mono" style={{ color }}>
              {score ?? '—'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
