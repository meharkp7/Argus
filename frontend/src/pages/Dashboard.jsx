import { useState } from 'react';
import StatTile from '../components/ui/StatTile';
import { api } from '../api/client';

const SAMPLE_READINGS = '[{"value": 45.2, "timestamp": "2026-07-21T10:00:00"}]';
const SCENARIOS = [
  'Hot work detected with H2S spike',
  'Multiple sensor anomalies + permit mismatch',
  'Shift changeover + maintenance + weather event',
];

function ResultPanel({ title, result }) {
  return (
    <div className="card card--glass">
      <div className="card-header">
        <span className="card-title">{title}</span>
      </div>
      <div className="inspector__body" style={{ whiteSpace: 'pre-wrap' }}>
        {result || 'Run the agent to see ARGUS output here.'}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [initResult, setInitResult] = useState('');
  const [sensorResult, setSensorResult] = useState('');
  const [correlationResult, setCorrelationResult] = useState('');
  const [orchestratorResult, setOrchestratorResult] = useState('');
  const [busy, setBusy] = useState('');
  const [sensorForm, setSensorForm] = useState({
    zoneId: 'Zone-A1',
    sensorType: 'H2S',
    readingsJson: SAMPLE_READINGS,
  });
  const [correlationForm, setCorrelationForm] = useState({
    event1: 'hot work permit submitted',
    event2: 'high H2S readings',
    event3: 'maintenance in progress',
  });
  const [scenario, setScenario] = useState(SCENARIOS[0]);

  const run = async (key, fn, setter) => {
    setBusy(key);
    try {
      setter(await fn());
    } catch (error) {
      setter(`Request failed: ${error.message}`);
    } finally {
      setBusy('');
    }
  };

  return (
    <>
      <section className="kpi-grid">
        <StatTile label="Space Runtime" value="Connected" subtext="Gradio Space API" tone="success" />
        <StatTile label="Operations Surface" value="3 agents" subtext="Initialize · sensor · correlation · orchestrator" tone="accent" />
        <StatTile label="Primary Host" value="HF Space" subtext="mk1647/argus" tone="neutral" />
        <StatTile label="Execution Path" value="/gradio_api" subtext="Queue-backed inference" tone="neutral" mono />
      </section>

      <div className="grid-2">
        <div className="stack">
          <div className="card card--glass">
            <div className="card-header">
              <span className="card-title">Initialize System</span>
            </div>
            <p className="muted">Boot the ARGUS simulation engine, corpus indexing, and orchestration stack inside the Hugging Face Space.</p>
            <div className="action-row">
              <button type="button" className="btn btn-primary" onClick={() => run('init', () => api.initialize(), setInitResult)} disabled={busy === 'init'}>
                {busy === 'init' ? 'Initializing…' : 'Initialize ARGUS'}
              </button>
            </div>
          </div>

          <div className="card card--glass">
            <div className="card-header">
              <span className="card-title">Sensor Agent</span>
            </div>
            <div className="form-group">
              <label>Zone ID</label>
              <input value={sensorForm.zoneId} onChange={(e) => setSensorForm((prev) => ({ ...prev, zoneId: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Sensor Type</label>
              <select value={sensorForm.sensorType} onChange={(e) => setSensorForm((prev) => ({ ...prev, sensorType: e.target.value }))}>
                {['Temperature', 'Pressure', 'H2S', 'Flame', 'Vibration'].map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Recent Readings JSON</label>
              <textarea rows={4} value={sensorForm.readingsJson} onChange={(e) => setSensorForm((prev) => ({ ...prev, readingsJson: e.target.value }))} />
            </div>
            <div className="action-row">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => run('sensor', () => api.sensorAgent(sensorForm), setSensorResult)}
                disabled={busy === 'sensor'}
              >
                {busy === 'sensor' ? 'Running…' : 'Run Sensor Agent'}
              </button>
            </div>
          </div>

          <div className="card card--glass">
            <div className="card-header">
              <span className="card-title">Correlation Agent</span>
            </div>
            <div className="form-group">
              <label>Event 1</label>
              <input value={correlationForm.event1} onChange={(e) => setCorrelationForm((prev) => ({ ...prev, event1: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Event 2</label>
              <input value={correlationForm.event2} onChange={(e) => setCorrelationForm((prev) => ({ ...prev, event2: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Event 3</label>
              <input value={correlationForm.event3} onChange={(e) => setCorrelationForm((prev) => ({ ...prev, event3: e.target.value }))} />
            </div>
            <div className="action-row">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => run('correlation', () => api.correlationAgent(correlationForm), setCorrelationResult)}
                disabled={busy === 'correlation'}
              >
                {busy === 'correlation' ? 'Analyzing…' : 'Detect Correlations'}
              </button>
            </div>
          </div>

          <div className="card card--glass">
            <div className="card-header">
              <span className="card-title">Orchestrator</span>
            </div>
            <div className="form-group">
              <label>Scenario</label>
              <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                {SCENARIOS.map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
            <div className="action-row">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => run('orchestrator', () => api.orchestrator({ scenario }), setOrchestratorResult)}
                disabled={busy === 'orchestrator'}
              >
                {busy === 'orchestrator' ? 'Handling…' : 'Handle Incident'}
              </button>
            </div>
          </div>
        </div>

        <div className="stack">
          <ResultPanel title="Initialization Output" result={initResult} />
          <ResultPanel title="Sensor Agent Output" result={sensorResult} />
          <ResultPanel title="Correlation Agent Output" result={correlationResult} />
          <ResultPanel title="Orchestrator Output" result={orchestratorResult} />
        </div>
      </div>
    </>
  );
}
