import { useEffect } from 'react';

export default function Modal({ open, title, description, confirmLabel, cancelLabel = 'Cancel', tone = 'danger', onConfirm, onCancel, children }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onCancel?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onCancel} role="presentation">
      <div className="modal-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal-panel__header">
          <h3 id="modal-title">{title}</h3>
          {description && <p>{description}</p>}
        </div>
        {children}
        <div className="modal-panel__actions">
          <button type="button" className="btn" onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className={`btn btn-${tone}`} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
