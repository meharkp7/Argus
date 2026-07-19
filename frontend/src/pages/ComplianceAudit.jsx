import { useState } from 'react';
import { api } from '../api/client';

const FRAMEWORKS = ['OISD', 'DGMS', 'Factory Act'];

const SAMPLE_PROCEDURE = `Hot Work Procedure — Tank Farm Zone B

1. Obtain hot work permit from area authority before commencing work.
2. Ensure continuous gas monitoring is active in the work zone.
3. Fire watch personnel must be stationed during all hot work operations.
4. Emergency response plan must be reviewed with crew before start.
5. All personnel must wear appropriate PPE including fire-resistant clothing.`;

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

  return (
    <>
      <div className="page-header">
        <h2>Compliance Audit</h2>
        <button className="btn btn-primary" onClick={handleAudit} disabled={loading || !documentText.trim()}>
          {loading ? 'Auditing...' : 'Run Audit'}
        </button>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Document Under Review</span>
          </div>
          <textarea
            rows={16}
            value={documentText}
            onChange={(e) => setDocumentText(e.target.value)}
            placeholder="Paste safety procedure or permit document text..."
          />
          <div style={{ marginTop: '1rem' }}>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
              Applicable Frameworks
            </p>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {FRAMEWORKS.map((fw) => (
                <button
                  key={fw}
                  className={`feedback-btn ${frameworks.includes(fw) ? 'active-useful' : ''}`}
                  onClick={() => toggleFramework(fw)}
                >
                  {fw}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div>
          {result ? (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Audit Results</span>
                <span style={{
                  fontWeight: 700,
                  color: result.compliance_score >= 0.8 ? 'var(--low)' : result.compliance_score >= 0.5 ? 'var(--medium)' : 'var(--critical)',
                }}>
                  {(result.compliance_score * 100).toFixed(0)}% compliant
                </span>
              </div>
              <p style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>{result.summary}</p>
              {result.gaps.length === 0 ? (
                <p style={{ color: 'var(--low)', fontSize: '0.875rem' }}>No compliance gaps detected.</p>
              ) : (
                result.gaps.map((gap) => (
                  <div key={gap.gap_id} className="alert-card severity-medium" style={{ cursor: 'default' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <strong className={`severity-${gap.severity}`}>{gap.framework}</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{gap.regulatory_clause}</span>
                    </div>
                    <p style={{ fontSize: '0.85rem', margin: '0.5rem 0' }}>{gap.description}</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>{gap.recommendation}</p>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="card" style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                Paste a procedure and run audit against OISD, DGMS, and Factory Act requirements
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
