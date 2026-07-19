export function IconRadar({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <circle cx="12" cy="12" r="9" opacity="0.35" />
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
      <path d="M12 12L19 8" strokeLinecap="round" />
    </svg>
  );
}

export function IconShield({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconClipboard({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <rect x="7" y="4" width="10" height="16" rx="2" />
      <path d="M9 4V3h6v1" />
      <path d="M9 10h6M9 14h4" strokeLinecap="round" />
    </svg>
  );
}

export function IconAudit({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M6 4h12v16H6z" />
      <path d="M9 8h6M9 12h6M9 16h4" strokeLinecap="round" />
      <circle cx="17" cy="17" r="4" fill="var(--bg-secondary)" />
      <path d="M15.5 17l1 1 2.5-2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconActivity({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 12h4l2-7 4 14 2-7h6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconLink({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 007.07 0l2.83-2.83a5 5 0 00-7.07-7.07L11 4" strokeLinecap="round" />
      <path d="M14 11a5 5 0 00-7.07 0L4.1 13.83a5 5 0 007.07 7.07L13 20" strokeLinecap="round" />
    </svg>
  );
}

export function IconAlert({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
      <path d="M12 9v4M12 17h.01" strokeLinecap="round" />
      <path d="M10.3 4.5L2.6 18a2 2 0 001.7 3h15.4a2 2 0 001.7-3L13.7 4.5a2 2 0 00-3.4 0z" />
    </svg>
  );
}
