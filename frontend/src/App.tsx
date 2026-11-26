import { useState } from 'react';
import {
  Dashboard, ExportPanel, FileUploader, InfinityShield, Sidebar, StatusIndicator, severities,
} from '@nextgenai/ui';
import shield from '../../nexa_scriptguard/gui_assets/infinity-shield.svg?url';
import { AnalysisFinding } from './features/analysis/AnalysisFinding';
import { downloadReport } from './features/reports/download';
import { createClient, type Analysis, type ExportFormat } from './services/api';

const formats = [
  { id: 'json', label: 'Exportar JSON' },
  { id: 'html', label: 'Exportar HTML' },
  { id: 'sarif', label: 'Exportar SARIF' },
] as const;

function languageFor(file: File | null) {
  if (!file) return '—';
  if (/\.sh$/i.test(file.name)) return 'Bash';
  if (/\.py$/i.test(file.name)) return 'Python';
  return 'No compatible';
}

export function App({ client }: { client: ReturnType<typeof createClient> }) {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [pending, setPending] = useState<'analyze' | 'export' | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');
  const report = analysis?.report;
  const language = report?.parser === 'python-ast' ? 'Python' : languageFor(file);

  function select(next: File | null) {
    setFile(next);
    setAnalysis(null);
    setSaved('');
    setError(languageFor(next) === 'No compatible' ? 'Seleccione un archivo Bash (.sh) o Python (.py).' : '');
  }

  async function analyze() {
    if (!file || pending || language === 'No compatible') return;
    setPending('analyze');
    setAnalysis(null);
    setSaved('');
    setError('');
    try {
      setAnalysis(await client.analyze(file));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'No se pudo analizar el archivo.');
    } finally {
      setPending(null);
    }
  }

  async function exportResult(format: ExportFormat) {
    if (!analysis || pending) return;
    setPending('export');
    setSaved('');
    setError('');
    try {
      downloadReport(await client.export(format, analysis.resultId), format);
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

  return <Dashboard header={<>
    <InfinityShield src={shield} alt="Escudo Infinity de NextGenAI" />
    <div>
      <h1>NEXA <b>ScriptGuard</b></h1>
      <div className="subtitle">NEXTGENAI INFINITY · STATIC SECURITY ANALYZER</div>
      <div className="motto">AI assists. Human verifies. Human decides.</div>
      {report && <Sidebar label="Navegación del reporte" links={[
        { id: 'archivo', label: 'Archivo y exportaciones' },
        { id: 'hallazgos', label: 'Hallazgos' },
      ]} />}
    </div>
  </>}>
    <section className="top" id="archivo" aria-label="Archivo y exportaciones">
      <FileUploader label="ARCHIVO DE SCRIPT PARA ANALIZAR" accept=".sh,.py" disabled={pending !== null} onSelect={select}>
        <button type="button" onClick={analyze} disabled={!file || pending !== null || language === 'No compatible'}>
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
        <div className="hash">SHA-256: {report.sha256}</div>
        <div className="hash">FECHA UTC: {report.analyzed_at_utc}</div>
        <ExportPanel label="Exportaciones" formats={formats} disabled={pending !== null} onExport={exportResult} />
      </>}
      <p className="notice">Un resultado sin hallazgos no demuestra que el script sea seguro. Revise las evidencias antes de compartirlas.</p>
    </section>
    <section id="hallazgos" aria-label="Hallazgos">
      {report?.incomplete_reasons.map((reason, index) => <p className="notice" key={index}>INCOMPLETO: {reason}</p>)}
      {!!report?.limitations.length && <details><summary>Limitaciones del análisis</summary>
        <ul>{report.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>
      </details>}
      {report?.findings.length === 0 && <p className="notice">Sin coincidencias detectadas.</p>}
      {report?.findings.map(finding => <AnalysisFinding key={finding.id} finding={finding} />)}
    </section>
  </Dashboard>;
}
