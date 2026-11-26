import type { ReactNode } from 'react';
import { SeverityBadge, type Severity } from './SeverityBadge';

export function FindingCard({ severity, rule, title, children }: {
  severity: Severity;
  rule: string;
  title: string;
  children: ReactNode;
}) {
  return <article className={`finding sev-${severity.toLowerCase()}`}>
    <div className="heading"><SeverityBadge severity={severity} /><span className="rule">{rule}</span></div>
    <h2>{title}</h2>
    {children}
  </article>;
}
