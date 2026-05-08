// Circular score gauge — matches the dashboard PDF visual style.
// Color tracks score band: red <40, amber 40-54, blue 55-69, green 70+

function colorForScore(score) {
  if (score == null) return 'var(--color-text-muted)';
  if (score >= 70) return 'var(--color-success)';
  if (score >= 55) return 'var(--color-accent)';
  if (score >= 40) return 'var(--color-warning)';
  return 'var(--color-danger)';
}

export default function ScoreGauge({ score, grade, size = 180 }) {
  const radius = size * 0.42;
  const stroke = size * 0.08;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.max(0, Math.min(100, score ?? 0)) / 100;
  const dash = circumference * pct;
  const color = colorForScore(score);

  return (
    <div className="score-gauge" style={{ width: size, textAlign: 'center' }}>
      <svg width={size} height={size} style={{ display: 'block' }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="var(--color-border)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: 'stroke-dasharray 600ms ease-out' }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.32}
          fontWeight="700"
          fill="var(--color-primary)"
          fontFamily="var(--font-sans)"
        >
          {score ?? '—'}
        </text>
        <text
          x="50%"
          y="68%"
          textAnchor="middle"
          dominantBaseline="central"
          fontSize={size * 0.085}
          fill="var(--color-text-muted)"
          fontFamily="var(--font-sans)"
        >
          / 100
        </text>
      </svg>
      {grade && (
        <div style={{ marginTop: '0.5rem' }}>
          <span
            style={{
              display: 'inline-block',
              padding: '0.2rem 0.7rem',
              background: color,
              color: 'white',
              borderRadius: 'var(--radius)',
              fontWeight: 700,
              fontSize: '0.95em',
              letterSpacing: '0.04em',
            }}
          >
            Grade {grade}
          </span>
        </div>
      )}
    </div>
  );
}

export { colorForScore };
