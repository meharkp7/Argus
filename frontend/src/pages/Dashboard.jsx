import { useState, useEffect, useCallback } from 'react';
import AlertFeed from '../components/AlertFeed/AlertFeed';
import GeospatialHeatmap from '../components/GeospatialHeatmap/GeospatialHeatmap';
import TrustCalibrationChart from '../components/TrustCalibrationChart/TrustCalibrationChart';
import { api } from '../api/client';

export default function Dashboard() {
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [simState, setSimState] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [emergencyResult, setEmergencyResult] = useState(null);
  const [health, setHealth] = useState(null);

  const refreshSim = useCallback(async () => {
    try {
      const state = await api.getSimulationState();
      setSimState(state);
    } catch (err) {
      console.error('Simulation state fetch failed:', err);
    }
  }, []);

  useEffect(() => {
    api.health().then(setHealth).catch(console.error);
    refreshSim();
    const interval = setInterval(refreshSim, 2000);
    return () => clearInterval(interval);
  }, [refreshSim]);

  const handleSimControl = async (action) => {
    try {
      const state = await api.controlSimulation(action);
      setSimState(state);
    } catch (err) {
      console.error('Simulation control failed:', err);
    }
  };

  const handleInvestigate = async () => {
    if (!selectedAlert) return;
    try {
      const result = await api.investigateAlert(selectedAlert.alert_id);
      setInvestigation(result);
    } catch (err) {
      console.error('Investigation failed:', err);
    }
  };

  const handleEmergency = async () => {
    if (!selectedAlert) return;
    if (!window.confirm('Confirm emergency response activation?')) return;
    try {
      const result = await api.triggerEmergency(selectedAlert.alert_id, true);
      setEmergencyResult(result);
    } catch (err) {
      console.error('Emergency response failed:', err);
    }
  };

  const progress = simState
    ? (simState.current_tick / Math.max(simState.total_ticks, 1)) * 100
    : 0;

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Operations Center</h2>
          {simState && (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Scenario: {simState.scenario_id} · Tick {simState.current_tick}/{simState.total_ticks}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {health && (
            <span className="status-badge live">
              <span className="status-dot" />
              {health.components?.simulation === 'running' ? 'Live Simulation' : 'Simulation Stopped'}
            </span>
          )}
          <div className="sim-controls">
            <button className="btn btn-sm" onClick={() => handleSimControl('start')}>Start</button>
            <button className="btn btn-sm" onClick={() => handleSimControl('stop')}>Stop</button>
            <button className="btn btn-sm" onClick={() => handleSimControl('step')}>Step</button>
            <button className="btn btn-sm" onClick={() => handleSimControl('reset')}>Reset</button>
            <div className="sim-progress">
              <div className="sim-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        <GeospatialHeatmap
          onZoneSelect={(zone) => setSelectedZone(zone.zone_id)}
          selectedZone={selectedZone}
        />
        <div>
          <AlertFeed
            onSelectAlert={(alert) => {
              setSelectedAlert(alert);
              setInvestigation(null);
              setEmergencyResult(null);
            }}
            selectedAlertId={selectedAlert?.alert_id}
          />
          {selectedAlert && (
            <div className="card" style={{ marginTop: '1.25rem' }}>
              <div className="card-header">
                <span className="card-title">Alert Detail</span>
                <span className={`severity-${selectedAlert.severity}`}>
                  {selectedAlert.severity.toUpperCase()}
                </span>
              </div>
              <p style={{ fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                {selectedAlert.explanation}
              </p>
              {selectedAlert.causal_chain?.length > 0 && (
                <div className="causal-chain">
                  {selectedAlert.causal_chain.map((link, i) => (
                    <span key={link.node_id}>
                      {i > 0 && <span className="causal-arrow"> → </span>}
                      <span className="causal-node" title={link.description}>
                        {link.label}
                      </span>
                    </span>
                  ))}
                </div>
              )}
              {selectedAlert.recommended_actions?.length > 0 && (
                <ul style={{ fontSize: '0.8rem', marginTop: '0.75rem', paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                  {selectedAlert.recommended_actions.map((action, i) => (
                    <li key={i}>{action}</li>
                  ))}
                </ul>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                <button className="btn btn-primary btn-sm" onClick={handleInvestigate}>
                  Investigate (RAG)
                </button>
                <button className="btn btn-danger btn-sm" onClick={handleEmergency}>
                  Emergency Response
                </button>
              </div>
              {investigation && (
                <div className="explanation-box">
                  <strong style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>RAG Investigation</strong>
                  <p style={{ marginTop: '0.5rem' }}>{investigation.answer}</p>
                  {investigation.citations?.map((c) => (
                    <p key={c.document_id} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                      [{c.source}] {c.title}: {c.excerpt?.substring(0, 120)}...
                    </p>
                  ))}
                </div>
              )}
              {emergencyResult && (
                <div className="explanation-box">
                  <strong style={{ fontSize: '0.75rem', color: 'var(--critical)' }}>Emergency Response Activated</strong>
                  <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                    {emergencyResult.actions?.length} actions executed · Evidence preserved
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <TrustCalibrationChart />
    </>
  );
}
