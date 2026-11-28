import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CodeBlock, EvidenceViewer, ExportPanel, FileUploader, InfinityShield, Sidebar, StatusIndicator } from '@nextgenai/ui';
import fixture from '../../demo/public/reports/synthetic.json';
import { AnalysisFinding } from '../../src/features/analysis/AnalysisFinding';
import { reportSchema } from '../../src/types/report';

afterEach(cleanup);

describe('NextGenAI UI', () => {
  it('highlights Unicode code points while preserving literal markup and whitespace', () => {
    const value = '\t😀<b>\n';
    const { container, rerender } = render(<CodeBlock label="Código" value={value}
      highlight={{ start: 2, end: 5, role: 'sink', label: 'Destino sensible' }} />);
    expect(container.querySelector('mark')?.textContent).toBe('<b>');
    expect(container.querySelector('b')).toBeNull();
    expect(screen.getByRole('region').textContent).toBe(value);
    rerender(<CodeBlock label="Código" value={value}
      highlight={{ start: 2, end: 99, role: 'sink', label: 'Destino sensible' }} />);
    expect(container.querySelector('mark')).toBeNull();
    expect(screen.getByRole('region').textContent).toBe(value);
  });

  it('accepts report 1.0 without SITA and presents the missing coverage', () => {
    const oldReport = {
      ...fixture,
      findings: fixture.findings.map(finding => ({ ...finding, impact_analysis: undefined })),
    };
    const parsed = reportSchema.parse(oldReport);
    render(<AnalysisFinding finding={parsed.findings[0]} />);
    expect(screen.getByText('Análisis de impacto no disponible.')).toBeTruthy();
  });

  it('preserves whitespace and exposes code evidence as a focusable text region', () => {
    const evidence = '\n\t  <b>literal</b>  \n';
    const { container } = render(<EvidenceViewer label="Evidencia" value={evidence} format="code" />);
    const region = screen.getByRole('region', { name: 'Evidencia' });
    expect(region.tagName).toBe('PRE');
    expect(region.tabIndex).toBe(0);
    expect(region.textContent).toBe(evidence);
    expect(container.querySelector('b')).toBeNull();
  });

  it('uses a native disclosure without interpreting markup as evidence', () => {
    const { container } = render(<EvidenceViewer label="Detalles" value="<b>literal</b>" expandable />);
    const details = container.querySelector('details');
    expect(details?.open).toBe(false);
    fireEvent.click(screen.getByText('Detalles'));
    expect(details?.open).toBe(true);
    expect(details?.querySelector('p')?.textContent).toBe('<b>literal</b>');
    expect(details?.querySelector('b')).toBeNull();
  });

  it('renders evidence as text and retains multiline content', () => {
    const evidence = '<img src=x onerror=alert(1)>\nsegunda línea';
    const { container } = render(<EvidenceViewer label="Evidencia" value={evidence} />);
    expect(container.querySelector('p')?.textContent).toBe(evidence);
    expect(container.querySelector('img')).toBeNull();
  });

  it('labels the upload, status, navigation, export and original shield', () => {
    const selected = vi.fn();
    const downloaded = vi.fn();
    render(<>
      <InfinityShield src="/infinity-shield.svg" alt="Escudo Infinity" />
      <Sidebar label="Navegación" links={[{ id: 'results', label: 'Resultados' }]} />
      <StatusIndicator tone="loading">Analizando</StatusIndicator>
      <FileUploader label="Archivo" accept=".sh,.py" disabled={false} onSelect={selected}>
        <button>Analizar</button>
      </FileUploader>
      <ExportPanel label="Formatos" formats={[{ id: 'sarif', label: 'SARIF' }]} disabled={false}
        onExport={downloaded} />
    </>);
    const file = new File(['data'], 'sample.py');
    fireEvent.change(screen.getByLabelText('Archivo'), { target: { files: { item: () => file } } });
    expect(selected).toHaveBeenCalledWith(file);
    expect(screen.getByRole('status').textContent).toBe('Analizando');
    expect(screen.getByRole('link').getAttribute('href')).toBe('#results');
    expect(screen.getByRole('img', { name: 'Escudo Infinity' }).getAttribute('src')).toBe('/infinity-shield.svg');
    fireEvent.click(screen.getByRole('button', { name: 'SARIF' }));
    expect(downloaded).toHaveBeenCalledWith('sarif');
  });
});
