import { CodeBlock, EvidenceViewer, FindingCard } from '@nextgenai/ui';
import { useId, useState } from 'react';
import type { Finding } from '../../types/report';
import { evidenceRoles, ImpactPanel, type EvidenceReference } from './ImpactPanel';

export function AnalysisFinding({ finding, compact = false }: { finding: Finding; compact?: boolean }) {
  const { start, end } = finding.location;
  const codeId = useId();
  const [selection, setSelection] = useState<EvidenceReference>();
  const prefix = `${String(start.line).padStart(4, '0')} │ `;
  const highlight = selection?.range && finding.instruction === finding.evidence.shared ? {
    start: selection.range.start + Array.from(prefix).length,
    end: selection.range.end + Array.from(prefix).length,
    role: selection.role,
    label: evidenceRoles[selection.role],
  } : undefined;
  const context = [...finding.context.before, ...finding.context.after].join('\n');
  const details = <>
    <EvidenceViewer label="CONTEXTO" value={context || 'Sin contexto adicional.'} format={context ? 'code' : 'text'} />
    {finding.evidence.correlation.length > 0 &&
      <EvidenceViewer label="CORRELACIÓN" value={JSON.stringify(finding.evidence.correlation, null, 2)} format="code" />}
    <EvidenceViewer label="ANÁLISIS TÉCNICO" value={finding.explanation} />
    {!compact && <EvidenceViewer label="RECOMENDACIÓN" value={finding.recommendation} />}
    <EvidenceViewer label="VERIFICACIONES · NO EJECUTADAS"
      value={finding.verification_commands.join('\n') || 'Sin verificaciones sugeridas.'} />
    {finding.limitations.length > 0 && <EvidenceViewer label="LIMITACIONES" value={finding.limitations.join('\n')} />}
  </>;
  return <FindingCard severity={finding.severity} rule={finding.rule_id} title={finding.title}>
    <div className="metadata">
      Línea {start.line} · Columna {start.column} · Fin {end.line}:{end.column} · Confianza {finding.confidence}
    </div>
    <h3>INSTRUCCIÓN DETECTADA</h3>
    <CodeBlock label="Instrucción detectada" className="instruction" id={codeId}
      value={prefix + finding.instruction} highlight={highlight} />
    <p aria-live="polite">{selection && `${evidenceRoles[selection.role]} · ${selection.location.start.line}:${selection.location.start.column}${selection.limitation ? ` · ${selection.limitation}` : ''}`}</p>
    <EvidenceViewer label={finding.evidence.truncated ? 'EVIDENCIA COMPARTIBLE · TRUNCADA' : 'EVIDENCIA COMPARTIBLE'}
      value={finding.evidence.shared} format="code" expandable />
    <ImpactPanel impact={finding.impact_analysis} onEvidence={reference => {
      setSelection(reference);
      if (reference.range) requestAnimationFrame(() => {
        const code = document.getElementById(codeId);
        code?.focus();
        code?.querySelector('mark')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      });
    }} />
    {compact ? <details className="detail ngi-disclosure"><summary>Análisis técnico y limitaciones</summary>{details}</details> : details}
    {compact && <EvidenceViewer label="RECOMENDACIÓN" value={finding.recommendation} />}
    <footer>ESTADO: {finding.status} · {finding.confidence_reason}</footer>
  </FindingCard>;
}
