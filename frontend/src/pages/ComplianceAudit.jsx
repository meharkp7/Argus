import { useState } from 'react';
import { api } from '../api/client';
import SeverityBadge from '../components/ui/SeverityBadge';
import StatTile from '../components/ui/StatTile';
import { formatPercent } from '../utils/format';

const FRAMEWORKS = ['OISD', 'DGMS', 'Factory Act'];

const SAMPLE_PROCEDURE = `Hot Work Procedure — Tank Farm Zone B

1. Obtain hot work permit from area authority before commencing work.
2. Ensure continuous gas monitoring is active in the work zone.
3. Fire watch personnel must be stationed during all hot work operations.
4. Emergency response plan must be reviewed with crew before start.
5. All personnel must wear appropriate PPE including fire-resistant clothing.`;

function ScoreRing({ score }) {
  const pct = Math.round(score * 100);
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score * circumference);
  const color = score >= 0.8 ? '#4ade80' : score >= 0.5 ? '#fbbf24' : '#f87171';

  return (
    <div className="score-ring">
      <svg width="92" height="92" viewBox="0 0 92 92">
        <circle cx="46" cy="46" r={radius} fill="none" stroke="rgba(148,163,184,0.12)" strokeWidth="8" />
        <circle
          cx="46"
          cy="46"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="score-ring__value">{pct}%</span>
    </div>
  );
}

export default function ComplianceAudit() {
  const [documentText, setDocumentText] = useState(SAMPLE_PROCEDURE);
  const [frameworks, setFrameworks] = useState(FRAMEWORKS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const toggleFramework = (fw) => {
    setFrameworks((prev) =>
      prev.includes(fw) ? prev.filter((f) => f !== fw) : [...prev, fw]
    );
  };

  const handleAudit = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await api.complianceAudit(documentText, frameworks);
      setResult(res);
    } catch (err) {
      console.error('Compliance audit failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const criticalGaps = result?.gaps?.filter((g) => g.severity === 'critical' || g.severity === 'high').length ?? 0;

  return (
    <>
      <section className="kpi-grid">
        <StatTile label="Frameworks" value={frameworks.length} subtext={frameworks.join(' · ') || 'None selected'} tone="accent" />
        <StatTile label="Compliance Score" value={result ? formatPercent(result.compliance_score, 0) : '—'} subtext={result?.document_type ?? 'Awaiting audit'} tone={result ? (result.compliance_score >= 0.8 ? 'success' : result.compliance_score >= 0.5 ? 'warn' : 'danger') : 'neutral'} />
        <StatTile label="Gaps Found" value={result?.gaps?.length ?? 0} subtext={`${criticalGaps} high severity`} tone={result?.gaps?.length ? 'warn' : 'success'} />
        <StatTile label="Document Size" value={`${documentText.split(/\s+/).filter(Boolean).length} words`} subtext="Procedure under review" tone="neutral" />
      </section>

      <div className="page-toolbar">
        <h3>RAG-backed regulatory gap analysis against Indian heavy-industry frameworks</h3>
        <button type="button" className="btn btn-primary" onClick={handleAudit} disabled={loading || !documentText.trim() || frameworks.length === 0}>
          {loading ? 'Auditing…' : 'Run Compliance Audit'}
        </button>
      </div>

      <div className="grid-2">
        <div className="card card--glass doc-editor">
          <div className="card-header">
            <span className="card-title">Document Under Review</span>
            <span className="pill">{frameworks.length} frameworks</span>
          </div>
          <textarea
            value={documentText}
            onChange={(e) => setDocumentText(e.target.value)}
            placeholder="Paste safety procedure, permit-to-work, or method statement…"
          />
          <div style={{ marginTop: '1rem' }}>
            <span className="label">Applicable Frameworks</span>
            <div className="feedback-buttons">
              {FRAMEWORKS.map((fw) => (
                <button
                  key={fw}
                  type="button"
                  className={`feedback-btn ${frameworks.includes(fw) ? 'active-useful' : ''}`}
                  onClick={() => toggleFramework(fw)}
                >
                  {fw}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="card card--glass">
          {!result ? (
            <div className="empty-state">
              <span className="empty-state__eyebrow">Compliance Engine</span>
              <h3>Audit against live corpus</h3>
              <p>Procedures are checked against OISD guidelines, DGMS circulars, and Factory Act clauses indexed in the ARGUS RAG store.</p>
            </div>
          ) : (
            <>
              <div className="card-header">
                <span className="card-title">Audit Results</span>
              </div>
              <div className="score-ring-wrap">
                <ScoreRing score={result.compliance_score} />
                <div>
                  <h3>{formatPercent(result.compliance_score, 0)} compliant</h3>
                  <p className="muted">{result.summary}</p>
                </div>
              </div>
              {result.gaps.length === 0 ? (
                <div className="callout callout--accent">No material compliance gaps detected for the selected frameworks.</div>
              ) : (
                result.gaps.map((gap) => (
                  <article key={gap.gap_id} className="gap-card">
                    <div className="gap-card__head">
                      <SeverityBadge severity={gap.severity} compact />
                      <span className="mono">{gap.regulatory_clause}</span>
                    </div>
                    <strong>{gap.framework}</strong>
                    <p className="muted" style={{ marginTop: '0.35rem' }}>{gap.description}</p>
                    <p style={{ marginTop: '0.5rem', fontSize: '0.82rem', color: 'var(--accent)' }}>{gap.recommendation}</p>
                  </article>
                ))
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
