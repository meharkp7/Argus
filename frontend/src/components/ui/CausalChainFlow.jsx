export default function CausalChainFlow({ chain = [] }) {
  if (!chain.length) return null;

  return (
    <div className="causal-flow">
      {chain.map((link, index) => (
        <div key={link.node_id} className="causal-flow__segment">
          <div className="causal-flow__node">
            <span className="causal-flow__step">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <strong>{link.label}</strong>
              <p>{link.description}</p>
            </div>
            {link.weight != null && (
              <span className="causal-flow__weight">w={link.weight.toFixed(2)}</span>
            )}
          </div>
          {index < chain.length - 1 && <div className="causal-flow__connector" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}
