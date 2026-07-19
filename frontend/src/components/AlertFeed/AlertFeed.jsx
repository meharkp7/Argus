import { useCallback } from 'react';
import { api } from '../../api/client';
import SeverityBadge from '../ui/SeverityBadge';
import { formatPercent, formatTime, formatZone } from '../../utils/format';

export default function AlertFeed({ alerts: externalAlerts, onSelectAlert, selectedAlertId }) {
  const handleFeedback = useCallback(async (alertId, label) => {
    try {
      await api.submitFeedback({
        alert_id: alertId,
        label,
        operator_id: 'safety-officer-01',
      });
    } catch (err) {
      console.error('Feedback failed:', err);
    }
  }, []);

  const alerts = externalAlerts ?? [];

  return (
    <div className="card card--glass alert-feed">
      <div className="card-header">
        <span className="card-title">Compound Risk Alerts</span>
        <span className="pill pill--live"><span className="status-dot" />{alerts.length} tracked</span>
      </div>

      <div className="alert-feed__list">
        {alerts.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <h4>No alerts yet</h4>
            <p>Start or advance the scenario engine. Compound detections surface here before single-sensor baselines trip.</p>
          </div>
        ) : (
          [...alerts].reverse().map((alert) => (
            <button
              key={alert.alert_id}
              type="button"
              className={`alert-card severity-${alert.severity} ${selectedAlertId === alert.alert_id ? 'selected' : ''}`}
              onClick={() => onSelectAlert(alert)}
            >
              <div className="alert-card__head">
                <SeverityBadge severity={alert.severity} compact />
                <span className="mono alert-card__time">{formatTime(alert.timestamp)}</span>
              </div>
              <div className="alert-card__meta">
                <span>{formatZone(alert.zone_id)}</span>
                <span>{alert.hazard_pattern_id.replace(/_/g, ' ')}</span>
              </div>
              <p className="alert-card__copy">{alert.explanation}</p>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{
                    width: `${alert.confidence * 100}%`,
                    background: alert.confidence >= 0.85 ? 'var(--critical)' : alert.confidence >= 0.65 ? 'var(--high)' : 'var(--medium)',
                  }}
                />
              </div>
              <div className="alert-card__footer">
                <span>{alert.confidence_band} · {formatPercent(alert.confidence, 0)}</span>
                {!alert.baseline_would_trigger && <span className="pill pill--accent">Early detection</span>}
              </div>
              <div className="feedback-buttons" onClick={(e) => e.stopPropagation()}>
                <button type="button" className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'useful')}>Useful</button>
                <button type="button" className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'not_useful')}>Not useful</button>
                <button type="button" className="feedback-btn" onClick={() => handleFeedback(alert.alert_id, 'false_alarm')}>False alarm</button>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
