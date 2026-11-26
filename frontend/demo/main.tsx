import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Dashboard, EvidenceViewer, ExportPanel, FindingCard, InfinityShield, Sidebar } from '@nextgenai/ui';
import '@nextgenai/ui/theme.css';
import shield from '../../nexa_scriptguard/gui_assets/infinity-shield.svg?url';
import fixture from './public/reports/synthetic.json';
import htmlReport from './public/reports/synthetic.html?raw';
import sarifReport from './public/reports/synthetic.sarif?raw';
import './demo.css';

const formats = [
  { id: 'json', label: 'Descargar JSON sintético' },
  { id: 'html', label: 'Descargar HTML sintético' },
  { id: 'sarif', label: 'Descargar SARIF sintético' },
] as const;
const reports = {
  json: [JSON.stringify(fixture, null, 2), 'application/json'],
  html: [htmlReport, 'text/html'],
  sarif: [sarifReport, 'application/sarif+json'],
} as const;

function Demo() {
  const [level, setLevel] = useState('');
  const findings = fixture.findings.filter(entry => !level || entry.severity === level);
  return <>
    <p className="demo-banner" role="note">DEMO MODE — SYNTHETIC DATA</p>
    <Dashboard header={<>
      <InfinityShield src={shield} alt="Escudo Infinity de NextGenAI" />
      <div><h1>NEXA ScriptGuard</h1><p>Explorá un reporte prefabricado de un archivo sintético.</p>
      <Sidebar label="Secciones de demostración" links={[{ id: 'demo-findings', label: 'Hallazgos' }, { id: 'demo-exports', label: 'Reportes' }]} />
      </div>
    </>}>
      <section id="demo-findings">
        <h2>Hallazgos sintéticos</h2>
        <label>Criticidad <select value={level} onChange={event => setLevel(event.target.value)}>
          <option value="">Todas</option><option>HIGH</option><option>MEDIUM</option>
        </select></label>
        <p role="status">{findings.length} hallazgos</p>
        {findings.map(item => <FindingCard key={item.id} severity={item.severity === 'HIGH' ? 'HIGH' : 'MEDIUM'}
          rule={item.rule_id} title={item.title}>
          <p>Línea {item.location.start.line} · Columna {item.location.start.column}</p>
          <EvidenceViewer label="Evidencia sintética" value={item.evidence.shared} expandable />
          <EvidenceViewer label="Recomendación" value={item.recommendation} />
        </FindingCard>)}
      </section>
      <section id="demo-exports">
        <h2>Reportes sintéticos</h2>
        <ExportPanel label="Formatos sintéticos" formats={formats} disabled={false} onExport={format => {
          const link = document.createElement('a');
          const [content, type] = reports[format];
          const url = URL.createObjectURL(new Blob([content], { type }));
          link.href = url;
          link.download = `synthetic.${format}`;
          link.click();
          window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        }} />
      </section>
    </Dashboard>
  </>;
}

const root = document.getElementById('root');
if (root) createRoot(root).render(<Demo />);
