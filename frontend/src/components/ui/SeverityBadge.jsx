const SEVERITY_LABELS = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
};

export default function SeverityBadge({ severity, compact = false }) {
  const label = SEVERITY_LABELS[severity] || severity;
  return (
    <span className={`severity-badge severity-badge--${severity}${compact ? ' severity-badge--compact' : ''}`}>
      <span className="severity-badge__dot" />
      {label}
    </span>
  );
}
