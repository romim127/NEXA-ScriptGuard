import type { ExportFormat } from '../../services/api';

export function downloadReport(blob: Blob, format: ExportFormat) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `nexa-scriptguard-report.${format}`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
