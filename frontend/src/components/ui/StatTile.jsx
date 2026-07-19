export default function StatTile({ label, value, subtext, tone = 'neutral', mono = false }) {
  return (
    <div className={`stat-tile stat-tile--${tone}`}>
      <span className="stat-tile__label">{label}</span>
      <span className={`stat-tile__value${mono ? ' stat-tile__value--mono' : ''}`}>{value}</span>
      {subtext && <span className="stat-tile__subtext">{subtext}</span>}
    </div>
  );
}
