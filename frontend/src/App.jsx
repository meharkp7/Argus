import { useState } from 'react';
import Dashboard from './pages/Dashboard';
import PermitDesk from './pages/PermitDesk';
import ComplianceAudit from './pages/ComplianceAudit';

const PAGES = [
  { id: 'dashboard', label: 'Operations Center', icon: '◉' },
  { id: 'permits', label: 'Permit Desk', icon: '⎔' },
  { id: 'compliance', label: 'Compliance Audit', icon: '☰' },
];

export default function App() {
  const [page, setPage] = useState('dashboard');

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>ARGUS</h1>
          <p>Zero-Harm Intelligence</p>
        </div>
        {PAGES.map(({ id, label, icon }) => (
          <div
            key={id}
            className={`nav-item ${page === id ? 'active' : ''}`}
            onClick={() => setPage(id)}
          >
            <span>{icon}</span>
            {label}
          </div>
        ))}
      </aside>
      <main className="main-content">
        {page === 'dashboard' && <Dashboard />}
        {page === 'permits' && <PermitDesk />}
        {page === 'compliance' && <ComplianceAudit />}
      </main>
    </div>
  );
}
