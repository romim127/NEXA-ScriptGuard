import { CodeBlock, EvidenceViewer, FindingCard } from '@nextgenai/ui';
import { useId, useState } from 'react';
import type { Finding } from '../../types/report';
import { evidenceRoles, ImpactPanel, type EvidenceReference, type EvidenceTarget } from './ImpactPanel';

export function AnalysisFinding({ finding, compact = false }: { finding: Finding; compact?: boolean }) {
  const { start, end } = finding.location;
  const codeId = useId();
  const [selectedId, setSelectedId] = useState<string>();
  const prefix = `${String(start.line).padStart(4, '0')} │ `;
  const evidenceLength = Array.from(finding.instruction).length;
  function evidenceTarget(reference: EvidenceReference): EvidenceTarget {
    const { range } = reference;
    if (range && !finding.evidence.truncated && finding.instruction === finding.evidence.shared &&
        range.start >= 0 && range.start < range.end && range.end <= evidenceLength) return 'exact';
    if (finding.instruction && reference.location.start.line === start.line) return 'line';
    return 'unavailable';
  }
  const selection = finding.impact_analysis?.references.find(reference => reference.id === selectedId);
  const selectedTarget = selection ? evidenceTarget(selection) : 'unavailable';
  const selectedRange = selectedTarget === 'exact' ? selection?.range : null;
  const highlight = selection && selectedRange ? {
    start: selectedRange.start + prefix.length,
    end: selectedRange.end + prefix.length,
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
    <p aria-live="polite">{selection && selectedTarget !== 'unavailable' &&
      `${evidenceRoles[selection.role]} · Línea ${selection.location.start.line}${selectedTarget === 'line' ? ' · Sin rango exacto' : ''}`}</p>
    <EvidenceViewer label={finding.evidence.truncated ? 'EVIDENCIA COMPARTIBLE · TRUNCADA' : 'EVIDENCIA COMPARTIBLE'}
      value={finding.evidence.shared} format="code" expandable />
    <ImpactPanel impact={finding.impact_analysis} omission={finding.impact_omission} evidenceTarget={evidenceTarget}
      onEvidence={reference => {
        const target = evidenceTarget(reference);
        if (target === 'unavailable') return;
        setSelectedId(reference.id);
        requestAnimationFrame(() => {
          const code = document.getElementById(codeId);
          code?.focus({ preventScroll: true });
          code?.scrollIntoView({ block: 'center', inline: 'nearest' });
          if (target === 'line' && code) code.scrollLeft = 0;
          if (target === 'exact') code?.querySelector('mark')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        });
      }} />
    {compact ? <details className="detail ngi-disclosure"><summary>Análisis técnico y limitaciones</summary>{details}</details> : details}
    {compact && <EvidenceViewer label="RECOMENDACIÓN" value={finding.recommendation} />}
    <footer>ESTADO: {finding.status} · {finding.confidence_reason}</footer>
  </FindingCard>;
}
