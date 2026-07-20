import { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import PermitDesk from './pages/PermitDesk';
import ComplianceAudit from './pages/ComplianceAudit';
import { IconRadar, IconShield, IconClipboard, IconAudit } from './components/ui/icons';
import { api } from './api/client';

const NAV = [
  { id: 'dashboard', label: 'Operations Center', desc: 'Live risk picture', icon: IconRadar },
  { id: 'permits', label: 'Permit Desk', desc: 'Pre-mortem gate', icon: IconClipboard },
  { id: 'compliance', label: 'Compliance Audit', desc: 'Regulatory gaps', icon: IconAudit },
];

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [health, setHealth] = useState(null);
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    api.health().then(setHealth).catch(console.error);
    const timer = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand__mark"><IconShield size={22} /></div>
          <div>
            <h1>ARGUS</h1>
            <p>Zero-Harm Intelligence Layer</p>
          </div>
        </div>

        <div className="sidebar-highlight">
          <span className="sidebar-highlight__eyebrow">Operations posture</span>
          <strong>Industrial safety command center</strong>
          <p>Monitor live risk, permit exposure, and regulatory posture from one view.</p>
        </div>

        <nav className="sidebar-nav">
          <span className="sidebar-nav__label">Command</span>
          {NAV.map(({ id, label, desc, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`nav-item ${page === id ? 'active' : ''}`}
              onClick={() => setPage(id)}
            >
              <span className="nav-item__icon"><Icon /></span>
              <span className="nav-item__copy">
                <strong>{label}</strong>
                <small>{desc}</small>
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="operator-card">
            <span className="operator-card__label">Active Operator</span>
            <strong>Safety Officer · Shift A</strong>
            <span className="mono">ID safety-officer-01</span>
          </div>
          {health && (
            <div className="system-strip">
              {Object.entries(health.components).map(([key, value]) => (
                <div key={key} className="system-strip__item">
                  <span>{key.replace(/_/g, ' ')}</span>
                  <span className={`pill pill--${value === 'valid' || value === 'operational' || value === 'running' || value === 'loaded' ? 'success' : 'warn'}`}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="topbar__eyebrow">Indian Heavy Industry · Simulated Plant</span>
            <h2>{NAV.find((item) => item.id === page)?.label}</h2>
          </div>
          <div className="topbar__meta">
            <div className="topbar__status">
              <span className="topbar__status-label">Last sync</span>
              <span className="mono">{clock.toLocaleString()}</span>
            </div>
            <span className="pill pill--live"><span className="status-dot" />Live Feed</span>
          </div>
        </header>

        <main className="main-content">
          {page === 'dashboard' && <Dashboard health={health} />}
          {page === 'permits' && <PermitDesk />}
          {page === 'compliance' && <ComplianceAudit />}
        </main>
      </div>
    </div>
  );
}
