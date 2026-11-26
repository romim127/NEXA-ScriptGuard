export const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const;
export type Severity = typeof severities[number];

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`flag sev-${severity.toLowerCase()}`}>
    <span aria-hidden="true">⚠ </span>{severity}
  </span>;
}
