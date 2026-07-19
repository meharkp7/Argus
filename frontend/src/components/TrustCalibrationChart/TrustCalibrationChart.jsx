import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { api } from '../../api/client';
import { formatPercent } from '../../utils/format';

export default function TrustCalibrationChart({ metrics: externalMetrics }) {
  const [metrics, setMetrics] = useState(externalMetrics ?? null);
  const [thresholds, setThresholds] = useState(null);

  useEffect(() => {
    if (externalMetrics) setMetrics(externalMetrics);
  }, [externalMetrics]);

  useEffect(() => {
    const fetchThresholds = async () => {
      try {
        const t = await api.getThresholds();
        setThresholds(t);
        if (!externalMetrics) {
          const m = await api.getTrustMetrics();
          setMetrics(m);
        }
      } catch (err) {
        console.error('Trust metrics fetch failed:', err);
      }
    };
    fetchThresholds();
    if (externalMetrics) return undefined;
    const interval = setInterval(async () => {
      try {
        setMetrics(await api.getTrustMetrics());
      } catch (err) {
        console.error(err);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [externalMetrics]);

  if (!metrics) {
    return (
      <div className="card card--glass">
        <div className="skeleton-block">Loading trust calibration…</div>
      </div>
    );
  }

  const chartData = metrics.history.length > 0
    ? metrics.history
    : [{ feedback_number: 0, false_positive_rate: metrics.false_positive_rate }];

  return (
    <div className="card card--glass">
      <div className="card-header">
        <span className="card-title">Trust Calibration</span>
        <span className="pill">{metrics.feedback_count} feedback rounds</span>
      </div>
      <div className="metric-row metric-row--compact">
        <div><span className="label">Alerts</span><strong>{metrics.total_alerts}</strong></div>
        <div><span className="label">False Positives</span><strong>{formatPercent(metrics.false_positive_rate, 1)}</strong></div>
        <div><span className="label">Precision</span><strong className="text-accent">{formatPercent(metrics.precision, 1)}</strong></div>
      </div>
      {thresholds && (
        <p className="muted chart-caption">
          Thresholds · compound ≥ {formatPercent(thresholds.compound_risk_threshold, 0)} · z-score ≥ {thresholds.sensor_zscore_threshold}
        </p>
      )}
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,0.12)" vertical={false} />
          <XAxis dataKey="feedback_number" stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid rgba(148,163,184,0.18)', borderRadius: 12, fontSize: 12 }}
            formatter={(value) => [formatPercent(value, 1), 'False positive rate']}
          />
          <ReferenceLine y={0.3} stroke="#f97316" strokeDasharray="6 4" label={{ value: 'Target ceiling', fill: '#f97316', fontSize: 10 }} />
          <Line type="monotone" dataKey="false_positive_rate" stroke="#38bdf8" strokeWidth={2.5} dot={{ fill: '#38bdf8', r: 3 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
