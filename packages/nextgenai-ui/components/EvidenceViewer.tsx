export function EvidenceViewer({ label, value, expandable = false }: {
  label: string;
  value: string;
  expandable?: boolean;
}) {
  if (expandable) return <details className="detail ngi-disclosure">
    <summary>{label}</summary><p className="ngi-evidence">{value}</p>
  </details>;
  return <div className="detail"><span>{label}</span><p className="ngi-evidence">{value}</p></div>;
}
