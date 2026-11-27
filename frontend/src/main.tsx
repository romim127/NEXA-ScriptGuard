import { createRoot } from 'react-dom/client';
import { App } from './App';
import { createClient, readSession } from './services/api';

const root = document.getElementById('root');
if (!root) throw new Error('No se encontró la raíz de la interfaz.');
const limit = Number(document.body.dataset.maxInputBytes);
createRoot(root).render(<App client={createClient(readSession())}
  maxInputBytes={Number.isSafeInteger(limit) && limit > 0 ? limit : undefined} />);
