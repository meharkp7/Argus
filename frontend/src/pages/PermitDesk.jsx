import { useState } from 'react';
import StatTile from '../components/ui/StatTile';
import { api } from '../api/client';

function ResultPanel({ result }) {
  return (
    <div className="card card--glass">
      <div className="card-header">
        <span className="card-title">Permit Agent Response</span>
      </div>
      <div className="inspector__body" style={{ whiteSpace: 'pre-wrap' }}>
        {result || 'Validate a permit to see ARGUS compliance and conditions here.'}
      </div>
    </div>
  );
}

export default function PermitDesk() {
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    workType: 'hot_work',
    zoneId: 'Zone-B3',
    durationHours: 2,
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      setResult(await api.permitAgent(form));
    } catch (error) {
      setResult(`Request failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <section className="kpi-grid">
        <StatTile label="Permit Surface" value="Live" subtext="HF Permit Agent" tone="success" />
        <StatTile label="Supported Work Types" value="4" subtext="hot work · electrical · confined space · excavation" tone="accent" />
        <StatTile label="Validation Mode" value="Regulatory" subtext="OISD · Factory Act · DGMS" tone="neutral" />
        <StatTile label="Response Format" value="Markdown" subtext="Operator-readable summary" tone="neutral" />
      </section>

      <div className="grid-2">
        <div className="card card--glass">
          <div className="card-header">
            <span className="card-title">Permit Validation</span>
          </div>
          <div className="form-group">
            <label>Work Type</label>
            <select value={form.workType} onChange={(e) => setForm((prev) => ({ ...prev, workType: e.target.value }))}>
              {['hot_work', 'electrical', 'confined_space', 'excavation'].map((type) => (
                <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Zone ID</label>
            <input value={form.zoneId} onChange={(e) => setForm((prev) => ({ ...prev, zoneId: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Duration (hours)</label>
            <input
              type="number"
              min="0.5"
              max="12"
              step="0.5"
              value={form.durationHours}
              onChange={(e) => setForm((prev) => ({ ...prev, durationHours: Number(e.target.value) }))}
            />
          </div>
          <div className="action-row">
            <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
              {loading ? 'Validating…' : 'Validate Permit'}
            </button>
          </div>
        </div>

        <ResultPanel result={result} />
      </div>
    </>
  );
}
