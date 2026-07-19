import { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { IconLink } from './icons';

export default function EvidenceLedgerPanel() {
  const [records, setRecords] = useState([]);
  const [verification, setVerification] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [evidence, verify] = await Promise.all([
          api.getEvidence(8),
          api.verifyEvidence(),
        ]);
        setRecords(evidence);
        setVerification(verify);
      } catch (err) {
        console.error('Evidence fetch failed:', err);
      }
    };
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card card--glass evidence-panel">
      <div className="card-header">
        <span className="card-title">Evidence Ledger</span>
        {verification && (
          <span className={`pill ${verification.chain_valid ? 'pill--success' : 'pill--danger'}`}>
            {verification.chain_valid ? 'Chain Valid' : 'Integrity Warning'}
          </span>
        )}
      </div>
      {verification && (
        <div className="evidence-panel__meta">
          <span><IconLink /> {verification.record_count} records</span>
          <span className="mono truncate">{verification.merkle_root?.slice(0, 18)}…</span>
        </div>
      )}
      <div className="evidence-panel__list">
        {records.length === 0 ? (
          <p className="muted">Awaiting ledger entries from simulation events…</p>
        ) : (
          records.map((record) => (
            <div key={record.record_id} className="evidence-row">
              <div>
                <span className="mono evidence-row__id">{record.record_id}</span>
                <span className="evidence-row__type">{record.record_type.replace(/_/g, ' ')}</span>
              </div>
              <span className="mono evidence-row__hash">{record.payload_hash.slice(0, 10)}…</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
