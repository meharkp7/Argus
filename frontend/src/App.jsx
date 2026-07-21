import { useMemo, useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import PermitDesk from './pages/PermitDesk';
import ComplianceAudit from './pages/ComplianceAudit';
import { IconRadar, IconShield, IconClipboard, IconAudit } from './components/ui/icons';
import { api } from './api/client';

const NAV = [
  { id: 'dashboard', label: 'Operations Center', desc: 'Sensor, correlation, orchestrator', icon: IconRadar },
  { id: 'permits', label: 'Permit Agent', desc: 'Regulatory validation', icon: IconClipboard },
  { id: 'compliance', label: 'Explainer Agent', desc: 'Causal reasoning', icon: IconAudit },
];

export default function App() {
  const [page, setPage] = useState('dashboard');
  const [clock, setClock] = useState(new Date());
  const spaceInfo = useMemo(() => api.getSpaceInfo(), []);

  useEffect(() => {
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
          <span className="sidebar-highlight__eyebrow">Hugging Face-connected</span>
          <strong>ARGUS agent console</strong>
          <p>Drive the Gradio Space directly from this React frontend through queue-backed agent calls.</p>
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
            <span className="operator-card__label">Connected Space</span>
            <strong>{spaceInfo.name}</strong>
            <span className="mono">{spaceInfo.spaceUrl.replace('https://', '')}</span>
          </div>
          <div className="system-strip">
            <div className="system-strip__item">
              <span>transport</span>
              <span className="pill pill--success">gradio_api</span>
            </div>
            <div className="system-strip__item">
              <span>runtime</span>
              <span className="pill pill--success">hf space</span>
            </div>
          </div>
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
          {page === 'dashboard' && <Dashboard />}
          {page === 'permits' && <PermitDesk />}
          {page === 'compliance' && <ComplianceAudit />}
        </main>
      </div>
    </div>
  );
}
