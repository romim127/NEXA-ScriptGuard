export function CodeBlock({ label, value, className }: {
  label: string;
  value: string;
  className?: string;
}) {
  return <pre className={className ? `ngi-code ${className}` : 'ngi-code'}
    role="region" aria-label={label} tabIndex={0}>{value}</pre>;
}
