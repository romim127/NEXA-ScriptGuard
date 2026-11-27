import { CodeBlock } from './CodeBlock';

export function EvidenceViewer({ label, value, expandable = false, format = 'text' }: {
  label: string;
  value: string;
  expandable?: boolean;
  format?: 'text' | 'code';
}) {
  const content = format === 'code'
    ? <CodeBlock label={label} value={value} />
    : <p className="ngi-evidence">{value}</p>;
  if (expandable) return <details className="detail ngi-disclosure">
    <summary>{label}</summary>{content}
  </details>;
  return <div className="detail"><span>{label}</span>{content}</div>;
}
