import { useState, useEffect, useCallback, useMemo } from 'react';
import AlertFeed from '../components/AlertFeed/AlertFeed';
import GeospatialHeatmap from '../components/GeospatialHeatmap/GeospatialHeatmap';
import TrustCalibrationChart from '../components/TrustCalibrationChart/TrustCalibrationChart';
import StatTile from '../components/ui/StatTile';
import SeverityBadge from '../components/ui/SeverityBadge';
import CausalChainFlow from '../components/ui/CausalChainFlow';
import EvidenceLedgerPanel from '../components/ui/EvidenceLedgerPanel';
import Modal from '../components/ui/Modal';
import { api } from '../api/client';
import { formatPercent, formatTime, formatZone } from '../utils/format';

const INSPECTOR_TABS = ['overview', 'causal', 'actions', 'investigation'];

export default function Dashboard({ health }) {
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [simState, setSimState] = useState(null);
  const [investigation, setInvestigation] = useState(null);
  const [emergencyResult, setEmergencyResult] = useState(null);
  const [inspectorTab, setInspectorTab] = useState('overview');
  const [investigating, setInvestigating] = useState(false);
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);
  const [simBusy, setSimBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const alertData = await api.getAlerts().catch((error) => ({ error }));
      const heatmapData = await api.getHeatmap().catch((error) => ({ error }));
      const metricData = await api.getTrustMetrics().catch((error) => ({ error }));
      const state = await api.getSimulationState().catch((error) => ({ error }));

      if (!alertData.error) setAlerts(alertData);
      if (!heatmapData.error) setHeatmap(heatmapData);
      if (!metricData.error) setMetrics(metricData);
      if (!state.error) setSimState(state);
    } catch (err) {
      console.error('Dashboard refresh failed:', err);
    } finally {
      setRefreshing(false);
    }
  }, [refreshing]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  const criticalZones = useMemo(
    () => heatmap?.zones?.filter((z) => ['critical', 'high'].includes(z.risk_level)).length ?? 0,
    [heatmap],
  );

  const handleSimControl = async (action) => {
    setSimBusy(true);
    try {
      const state = await api.controlSimulation(action);
      setSimState(state);
      await refresh();
    } catch (err) {
      console.error('Simulation control failed:', err);
    } finally {
      setSimBusy(false);
    }
  };

  const handleInvestigate = async () => {
    if (!selectedAlert) return;
    setInvestigating(true);
    setInspectorTab('investigation');
    try {
      const result = await api.investigateAlert(selectedAlert.alert_id);
      setInvestigation(result);
    } catch (err) {
      console.error('Investigation failed:', err);
    } finally {
      setInvestigating(false);
    }
  };

  const handleEmergency = async () => {
    if (!selectedAlert) return;
    try {
      const result = await api.triggerEmergency(selectedAlert.alert_id, true);
      setEmergencyResult(result);
      setInspectorTab('actions');
      setShowEmergencyModal(false);
    } catch (err) {
      console.error('Emergency response failed:', err);
    }
  };

  const progress = simState
    ? (simState.current_tick / Math.max(simState.total_ticks, 1)) * 100
    : 0;

  return (
    <>
      <section className="kpi-grid">
        <StatTile
          label="Active Compound Alerts"
          value={alerts.length}
          subtext={alerts[0] ? `Latest ${formatTime(alerts[alerts.length - 1]?.timestamp)}` : 'Scenario warming up'}
          tone={alerts.length ? 'danger' : 'neutral'}
        />
        <StatTile
          label="Elevated Zones"
          value={criticalZones}
          subtext={`${heatmap?.zones?.length ?? 0} monitored sectors`}
          tone={criticalZones ? 'warn' : 'success'}
        />
        <StatTile
          label="Operator Precision"
          value={formatPercent(metrics?.precision ?? 0, 1)}
          subtext={`FP rate ${formatPercent(metrics?.false_positive_rate ?? 0, 1)}`}
          tone="accent"
        />
        <StatTile
          label="Evidence Ledger"
          value={health?.components?.evidence_ledger === 'valid' ? 'Verified' : 'Check'}
          subtext={`Simulation ${health?.components?.simulation ?? '—'}`}
          tone={health?.components?.evidence_ledger === 'valid' ? 'success' : 'warn'}
          mono
        />
      </section>

      <section className="sim-bar card card--glass">
        <div>
          <span className="card-title">Scenario Engine</span>
          <p className="sim-bar__title">{simState?.scenario_id ?? 'compound_risk_scenario'}</p>
          <p className="muted">Tick {simState?.current_tick ?? 0} / {simState?.total_ticks ?? 0} · Elapsed {simState?.elapsed_seconds?.toFixed(0) ?? 0}s</p>
        </div>
        <div className="sim-bar__controls">
          <button type="button" className="btn btn-sm" disabled={simBusy} onClick={() => handleSimControl('start')}>Start</button>
          <button type="button" className="btn btn-sm" disabled={simBusy} onClick={() => handleSimControl('stop')}>Pause</button>
          <button type="button" className="btn btn-sm" disabled={simBusy} onClick={() => handleSimControl('step')}>Advance Tick</button>
          <button type="button" className="btn btn-sm" disabled={simBusy} onClick={() => handleSimControl('reset')}>Reset</button>
        </div>
        <div className="sim-bar__progress">
          <div className="sim-progress"><div className="sim-progress-fill" style={{ width: `${progress}%` }} /></div>
          <span className="mono">{progress.toFixed(0)}%</span>
        </div>
      </section>

      <div className="dashboard-grid">
        <GeospatialHeatmap
          heatmap={heatmap}
          refreshing={refreshing}
          onZoneSelect={(zone) => {
            setSelectedZone(zone.zone_id);
            const zoneAlert = alerts.find((a) => a.zone_id === zone.zone_id);
            if (zoneAlert) setSelectedAlert(zoneAlert);
          }}
          selectedZone={selectedZone}
        />

        <div className="stack">
          <AlertFeed
            alerts={alerts}
            onSelectAlert={(alert) => {
              setSelectedAlert(alert);
              setInvestigation(null);
              setEmergencyResult(null);
              setInspectorTab('overview');
            }}
            selectedAlertId={selectedAlert?.alert_id}
          />

          <div className="card card--glass inspector">
            {!selectedAlert ? (
              <div className="empty-state">
                <span className="empty-state__eyebrow">Alert Inspector</span>
                <h3>Select a compound alert</h3>
                <p>Review causal propagation, recommended mitigations, and launch RAG-backed investigations from the feed or map.</p>
              </div>
            ) : (
              <>
                <div className="inspector__header">
                  <div>
                    <span className="mono inspector__id">{selectedAlert.alert_id}</span>
                    <h3>{formatZone(selectedAlert.zone_id)}</h3>
                    <p className="muted">{selectedAlert.hazard_pattern_id.replace(/_/g, ' ')} · {formatTime(selectedAlert.timestamp)}</p>
                  </div>
                  <SeverityBadge severity={selectedAlert.severity} />
                </div>

                <div className="tab-row">
                  {INSPECTOR_TABS.map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      className={`tab-btn ${inspectorTab === tab ? 'active' : ''}`}
                      onClick={() => setInspectorTab(tab)}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {inspectorTab === 'overview' && (
                  <div className="inspector__body">
                    <p>{selectedAlert.explanation}</p>
                    <div className="metric-row">
                      <div><span className="label">Confidence</span><strong>{formatPercent(selectedAlert.confidence, 0)}</strong></div>
                      <div><span className="label">Band</span><strong>{selectedAlert.confidence_band}</strong></div>
                      <div><span className="label">Lead Time</span><strong>{selectedAlert.lead_time_minutes ? `${selectedAlert.lead_time_minutes} min` : '—'}</strong></div>
                      <div><span className="label">Baseline</span><strong>{selectedAlert.baseline_would_trigger ? 'Would trigger' : 'Early detection'}</strong></div>
                    </div>
                    {!selectedAlert.baseline_would_trigger && (
                      <div className="callout callout--accent">Detected before single-sensor baseline thresholds would have fired.</div>
                    )}
                  </div>
                )}

                {inspectorTab === 'causal' && (
                  <div className="inspector__body">
                    <CausalChainFlow chain={selectedAlert.causal_chain} />
                  </div>
                )}

                {inspectorTab === 'actions' && (
                  <div className="inspector__body">
                    <ul className="action-list">
                      {selectedAlert.recommended_actions?.map((action) => (
                        <li key={action}>{action}</li>
                      ))}
                    </ul>
                    {emergencyResult && (
                      <div className="callout callout--danger">
                        Emergency playbook executed · {emergencyResult.actions?.length} actions · evidence bundle preserved.
                      </div>
                    )}
                    <div className="inspector__actions">
                      <button type="button" className="btn btn-primary btn-sm" onClick={handleInvestigate} disabled={investigating}>
                        {investigating ? 'Investigating…' : 'Run RAG Investigation'}
                      </button>
                      <button type="button" className="btn btn-danger btn-sm" onClick={() => setShowEmergencyModal(true)}>
                        Trigger Emergency Response
                      </button>
                    </div>
                  </div>
                )}

                {inspectorTab === 'investigation' && (
                  <div className="inspector__body">
                    {!investigation && !investigating && (
                      <p className="muted">No investigation yet. Use the actions tab or run one directly.</p>
                    )}
                    {investigating && <div className="skeleton-block">Retrieving regulatory corpus and incident precedents…</div>}
                    {investigation && (
                      <>
                        <p>{investigation.answer}</p>
                        <div className="citation-list">
                          {investigation.citations?.map((citation) => (
                            <article key={citation.document_id} className="citation-card">
                              <div className="citation-card__head">
                                <strong>{citation.title}</strong>
                                <span>{formatPercent(citation.relevance_score, 0)} match</span>
                              </div>
                              <p>{citation.excerpt}</p>
                              <span className="mono">{citation.source}{citation.clause_reference ? ` · ${citation.clause_reference}` : ''}</span>
                            </article>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div className="stack stack--compact">
          <TrustCalibrationChart metrics={metrics} />
          <EvidenceLedgerPanel />
        </div>
      </div>

      <Modal
        open={showEmergencyModal}
        title="Confirm Emergency Response"
        description="This will execute the playbook, preserve evidence to the hash-chained ledger, and generate an incident report draft."
        confirmLabel="Execute Playbook"
        onCancel={() => setShowEmergencyModal(false)}
        onConfirm={handleEmergency}
      />
    </>
  );
}
