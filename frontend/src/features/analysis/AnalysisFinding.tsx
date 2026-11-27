import { CodeBlock, EvidenceViewer, FindingCard } from '@nextgenai/ui';
import type { Finding } from '../../types/report';

export function AnalysisFinding({ finding, compact = false }: { finding: Finding; compact?: boolean }) {
  const { start, end } = finding.location;
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
    <CodeBlock label="Instrucción detectada" className="instruction"
      value={`${String(start.line).padStart(4, '0')} │ ${finding.instruction}`} />
    <EvidenceViewer label={finding.evidence.truncated ? 'EVIDENCIA COMPARTIBLE · TRUNCADA' : 'EVIDENCIA COMPARTIBLE'}
      value={finding.evidence.shared} format="code" expandable />
    {compact ? <details className="detail ngi-disclosure"><summary>Análisis técnico y limitaciones</summary>{details}</details> : details}
    {compact && <EvidenceViewer label="RECOMENDACIÓN" value={finding.recommendation} />}
    <footer>ESTADO: {finding.status} · {finding.confidence_reason}</footer>
  </FindingCard>;
}
