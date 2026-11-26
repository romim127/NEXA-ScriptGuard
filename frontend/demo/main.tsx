import { createRoot } from 'react-dom/client';
import { App } from '../src/App';
import { reportSchema } from '../src/types/report';
import fixture from './public/reports/synthetic.json';
import htmlReport from './public/reports/synthetic.html?raw';
import sarifReport from './public/reports/synthetic.sarif?raw';
import './demo.css';

const reports = {
  json: [JSON.stringify(fixture, null, 2), 'application/json'],
  html: [htmlReport, 'text/html'],
  sarif: [sarifReport, 'application/sarif+json'],
} as const;

const root = document.getElementById('root');
if (!root) throw new Error('No se encontró la raíz de la interfaz.');
createRoot(root).render(<App mode="demo" report={reportSchema.parse(fixture)} exportSample={format => {
  const [content, type] = reports[format];
  return new Blob([content], { type });
}} />);
