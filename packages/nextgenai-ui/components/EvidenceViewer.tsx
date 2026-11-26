export function EvidenceViewer({ label, value }: { label: string; value: string }) {
  return <div className="detail"><span>{label}</span><p className="ngi-evidence">{value}</p></div>;
}
