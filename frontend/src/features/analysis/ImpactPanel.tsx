import type { Impact } from '../../types/impact';
import type { Finding } from '../../types/report';
import './impact.css';

export type EvidenceReference = Impact['references'][number];
export type EvidenceTarget = 'exact' | 'line' | 'unavailable';

export const evidenceRoles = {
  instruction: 'Instrucción',
  source: 'Origen',
  sink: 'Destino sensible',
  propagation: 'Propagación',
  validation: 'Validación identificada',
};

const statuses = {
  potential: 'Potencial',
  conditional: 'Condicional',
  indeterminate: 'Indeterminado',
  not_established: 'No establecido',
  not_evaluated: 'No evaluado',
};
const dimensions = {
  confidentiality: 'Confidencialidad',
  integrity: 'Integridad',
  availability: 'Disponibilidad',
} as const;

const coverageLabels = {
  syntax: 'Cobertura sintáctica',
  correlated: 'Cobertura correlacionada',
  partial: 'Cobertura parcial',
  not_evaluated: 'No evaluado por el motor SITA',
};

function trustBoundary(boundary: Impact['boundaries'][number]) {
  return `${boundary.origin} → ${boundary.destination}`;
}

export function ImpactPanel({ impact, omission, evidenceTarget, onEvidence }: {
  impact?: Impact;
  omission?: Finding['impact_omission'];
  evidenceTarget: (ref: EvidenceReference) => EvidenceTarget;
  onEvidence: (ref: EvidenceReference) => void;
}) {
  const cia = impact ? (Object.keys(dimensions) as Array<keyof typeof dimensions>).map(key =>
    ({ label: dimensions[key], value: impact.cia[key] })) : [];
  const conclusions = [
    ...(impact?.resources.map(resource => ({
      label: `${resource.id} · ${resource.label} · ${resource.scope === 'direct' ? 'Señal directa' : 'Asociación correlacionada'}`,
      value: resource,
    })) ?? []),
    ...(impact?.boundaries.map(boundary => ({ label: `${boundary.id} · ${trustBoundary(boundary)}`, value: boundary })) ?? []),
    ...cia,
  ];
  const groups = new Map<string, typeof conclusions>();
  for (const conclusion of conclusions) {
    const key = JSON.stringify([conclusion.value.justification, conclusion.value.conditions]);
    const group = groups.get(key);
    if (group) group.push(conclusion);
    else groups.set(key, [conclusion]);
  }
  const references = new Map(impact?.references.map((ref, index) => [ref.id, index + 1]));
  const referenceNumbers = (ids: string[]) => ids.map(id => references.get(id)).join(', ');
  const condition = conclusions.flatMap(({ value }) => value.conditions)[0];

  return <section className="sita">
    <h3>IMPACTO EN EL SISTEMA Y LÍMITES DE CONFIANZA</h3>
    <p>System Impact &amp; Trust Analysis — SITA</p>
    <p className="sita-disclaimer">ANÁLISIS ESTÁTICO · SIN EJECUCIÓN · IMPACTO NO OBSERVADO</p>
    <p className="sita-coverage"><strong>{omission ? 'No evaluado por límite de recursos' : impact
      ? coverageLabels[impact.coverage] : 'Análisis de impacto no disponible en este reporte'}</strong>
      {impact && <span>Confianza SITA {impact.confidence === 'medium' ? 'media' : 'baja'}</span>}</p>
    {impact && <>
      {(impact.resources.length > 0 || impact.boundaries.length > 0) && <dl className="sita-surface">
        {impact.resources.length > 0 && <div><dt>Recursos</dt>{impact.resources.map(resource =>
          <dd key={resource.id}>{resource.label} · {resource.operation}</dd>)}</div>}
        {impact.boundaries.length > 0 && <div><dt>Límites de confianza</dt>{impact.boundaries.map(boundary =>
          <dd key={boundary.id}>{trustBoundary(boundary)}</dd>)}</div>}
      </dl>}
      <dl className="sita-cia" aria-label="Dimensiones CIA">{cia.map(({ label, value }) =>
        <div key={label}><dt>{label}</dt><dd>{statuses[value.status]}</dd></div>)}</dl>
      {condition && <p><strong>Condición principal</strong> · {condition}</p>}
      {impact.limitations.length > 0 && <ul className="sita-limitations">
        {impact.limitations.map(message => <li key={message}>{message}</li>)}
      </ul>}
      <details className="ngi-disclosure sita-details">
      <summary>Ver impacto, confianza y evidencia</summary>
      <h4>Justificaciones y condiciones</h4>
      {[...groups.values()].map(group => {
        const { justification, conditions } = group[0].value;
        return <section className="sita-reason" key={JSON.stringify([justification, conditions])}>
          <p>{justification}</p>
          {condition && conditions.includes(condition) && <small>Aplica la condición principal.</small>}
          {conditions.filter(text => text !== condition).map(text => <p key={text}>{text}</p>)}
          <ul>{group.map(({ label, value }) => <li key={label}>
            {label} · {statuses[value.status]}
            {value.evidence.length > 0 && ` · Evidencia ${referenceNumbers(value.evidence)}`}
          </li>)}</ul>
        </section>;
      })}
      {impact.flows.length > 0 && <section>
        <h4>Flujos correlacionados</h4>
        {impact.flows.map(flow => <div key={flow.source}>
          <p>{flow.relationship === 'possible' ? 'Origen → destino posible' : 'Origen → destino indeterminado'}
            {flow.assignment_steps > 0 && ` · Asignaciones registradas: ${flow.assignment_steps}`}</p>
          <p>Evidencia {referenceNumbers([flow.source, flow.sink])}</p>
        </div>)}
      </section>}
      {impact.references.length > 0 && <section>
        <h4>Referencias de evidencia</h4>
        <ol className="sita-references">{impact.references.map(ref => {
          const target = evidenceTarget(ref);
          const { line, column } = ref.location.start;
          const label = `${evidenceRoles[ref.role]} · Línea ${line}, columna ${column}`;
          return <li key={ref.id}>
            {target === 'unavailable' ? <span>{label} · Sin destino verificable en la evidencia visible</span> :
              <button type="button" className="sita-reference" onClick={() => onEvidence(ref)}>
                {label} · {target === 'exact' ? 'Resaltar fragmento' : 'Localizar línea, sin rango exacto'}
              </button>}
            {ref.limitation && <small>{ref.limitation}</small>}
          </li>;
        })}</ol>
        <p>Leyenda: origen, propagación, destino sensible y validación identificada.</p>
      </section>}
      </details>
    </>}
  </section>;
}
