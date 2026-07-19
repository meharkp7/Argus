import { useState, useEffect } from 'react';
import { api } from '../api/client';

const PERMIT_TYPES = ['hot_work', 'confined_space', 'lifting', 'electrical', 'excavation'];
const ZONES = ['zone_a_crude', 'zone_b_tank_farm', 'zone_c_reformer', 'zone_d_utilities'];

export default function PermitDesk() {
  const [permits, setPermits] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    permit_type: 'hot_work',
    zone_id: 'zone_b_tank_farm',
    start_time: new Date(Date.now() + 3600000).toISOString().slice(0, 16),
    end_time: new Date(Date.now() + 7200000).toISOString().slice(0, 16),
    description: '',
    requester: 'shift-supervisor-01',
    latitude: 17.6869,
    longitude: 83.2185,
  });

  useEffect(() => {
    api.getPermits().then(setPermits).catch(console.error);
  }, [result]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
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
    } catch (err) {
      console.error('Permit submission failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h2>Permit Desk</h2>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {permits.length} active permits in simulation
        </span>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">New Permit Request</span>
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
                <option key={z} value={z}>{z.replace(/_/g, ' ')}</option>
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
            <label>Description</label>
            <textarea rows={3} value={form.description} onChange={(e) => handleChange('description', e.target.value)} placeholder="Describe the work scope..." />
          </div>
          <div className="form-group">
            <label>Requester</label>
            <input value={form.requester} onChange={(e) => handleChange('requester', e.target.value)} />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button className="btn btn-primary" onClick={handlePreMortem} disabled={loading}>
              Run Pre-Mortem
            </button>
            <button className="btn" onClick={handleSubmit} disabled={loading}>
              Submit Permit
            </button>
          </div>
        </div>

        <div>
          {result && (
            <div className="card" style={{ marginBottom: '1.25rem' }}>
              <div className="card-header">
                <span className="card-title">Pre-Mortem Result</span>
                <span style={{ color: result.approved_recommendation ? 'var(--low)' : 'var(--critical)' }}>
                  {result.approved_recommendation ? 'APPROVED' : 'REJECTED'}
                </span>
              </div>
              <p style={{ fontSize: '0.875rem', marginBottom: '0.75rem' }}>{result.reasoning}</p>
              <div className="grid-3" style={{ marginBottom: '0.75rem' }}>
                <div>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Risk Score</p>
                  <p style={{ fontWeight: 700 }}>{(result.risk_score * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Confidence</p>
                  <p style={{ fontWeight: 700 }}>{(result.confidence * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Violations</p>
                  <p style={{ fontWeight: 700, color: result.violations?.length ? 'var(--critical)' : 'var(--low)' }}>
                    {result.violations?.length || 0}
                  </p>
                </div>
              </div>
              {result.violations?.map((v, i) => (
                <p key={i} style={{ fontSize: '0.8rem', color: 'var(--critical)' }}>✕ {v}</p>
              ))}
              {result.warnings?.map((w, i) => (
                <p key={i} style={{ fontSize: '0.8rem', color: 'var(--high)' }}>⚠ {w}</p>
              ))}
              {result.regulatory_citations?.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>REGULATORY CITATIONS</p>
                  {result.regulatory_citations.map((c, i) => (
                    <p key={i} style={{ fontSize: '0.75rem' }}>{c}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="card">
            <div className="card-header">
              <span className="card-title">Active Permits</span>
            </div>
            {permits.length === 0 ? (
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>No active permits</p>
            ) : (
              permits.map((p) => (
                <div key={p.permit_id} className="alert-card" style={{ cursor: 'default' }}>
                  <strong>{p.permit_id}</strong>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    {p.permit_type} · {p.zone_id} · {p.status}
                  </p>
                  <p style={{ fontSize: '0.85rem', marginTop: '0.35rem' }}>{p.description}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
}
