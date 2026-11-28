type CodeRange = { start: number; end: number; role: string; label: string };

export function CodeBlock({ label, value, className, highlight, id }: {
  label: string;
  value: string;
  className?: string;
  highlight?: CodeRange;
  id?: string;
}) {
  let content = <>{value}</>;
  if (highlight) {
    const characters = Array.from(value);
    const { start, end, role, label } = highlight;
    if (Number.isInteger(start) && Number.isInteger(end) && start >= 0 && end > start && end <= characters.length) {
      content = <>{characters.slice(0, start).join('')}<mark className={`ngi-code-mark ngi-code-mark--${role}`}
        title={label}>{characters.slice(start, end).join('')}</mark>{characters.slice(end).join('')}</>;
    }
  }
  return <pre className={className ? `ngi-code ${className}` : 'ngi-code'}
    id={id} role="region" aria-label={label} tabIndex={0}>{content}</pre>;
}
