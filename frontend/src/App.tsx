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
    disabled={pending !== null} onExport={exportResult} />;

  return <>
    {demo && <p className="demo-banner" role="note">DEMO MODE — SYNTHETIC DATA</p>}
    <Dashboard header={<>
    <InfinityShield src={shield} alt="Escudo Infinity de NextGenAI" />
    <div>
      <h1>NEXA <b>ScriptGuard</b></h1>
      <div className="subtitle">NEXTGENAI INFINITY · STATIC SECURITY ANALYZER</div>
      <div className="motto">AI assists. Human verifies. Human decides.</div>
      {demo && <p className="demo-creed">THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.</p>}
      {report && <Sidebar label="Navegación del reporte" links={[
        { id: 'archivo', label: demo ? 'Resumen' : 'Archivo y exportaciones' },
        { id: 'hallazgos', label: 'Hallazgos' },
        ...(demo ? [{ id: 'exportaciones', label: 'Exportaciones' }] : []),
      ]} />}
    </div>
  </>}>
    {demo ? <div className="demo-overview">
      <section className="demo-panel" id="archivo" aria-labelledby="demo-overview-title">
        <h2 id="demo-overview-title">Resumen del reporte</h2>
        <p className="demo-file"><strong>{props.report.file}</strong> · {language} · {props.report.lines} líneas</p>
        <dl className="demo-metrics">
          <div><dt>Hallazgos</dt><dd>{props.report.findings.length}</dd></div>
          {severities.map(severity => {
            const count = props.report.findings.filter(finding => finding.severity === severity).length;
            return count > 0 && <div key={severity} className={`metric-${severity.toLowerCase()}`}>
              <dt>{severity}</dt><dd>{count}</dd>
            </div>;
          })}
        </dl>
        <details className="demo-metadata"><summary>Metadatos y alcance</summary>
          <p>Reporte precomputado · {props.report.complete ? 'Análisis completo' : 'Análisis incompleto'} · {props.report.parser}</p>
          <div className="hash">SHA-256: {props.report.sha256}</div>
          <div className="hash">FECHA UTC: {props.report.analyzed_at_utc}</div>
          <p className="notice">Un resultado sin hallazgos no demuestra que el script sea seguro.</p>
        </details>
        <p className="demo-local-help"><strong>¿Querés analizar tu archivo?</strong> Escribí <code>RUN</code> en la terminal. Cuando se abra el navegador, pulsá <strong>Subir archivo</strong>, elegí el script de tu equipo y pulsá <strong>Analizar archivo</strong>.</p>
      </section>
      <section className="demo-panel" id="exportaciones" aria-labelledby="demo-exports-title">
        <h2 id="demo-exports-title">Exportaciones</h2>
        <p className="notice">Descargá el reporte sintético completo.</p>
        {exports}
        {saved && <p role="status">{saved}</p>}
        {error && <p className="summary ngi-status-error" role="alert">{error}</p>}
        <h3>Capacidades del producto</h3>
        <ul className="demo-capabilities" aria-label="Motores disponibles en la aplicación local">
          <li>Bash</li><li>Python</li><li>Rust <small>helper</small></li>
        </ul>
        <p className="notice">Motores disponibles en la aplicación local.</p>
      </section>
    </div> : <section className="top" id="archivo" aria-label="Archivo y exportaciones">
      <FileUploader label="ARCHIVO DE SCRIPT PARA ANALIZAR" buttonLabel="Subir archivo"
        accept=".sh,.py" disabled={pending !== null} onSelect={select}>
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
      {error && <p className="summary ngi-status-error" role="alert">{error}</p>}
      {saved && <p role="status">{saved}</p>}
      {report && <>
        <div>RESUMEN · {report.file} · {report.lines} líneas · Parser: {report.parser}</div>
        {report.findings.length > 0 && <div>Motores de hallazgos: {[...new Set(report.findings.map(finding => finding.engine))].join(', ')}</div>}
        <div className="hash">SHA-256: {report.sha256}</div>
        <div className="hash">FECHA UTC: {report.analyzed_at_utc}</div>
        {exports}
      </>}
      <p className="notice">Un resultado sin hallazgos no demuestra que el script sea seguro. Revise las evidencias antes de compartirlas.</p>
    </section>}
    <section id="hallazgos" aria-label="Hallazgos">
      {demo && <h2>Hallazgos</h2>}
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
