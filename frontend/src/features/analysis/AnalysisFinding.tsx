import { EvidenceViewer, FindingCard } from '@nextgenai/ui';
import type { Finding } from '../../types/report';

export function AnalysisFinding({ finding }: { finding: Finding }) {
  const { start, end } = finding.location;
  const context = [...finding.context.before, ...finding.context.after].join('\n');
  return <FindingCard severity={finding.severity} rule={finding.rule_id} title={finding.title}>
    <div className="metadata">
      Línea {start.line} · Columna {start.column} · Fin {end.line}:{end.column} · Confianza {finding.confidence}
    </div>
    <h3>INSTRUCCIÓN DETECTADA</h3>
    <pre className="instruction">{String(start.line).padStart(4, '0')} │ {finding.instruction}</pre>
    <EvidenceViewer label={finding.evidence.truncated ? 'EVIDENCIA COMPARTIBLE · TRUNCADA' : 'EVIDENCIA COMPARTIBLE'}
      value={finding.evidence.shared} expandable />
    <EvidenceViewer label="CONTEXTO" value={context || 'Sin contexto adicional.'} />
    {finding.evidence.correlation.length > 0 &&
      <EvidenceViewer label="CORRELACIÓN" value={JSON.stringify(finding.evidence.correlation, null, 2)} />}
    <EvidenceViewer label="ANÁLISIS TÉCNICO" value={finding.explanation} />
    <EvidenceViewer label="RECOMENDACIÓN" value={finding.recommendation} />
    <EvidenceViewer label="VERIFICACIONES · NO EJECUTADAS"
      value={finding.verification_commands.join('\n') || 'Sin verificaciones sugeridas.'} />
    {finding.limitations.length > 0 && <EvidenceViewer label="LIMITACIONES" value={finding.limitations.join('\n')} />}
    <footer>ESTADO: {finding.status} · {finding.confidence_reason}</footer>
  </FindingCard>;
}
