// @vitest-environment node
import { expect, it, vi } from 'vitest';
import { createClient } from '../../src/services/api';

const token = 'x'.repeat(43);
const resultId = 'y'.repeat(32);
const local = 'http://127.0.0.1:55555';
const report = {
  schema_version: '1.0', parser: 'python-ast', sha256: 'a'.repeat(64),
  file: 'example.py', lines: 1,
  analyzed_at_utc: '2026-11-25T12:00:00+00:00', complete: true,
  analysis_status: 'complete', incomplete_reasons: [], redaction_applied: true, limitations: [],
  findings: [],
};
const file = new File(['example'], 'análisis.py');

it('sends snapshot bytes and token only to same-origin routes', async () => {
  const request = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(Response.json(report, { headers: { 'X-Nexa-Result': resultId } }))
    .mockResolvedValueOnce(new Response('report', { headers: { 'Content-Type': 'text/html; charset=utf-8' } }));
  const client = createClient(token, request, local);
  expect(await client.analyze(file)).toEqual({ report, resultId });
  expect(request).toHaveBeenNthCalledWith(1, '/analyze', expect.objectContaining({
    method: 'POST', body: file, mode: 'same-origin', redirect: 'error', cache: 'no-store',
    headers: { 'X-Nexa-Filename': encodeURIComponent(file.name), 'X-Nexa-Token': token, 'Content-Type': 'application/octet-stream' },
  }));
  expect(await (await client.export('html', resultId)).text()).toBe('report');
  expect(request).toHaveBeenNthCalledWith(2, '/export/html', expect.objectContaining({
    method: 'GET', headers: { 'X-Nexa-Result': resultId, 'X-Nexa-Token': token },
  }));
});

it('rejects missing sessions, malformed responses and raw server diagnostics', async () => {
  const request = vi.fn<typeof fetch>()
    .mockResolvedValueOnce(Response.json({ ...report, redaction_applied: false }, { headers: { 'X-Nexa-Result': resultId } }))
    .mockResolvedValueOnce(Response.json(report))
    .mockResolvedValueOnce(new Response('unexpected HTML', { headers: { 'Content-Type': 'text/html' } }))
    .mockResolvedValueOnce(Response.json({ error: 'private diagnostic' }, { status: 500 }));
  await expect(createClient('', request, local).analyze(file)).rejects.toThrow(/no autorizada/);
  await expect(createClient(token, request, 'https://static.example.invalid').analyze(file)).rejects.toThrow(/no autorizada/);
  expect(request).not.toHaveBeenCalled();
  const client = createClient(token, request, local);
  await expect(client.analyze(file)).rejects.toThrow(/inválido/);
  await expect(client.analyze(file)).rejects.toThrow(/inválido/);
  await expect(client.export('json', resultId)).rejects.toThrow(/formato inesperado/);
  await expect(client.analyze(file)).rejects.toThrow('Error del servidor (HTTP 500).');
});
