import { createRoot } from 'react-dom/client';
import { App } from './App';
import { createClient, readSession } from './services/api';
import '../../nexa_scriptguard/gui_assets/app.css';
import '@nextgenai/ui/theme.css';
import './results.css';

const root = document.getElementById('root');
if (!root) throw new Error('No se encontró la raíz de la interfaz.');
const limit = Number(document.body.dataset.maxInputBytes);
createRoot(root).render(<App client={createClient(readSession())}
  maxInputBytes={Number.isSafeInteger(limit) && limit > 0 ? limit : undefined} />);
