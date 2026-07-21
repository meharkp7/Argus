import { useState } from 'react';
import StatTile from '../components/ui/StatTile';
import { api } from '../api/client';

const REASONING_TYPES = ['compound_risk', 'permit_violation', 'anomaly_correlation'];

function OutputCard({ title, result }) {
  return (
    <div className="card card--glass">
      <div className="card-header">
        <span className="card-title">{title}</span>
      </div>
      <div className="inspector__body" style={{ whiteSpace: 'pre-wrap' }}>
        {result || 'Run the explainer to retrieve causal reasoning from the Hugging Face Space.'}
      </div>
    </div>
  );
}

export default function ComplianceAudit() {
  const [explainerResult, setExplainerResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    alertId: 'ALERT-2026-07-21-001',
    reasoningType: 'compound_risk',
  });

  const handleExplain = async () => {
    setLoading(true);
    try {
      setExplainerResult(await api.explainerAgent(form));
    } catch (error) {
      setExplainerResult(`Request failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <section className="kpi-grid">
        <StatTile label="Explainer Agent" value="Ready" subtext="HF Space endpoint" tone="success" />
        <StatTile label="Reasoning Modes" value={REASONING_TYPES.length} subtext={REASONING_TYPES.join(' · ')} tone="accent" />
        <StatTile label="Audit Style" value="Causal Chain" subtext="Evidence-backed narrative" tone="neutral" />
        <StatTile label="Alert Input" value="Manual" subtext="Operator-provided alert ID" tone="neutral" />
      </section>

      <div className="grid-2">
        <div className="card card--glass">
          <div className="card-header">
            <span className="card-title">Explainer Agent</span>
          </div>
          <div className="form-group">
            <label>Alert ID</label>
            <input value={form.alertId} onChange={(e) => setForm((prev) => ({ ...prev, alertId: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Reasoning Type</label>
            <select value={form.reasoningType} onChange={(e) => setForm((prev) => ({ ...prev, reasoningType: e.target.value }))}>
              {REASONING_TYPES.map((type) => (
                <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div className="action-row">
            <button type="button" className="btn btn-primary" onClick={handleExplain} disabled={loading}>
              {loading ? 'Generating…' : 'Generate Explanation'}
            </button>
          </div>
        </div>

        <OutputCard title="Explainer Output" result={explainerResult} />
      </div>
    </>
  );
}
