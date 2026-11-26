import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { EvidenceViewer, ExportPanel, FileUploader, InfinityShield, Sidebar, StatusIndicator } from '@nextgenai/ui';

afterEach(cleanup);

describe('NextGenAI UI', () => {
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
