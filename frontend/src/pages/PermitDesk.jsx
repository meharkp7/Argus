import { useState, useEffect } from 'react';
import { api } from '../api/client';
import StatTile from '../components/ui/StatTile';
import CausalChainFlow from '../components/ui/CausalChainFlow';
import { formatPercent, formatZone } from '../utils/format';

const PERMIT_TYPES = ['hot_work', 'confined_space', 'lifting', 'electrical', 'excavation'];
const ZONES = ['zone_a_crude', 'zone_b_tank_farm', 'zone_c_reformer', 'zone_d_utilities'];

function riskTone(score) {
  if (score >= 0.75) return 'danger';
  if (score >= 0.5) return 'warn';
  return 'success';
}

export default function PermitDesk() {
  const [permits, setPermits] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    permit_type: 'hot_work',
    zone_id: 'zone_b_tank_farm',
    start_time: new Date(Date.now() + 3600000).toISOString().slice(0, 16),
    end_time: new Date(Date.now() + 7200000).toISOString().slice(0, 16),
    description: 'Welding repair on tank farm manifold flange — night shift crew.',
    requester: 'shift-supervisor-01',
    latitude: 17.6869,
    longitude: 83.2185,
  });

  useEffect(() => {
    api.getPermits().then(setPermits).catch(console.error);
  }, [result]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setStep(1);
  };

  const buildPayload = () => ({
    ...form,
    start_time: new Date(form.start_time).toISOString(),
    end_time: new Date(form.end_time).toISOString(),
  });

  const handlePreMortem = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await api.preMortemPermit(buildPayload());
      setResult(res);
      setStep(2);
    } catch (err) {
      console.error('Pre-mortem failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await api.submitPermit(buildPayload());
      setResult(res);
      setStep(3);
      api.getPermits().then(setPermits).catch(console.error);
    } catch (err) {
      console.error('Permit submission failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const rejectedCount = permits.filter((p) => p.status === 'rejected').length;

  return (
    <>
      <section className="kpi-grid">
        <StatTile label="Active Permits" value={permits.length} subtext="Live in simulation" tone="accent" />
        <StatTile label="Last Pre-Mortem" value={result ? formatPercent(result.risk_score, 0) : '—'} subtext={result ? (result.approved_recommendation ? 'Recommended' : 'Blocked') : 'Run analysis first'} tone={result ? riskTone(result.risk_score) : 'neutral'} />
        <StatTile label="Violations" value={result?.violations?.length ?? 0} subtext={`${result?.warnings?.length ?? 0} warnings`} tone={result?.violations?.length ? 'danger' : 'success'} />
        <StatTile label="Citations" value={result?.regulatory_citations?.length ?? 0} subtext="OISD · DGMS · Factory Act" tone="neutral" />
      </section>

      <div className="grid-2">
        <div className="card card--glass">
          <div className="card-header">
            <span className="card-title">Permit Intake</span>
            <span className="pill">Pre-mortem gated</span>
          </div>

          <div className="workflow-steps">
            <div className={`workflow-step ${step >= 1 ? 'active' : ''}`}><span>Step 1</span><strong>Define scope</strong></div>
            <div className={`workflow-step ${step >= 2 ? 'active' : ''}`}><span>Step 2</span><strong>Simulate risk</strong></div>
            <div className={`workflow-step ${step >= 3 ? 'active' : ''}`}><span>Step 3</span><strong>Issue permit</strong></div>
          </div>

          <div className="form-group">
            <label>Permit Type</label>
            <select value={form.permit_type} onChange={(e) => handleChange('permit_type', e.target.value)}>
              {PERMIT_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Zone</label>
            <select value={form.zone_id} onChange={(e) => handleChange('zone_id', e.target.value)}>
              {ZONES.map((z) => (
                <option key={z} value={z}>{formatZone(z)}</option>
              ))}
            </select>
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Start Time</label>
              <input type="datetime-local" value={form.start_time} onChange={(e) => handleChange('start_time', e.target.value)} />
            </div>
            <div className="form-group">
              <label>End Time</label>
              <input type="datetime-local" value={form.end_time} onChange={(e) => handleChange('end_time', e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label>Work Description</label>
            <textarea rows={4} value={form.description} onChange={(e) => handleChange('description', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Requester</label>
            <input value={form.requester} onChange={(e) => handleChange('requester', e.target.value)} />
          </div>
          <div className="action-row">
            <button type="button" className="btn btn-primary" onClick={handlePreMortem} disabled={loading}>
              {loading ? 'Simulating…' : 'Run Pre-Mortem'}
            </button>
            <button type="button" className="btn" onClick={handleSubmit} disabled={loading || !result?.approved_recommendation}>
              Submit Permit
            </button>
          </div>
        </div>

        <div className="stack">
          {result ? (
            <div className="card card--glass">
              <div className="card-header">
                <span className="card-title">Pre-Mortem Analysis</span>
                <span className={`pill ${result.approved_recommendation ? 'pill--success' : 'pill--danger'}`}>
                  {result.approved_recommendation ? 'Approved' : 'Rejected'}
                </span>
              </div>
              <p>{result.reasoning}</p>
              <div className="risk-meter">
                <div className="metric-row metric-row--compact">
                  <div><span className="label">Risk Score</span><strong>{formatPercent(result.risk_score, 0)}</strong></div>
                  <div><span className="label">Confidence</span><strong>{formatPercent(result.confidence, 0)}</strong></div>
                  <div><span className="label">Rejected (sim)</span><strong>{rejectedCount}</strong></div>
                </div>
                <div className="risk-meter__track">
                  <div
                    className="risk-meter__fill"
                    style={{
                      width: `${result.risk_score * 100}%`,
                      background: result.risk_score >= 0.75 ? 'linear-gradient(90deg,#dc2626,#f87171)' : result.risk_score >= 0.5 ? 'linear-gradient(90deg,#ea580c,#fb923c)' : 'linear-gradient(90deg,#16a34a,#4ade80)',
                    }}
                  />
                </div>
              </div>
              {result.violations?.map((v) => (
                <div key={v} className="callout callout--danger">{v}</div>
              ))}
              {result.warnings?.map((w) => (
                <div key={w} className="callout callout--accent">{w}</div>
              ))}
              {result.causal_factors?.length > 0 && (
                <div style={{ marginTop: '0.5rem' }}>
                  <span className="card-title">Causal Factors</span>
                  <CausalChainFlow chain={result.causal_factors} />
                </div>
              )}
              {result.regulatory_citations?.length > 0 && (
                <div className="citation-list" style={{ marginTop: '0.75rem' }}>
                  {result.regulatory_citations.map((citation) => (
                    <article key={citation} className="citation-card">
                      <span className="mono">{citation}</span>
                    </article>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="card card--glass">
              <div className="empty-state empty-state--compact">
                <span className="empty-state__eyebrow">Pre-Mortem Engine</span>
                <h3>Simulate before issuing</h3>
                <p>ARGUS correlates active permits, sensor anomalies, weather, and shift fatigue before a permit enters the live plant state.</p>
                <div className="hint-list">
                  <span>Live causal reasoning</span>
                  <span>Regulatory guardrails</span>
                  <span>Operator-ready recommendations</span>
                </div>
              </div>
            </div>
          )}

          <div className="card card--glass">
            <div className="card-header">
              <span className="card-title">Active Permit Register</span>
            </div>
            {permits.length === 0 ? (
              <p className="muted">No active permits in the current scenario tick.</p>
            ) : (
              <table className="permit-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Zone</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {permits.map((p) => (
                    <tr key={p.permit_id}>
                      <td className="mono">{p.permit_id}</td>
                      <td>{p.permit_type.replace(/_/g, ' ')}</td>
                      <td>{formatZone(p.zone_id)}</td>
                      <td><span className="pill">{p.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
