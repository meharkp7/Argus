import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../../api/client';

export default function TrustCalibrationChart() {
  const [metrics, setMetrics] = useState(null);
  const [thresholds, setThresholds] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [m, t] = await Promise.all([
          api.getTrustMetrics(),
          api.getThresholds(),
        ]);
        setMetrics(m);
        setThresholds(t);
      } catch (err) {
        console.error('Trust metrics fetch failed:', err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return null;

  const chartData = metrics.history.length > 0
    ? metrics.history
    : [{ feedback_number: 0, false_positive_rate: metrics.false_positive_rate }];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">Trust Calibration</span>
      </div>
      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        <div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Total Alerts</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 700 }}>{metrics.total_alerts}</p>
        </div>
        <div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>False Positive Rate</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 700, color: metrics.false_positive_rate > 0.3 ? 'var(--high)' : 'var(--low)' }}>
            {(metrics.false_positive_rate * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Precision</p>
          <p style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent)' }}>
            {(metrics.precision * 100).toFixed(1)}%
          </p>
        </div>
      </div>
      {thresholds && (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          Active thresholds: compound risk ≥ {(thresholds.compound_risk_threshold * 100).toFixed(0)}% ·
          sensor z-score ≥ {thresholds.sensor_zscore_threshold}
        </p>
      )}
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
          <XAxis dataKey="feedback_number" stroke="#8899ae" fontSize={11} label={{ value: 'Feedback Round', position: 'insideBottom', offset: -5, fill: '#8899ae', fontSize: 10 }} />
          <YAxis stroke="#8899ae" fontSize={11} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
          <Tooltip
            contentStyle={{ background: '#1a2332', border: '1px solid #2d3a4f', borderRadius: 8, fontSize: 12 }}
            formatter={(value) => [`${(value * 100).toFixed(1)}%`, 'False Positive Rate']}
          />
          <Line type="monotone" dataKey="false_positive_rate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
      <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.5rem', textAlign: 'center' }}>
        Alert precision improves as operator feedback accumulates
      </p>
    </div>
  );
}
