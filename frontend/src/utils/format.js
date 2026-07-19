export function formatTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatPercent(value, digits = 0) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatZone(zoneId) {
  if (!zoneId) return 'Unknown zone';
  return zoneId.replace(/^zone_[a-z]_/, '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
