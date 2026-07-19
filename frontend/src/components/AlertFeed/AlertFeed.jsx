import { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';

export default function AlertFeed({ onSelectAlert, selectedAlertId }) {
  const [alerts, setAlerts] = useState([]);

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.getAlerts();
      setAlerts(data);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleFeedback = async (alertId, label) => {
    try {
      await api.submitFeedback({
        alert_id: alertId,
        label,
        operator_id: 'safety-officer-01',
      });
      fetchAlerts();
    } catch (err) {
      console.error('Feedback failed:', err);
    }
  };

  if (alerts.length === 0) {
    return (
      <div className="card">
        <div className="card-header">
          <span className="card-title">Compound Risk Alerts</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          Monitoring active — alerts will appear as the scenario unfolds...
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Compound Risk Alerts</span>
        <span className="status-badge live">
          <span className="status-dot" />
          {alerts.length} active
        </span>
      </div>
      {alerts.slice().reverse().map((alert) => (
        <div
          key={alert.alert_id}
          className={`alert-card severity-${alert.severity} ${selectedAlertId === alert.alert_id ? 'selected' : ''}`}
          onClick={() => onSelectAlert(alert)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong className={`severity-${alert.severity}`}>
              {alert.severity.toUpperCase()}
            </strong>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {alert.confidence_band} · {(alert.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p style={{ fontSize: '0.8rem', margin: '0.5rem 0', color: 'var(--text-secondary)' }}>
            {alert.zone_id} · {alert.hazard_pattern_id}
          </p>
          <p style={{ fontSize: '0.85rem' }}>
            {alert.explanation?.substring(0, 200)}
            {alert.explanation?.length > 200 ? '...' : ''}
          </p>
          <div className="confidence-bar">
            <div
              className="confidence-fill"
              style={{
                width: `${alert.confidence * 100}%`,
                background: alert.confidence >= 0.85 ? 'var(--critical)' : alert.confidence >= 0.65 ? 'var(--high)' : 'var(--medium)',
              }}
            />
          </div>
          {!alert.baseline_would_trigger && (
            <p style={{ fontSize: '0.7rem', color: 'var(--accent)', marginTop: '0.5rem' }}>
              ⚡ Detected before single-sensor baseline
            </p>
          )}
          <div className="feedback-buttons" onClick={(e) => e.stopPropagation()}>
            <button className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'useful')}>
              👍 Useful
            </button>
            <button className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'not_useful')}>
              👎 Not Useful
            </button>
            <button className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'false_alarm')}>
              🚫 False Alarm
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
