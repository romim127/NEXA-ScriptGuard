import { useState } from 'react';
import {
  Dashboard, ExportPanel, FileUploader, InfinityShield, Sidebar, StatusIndicator, severities,
} from '@nextgenai/ui';
import shield from '../../nexa_scriptguard/gui_assets/infinity-shield.svg?url';
import { FindingExplorer } from './features/analysis/FindingExplorer';
import { downloadReport } from './features/reports/download';
import type { createClient, Analysis, ExportFormat } from './services/api';
import type { Report } from './types/report';
import '../../nexa_scriptguard/gui_assets/app.css';
import '@nextgenai/ui/theme.css';
import './results.css';
import './dashboard.css';

const formats = [
  { id: 'json', label: 'Exportar JSON' },
  { id: 'html', label: 'Exportar HTML' },
  { id: 'sarif', label: 'Exportar SARIF' },
] as const;

function languageFor(name?: string) {
  if (!name) return '—';
  if (/\.sh$/i.test(name)) return 'Bash';
  if (/\.py$/i.test(name)) return 'Python';
  return 'No compatible';
}

type AppProps = {
  mode?: 'local';
  client: ReturnType<typeof createClient>;
  maxInputBytes?: number;
} | {
  mode: 'demo';
  report: Report;
  exportSample: (format: ExportFormat) => Blob;
};

export function App(props: AppProps) {
  const demo = props.mode === 'demo';
  const maxInputBytes = demo ? undefined : props.maxInputBytes;
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [pending, setPending] = useState<'analyze' | 'export' | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const report = demo ? props.report : analysis?.report;
  const language = report?.parser === 'python-ast' ? 'Python' : languageFor(report?.file ?? file?.name);
  const tooLarge = file != null && maxInputBytes != null && file.size > maxInputBytes;

  function select(next: File | null) {
    setFile(next);
    setAnalysis(null);
    setSaved('');
    if (next && maxInputBytes != null && next.size > maxInputBytes) {
      setError('El archivo supera el límite de entrada.');
    } else {
      setError(languageFor(next?.name) === 'No compatible' ? 'Seleccione un archivo Bash (.sh) o Python (.py).' : '');
    }
  }

  async function analyze() {
    if (demo || !file || pending || tooLarge || language === 'No compatible') return;
    setPending('analyze');
    setAnalysis(null);
    setSaved('');
    setError('');
    try {
      setAnalysis(await props.client.analyze(file));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo analizar el archivo.');
    } finally {
      setPending(null);
    }
  }

  async function exportResult(format: ExportFormat) {
    const result = analysis;
    const exportBlob = demo ? () => props.exportSample(format)
      : result ? () => props.client.export(format, result.resultId) : null;
    if (pending || !exportBlob) return;
    setPending('export');
    setSaved('');
    setError('');
    try {
      downloadReport(await exportBlob(), format, demo ? 'synthetic' : undefined);
      setSaved(`Descarga ${format.toUpperCase()} iniciada.`);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo exportar el reporte.');
    } finally {
      setPending(null);
    }
  }

  const summary = report && severities.map(severity => {
    const count = report.findings.filter(finding => finding.severity === severity).length;
    return count ? ` · ${severity} ${count}` : '';
  });
  const exports = <ExportPanel label="Exportaciones" formats={formats}
    disabled={!report || pending !== null} onExport={exportResult} />;

  return <>
    {demo && <p className="demo-banner" role="note">DEMO MODE — SYNTHETIC DATA</p>}
    <Dashboard className="scriptguard-dashboard" header={<>
    <InfinityShield src={shield} alt="Escudo Infinity de NextGenAI" />
    <div>
      <h1>NEXA <b>ScriptGuard</b></h1>
      <div className="subtitle">NEXTGENAI INFINITY · STATIC SECURITY ANALYZER</div>
      <div className="motto">AI assists. Human verifies. Human decides.</div>
      <p className="dashboard-creed">THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.</p>
      <Sidebar label="Navegación del reporte" links={[
        { id: 'archivo', label: demo ? 'Resumen' : 'Archivo' },
        { id: 'hallazgos', label: 'Hallazgos' },
        { id: 'exportaciones', label: 'Exportaciones' },
      ]} />
    </div>
  </>}>
    <div className="dashboard-overview">
      <section className="dashboard-panel" id="archivo" aria-label={demo ? 'Resumen del reporte' : 'Archivo de análisis'}>
        {demo ? <h2>Resumen del reporte</h2> : <>
          <FileUploader label="ARCHIVO DE SCRIPT PARA ANALIZAR" accept=".sh,.py" disabled={pending !== null} onSelect={select}>
            <button type="button" onClick={analyze} disabled={!file || pending !== null || tooLarge || language === 'No compatible'}>
              Analizar archivo
            </button>
          </FileUploader>
          <div>ARCHIVO SELECCIONADO · <strong className="path">{file?.name ?? 'Ninguno'}</strong></div>
          <div>LENGUAJE DETECTADO · <strong>{language}</strong></div>
          <StatusIndicator tone={pending ? 'loading' : report ? report.complete ? 'success' : 'warning' : 'idle'}>
            {pending === 'analyze' ? 'ANALIZANDO · El script no se ejecuta.'
              : pending === 'export' ? 'EXPORTANDO · Preparando el reporte.'
              : report ? <>{report.complete ? 'ANÁLISIS COMPLETO' : 'ANÁLISIS INCOMPLETO'} · {report.findings.length} HALLAZGOS{summary}</>
              : file ? 'Seleccione Analizar archivo.' : 'Seleccione un archivo. No se ejecutará.'}
          </StatusIndicator>
        </>}
        {error && <p className="summary ngi-status-error" role="alert">{error}</p>}
        {report && <>
        <p className="dashboard-file"><strong>{report.file}</strong> · {language} · {report.lines} líneas · Parser: {report.parser}</p>
        {!demo && report.findings.length > 0 && <div>Motores de hallazgos: {[...new Set(report.findings.map(finding => finding.engine))].join(', ')}</div>}
        <dl className="dashboard-metrics">
          <div><dt>Hallazgos</dt><dd>{report.findings.length}</dd></div>
          {severities.map(severity => {
            const count = report.findings.filter(finding => finding.severity === severity).length;
            return count > 0 && <div key={severity} className={`metric-${severity.toLowerCase()}`}>
              <dt>{severity}</dt><dd>{count}</dd>
            </div>;
          })}
        </dl>
        <details className="dashboard-metadata"><summary>Metadatos y alcance</summary>
          {demo && <p>Reporte precomputado · {report.complete ? 'Análisis completo' : 'Análisis incompleto'}</p>}
          <div className="hash">SHA-256: {report.sha256}</div>
          <div className="hash">FECHA UTC: {report.analyzed_at_utc}</div>
          <p className="notice">Un resultado sin hallazgos no demuestra que el script sea seguro.</p>
        </details>
        </>}
      </section>
      <section className="dashboard-panel" id="exportaciones" aria-labelledby="exports-title">
        <h2 id="exports-title">Exportaciones</h2>
        <p className="notice">{demo ? 'Descargá el reporte sintético completo.'
          : report ? 'Descargá el reporte completo.' : 'El reporte estará disponible después de analizar un archivo.'}</p>
        {exports}
        {saved && <p role="status">{saved}</p>}
        <h3>Capacidades del producto</h3>
        <ul className="dashboard-capabilities" aria-label="Motores disponibles en la aplicación local">
          <li>Bash</li><li>Python</li><li>Rust <small>helper</small></li>
        </ul>
        <p className="notice">Motores disponibles en la aplicación local.</p>
      </section>
    </div>
    <section id="hallazgos" aria-label="Hallazgos">
      <h2>Hallazgos</h2>
      {!report && <p className="notice">Los hallazgos aparecerán acá después del análisis.</p>}
      {report?.incomplete_reasons.map((reason, index) => <p className="notice" key={index}>INCOMPLETO: {reason}</p>)}
      {!!report?.limitations.length && <details><summary>Limitaciones del análisis</summary>
        <ul>{report.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>
      </details>}
      {report?.findings.length === 0 && <p className="notice">Sin coincidencias detectadas.</p>}
      {!!report?.findings.length && <FindingExplorer findings={report.findings} compact={demo} />}
    </section>
    </Dashboard>
  </>;
}
