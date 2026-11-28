import type { Impact } from '../../types/impact';
import './impact.css';

export type EvidenceReference = Impact['references'][number];

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

export function ImpactPanel({ impact, onEvidence }: {
  impact?: Impact;
  onEvidence: (ref: EvidenceReference) => void;
}) {
  function links(ids: string[]) {
    return impact?.references.filter(ref => ids.includes(ref.id)).map(ref =>
      <li key={ref.id}>
        <button type="button" className="sita-reference" onClick={() => onEvidence(ref)}>
          {evidenceRoles[ref.role]} · {ref.location.start.line}:{ref.location.start.column}
        </button>
        {ref.limitation && <small>{ref.limitation}</small>}
      </li>);
  }

  function conclusion(value: Impact['cia']['integrity']) {
    return <>
      <p><strong>{statuses[value.status]}</strong> · {value.justification}</p>
      {value.conditions.map(condition => <p key={condition}>{condition}</p>)}
      {value.evidence.length > 0 && <ul>{links(value.evidence)}</ul>}
    </>;
  }

  return <section className="sita">
    <h3>IMPACTO EN EL SISTEMA Y LÍMITES DE CONFIANZA</h3>
    <p>System Impact &amp; Trust Analysis — SITA</p>
    <p><strong>ANÁLISIS ESTÁTICO · SIN EJECUCIÓN · IMPACTO NO OBSERVADO</strong></p>
    {impact ? <details className="ngi-disclosure">
      <summary>Ver impacto, confianza y evidencia</summary>
      <p>Cobertura: {{ syntax: 'Sintáctica', correlated: 'Correlacionada', partial: 'Parcial', not_evaluated: 'No evaluada' }[impact.coverage]}
        {' · '}Confianza SITA: {impact.confidence === 'medium' ? 'Media' : 'Baja'}</p>
      {impact.resources.map(resource => <section key={resource.id}>
        <h4>{resource.id} · {resource.label} · {resource.operation}</h4>
        <p>{resource.scope === 'direct' ? 'Señal directa' : 'Asociación correlacionada'}</p>
        {conclusion(resource)}
      </section>)}
      {impact.boundaries.map(boundary => <section key={boundary.id}>
        <h4>{boundary.id} · {boundary.origin} → {boundary.destination}</h4>
        {conclusion(boundary)}
      </section>)}
      {impact.flows.length > 0 && <section>
        <h4>Flujos correlacionados</h4>
        {impact.flows.map(flow => <div key={flow.source}>
          <p>{flow.relationship === 'possible' ? 'Origen → destino posible' : 'Origen → destino indeterminado'}
            {flow.assignment_steps > 0 && ` · Asignaciones registradas: ${flow.assignment_steps}`}</p>
          <ul>{links([flow.source, flow.sink])}</ul>
        </div>)}
      </section>}
      <h4>Confidencialidad, integridad y disponibilidad</h4>
      {(Object.keys(dimensions) as Array<keyof typeof dimensions>).map(key =>
        <section key={key}><h5>{dimensions[key]}</h5>{conclusion(impact.cia[key])}</section>)}
      <p>Leyenda: origen, propagación, destino sensible y validación identificada.</p>
      <ul>{impact.limitations.map(text => <li key={text}>{text}</li>)}</ul>
    </details> : <p>Análisis de impacto no disponible.</p>}
  </section>;
}
