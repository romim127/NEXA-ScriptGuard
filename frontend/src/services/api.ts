import { reportSchema, type Report } from '../types/report';

const sessionKey = 'nexa-token';
const identifier = /^[A-Za-z0-9_-]{32,128}$/;
const loopback = /^http:\/\/127\.0\.0\.1:[1-9]\d{0,4}$/;
const exportTypes = {
  json: 'application/json',
  html: 'text/html',
  sarif: 'application/sarif+json',
};

export type ExportFormat = keyof typeof exportTypes;
export type Analysis = { report: Report; resultId: string };

export function readSession(): string {
  const fragment = window.location.hash.slice(1);
  if (identifier.test(fragment)) {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    if (!loopback.test(window.location.origin)) return '';
    try { window.sessionStorage.setItem(sessionKey, fragment); } catch { /* Storage may be disabled. */ }
    return fragment;
  }
  if (!loopback.test(window.location.origin)) return '';
  try {
    const stored = window.sessionStorage.getItem(sessionKey) ?? '';
    return identifier.test(stored) ? stored : '';
  } catch {
    return '';
  }
}

const errors: Record<number, string> = {
  400: 'La solicitud o el archivo no es válido.',
  403: 'Sesión no autorizada. Volvé a abrir la URL privada de la consola.',
  409: 'Hay otro análisis en curso o el resultado venció. Volvé a analizar.',
  413: 'El archivo o resultado supera el límite configurado.',
};

function checkResponse(response: Response, contentType: string) {
  if (!response.ok) throw new Error(errors[response.status] ?? `Error del servidor (HTTP ${response.status}).`);
  const actual = response.headers.get('Content-Type')?.split(';', 1)[0].trim();
  if (actual !== contentType) throw new Error('El servidor devolvió un formato inesperado.');
}

export function createClient(token: string, request: typeof fetch = fetch, origin = globalThis.location?.origin ?? '') {
  async function send(path: string, init: RequestInit) {
    if (!loopback.test(origin) || !identifier.test(token)) throw new Error(errors[403]);
    try {
      return await request(path, {
        ...init, mode: 'same-origin', credentials: 'same-origin', redirect: 'error',
        cache: 'no-store', headers: { ...init.headers, 'X-Nexa-Token': token },
      });
    } catch {
      throw new Error('No se pudo conectar al servidor local.');
    }
  }

  return {
    async analyze(file: File): Promise<Analysis> {
      const response = await send('/analyze', {
        method: 'POST',
        headers: { 'X-Nexa-Filename': encodeURIComponent(file.name), 'Content-Type': 'application/octet-stream' },
        body: file,
      });
      checkResponse(response, 'application/json');
      const resultId = response.headers.get('X-Nexa-Result') ?? '';
      const payload: unknown = await response.json().catch(() => null);
      const parsed = reportSchema.safeParse(payload);
      if (!identifier.test(resultId) || !parsed.success) {
        throw new Error('El servidor devolvió un resultado inválido.');
      }
      return { report: parsed.data, resultId };
    },
    async export(format: ExportFormat, resultId: string): Promise<Blob> {
      const response = await send(`/export/${format}`, {
        method: 'GET', headers: { 'X-Nexa-Result': resultId },
      });
      checkResponse(response, exportTypes[format]);
      return response.blob();
    },
  };
}
