import { useState } from 'react';
import { severities } from '@nextgenai/ui';
import type { Finding } from '../../types/report';
import { AnalysisFinding } from './AnalysisFinding';

export function FindingExplorer({ findings }: { findings: Finding[] }) {
  const [severity, setSeverity] = useState('');
  const [rule, setRule] = useState('');
  const [search, setSearch] = useState('');
  const [order, setOrder] = useState('report');
  const rules = [...new Set(findings.map(finding => finding.rule_id))].sort();
  const query = search.trim().toLowerCase();
  const visible = findings.filter(finding => {
    if ((severity && finding.severity !== severity) || (rule && finding.rule_id !== rule)) return false;
    return !query || [
      finding.rule_id, finding.title, finding.instruction, finding.evidence.shared,
      finding.explanation, finding.recommendation, String(finding.location.start.line),
    ].some(value => value.toLowerCase().includes(query));
  });
  if (order === 'line') visible.sort((a, b) =>
    a.location.start.line - b.location.start.line || a.location.start.column - b.location.start.column);
  if (order === 'severity') visible.sort((a, b) =>
    severities.indexOf(a.severity) - severities.indexOf(b.severity));

  return <>
    <div className="controls finding-filters" role="group" aria-label="Filtros de hallazgos">
      <label>Buscar hallazgos <input type="search" value={search} onChange={event => setSearch(event.target.value)} /></label>
      <label>Criticidad <select aria-label="Criticidad" value={severity} onChange={event => setSeverity(event.target.value)}>
        <option value="">Todas</option>
        {severities.map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>Regla <select aria-label="Regla" value={rule} onChange={event => setRule(event.target.value)}>
        <option value="">Todas</option>
        {rules.map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>Orden <select aria-label="Orden" value={order} onChange={event => setOrder(event.target.value)}>
        <option value="report">Del reporte</option><option value="severity">Por criticidad</option>
        <option value="line">Por línea</option>
      </select></label>
    </div>
    <p aria-live="polite">Mostrando {visible.length} de {findings.length} hallazgos.</p>
    {visible.length === 0 && <p className="notice">Ningún hallazgo coincide con los filtros.</p>}
    {visible.length > 0 && <details>
      <summary>Ir a una ubicación detectada</summary>
      <ul>{visible.map((finding, index) => <li key={finding.id}>
        <a href={`#finding-${index}`}>Línea {finding.location.start.line}, columna {finding.location.start.column} · {finding.rule_id}</a>
      </li>)}</ul>
    </details>}
    {visible.map((finding, index) => <section id={`finding-${index}`} tabIndex={-1} key={finding.id}>
      <AnalysisFinding finding={finding} />
    </section>)}
  </>;
}
