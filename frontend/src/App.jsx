import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import NewAudit from './views/NewAudit.jsx';
import InProgress from './views/InProgress.jsx';
import AllAudits from './views/AllAudits.jsx';
import AuditDetail from './views/AuditDetail.jsx';
import Settings from './views/Settings.jsx';

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <h1>SYNTHETIC-MARKETER</h1>
        <NavLink to="/new" className={({ isActive }) => (isActive ? 'active' : '')}>
          + New audit
        </NavLink>
        <NavLink to="/all" className={({ isActive }) => (isActive ? 'active' : '')}>
          All audits
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? 'active' : '')}>
          Settings
        </NavLink>
        <div style={{ flex: 1 }} />
        <small style={{ opacity: 0.5 }}>v0.1.0 · B4 detail views</small>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/new" replace />} />
          <Route path="/new" element={<NewAudit />} />
          <Route path="/audits/bin/:binName" element={<AuditDetail />} />
          <Route path="/audits/:jobId" element={<InProgress />} />
          <Route path="/all" element={<AllAudits />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
