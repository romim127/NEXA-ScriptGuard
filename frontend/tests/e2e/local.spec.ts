import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const probe = fileURLToPath(new URL('./browser_probe.py', import.meta.url)).replaceAll('\\', '/');
const python = process.env.NEXA_PYTHON ?? 'python';

async function service() {
  const folder = await mkdtemp(join(tmpdir(), 'nexa-e2e-'));
  const capture = join(folder, 'browser.txt');
  const run = process.env.NEXA_RUN;
  const browser = `"${python.replaceAll('\\', '/')}" "${probe}" %s`;
  const processPath = run && process.platform !== 'win32' ? folder : process.env.PATH;
  const child = spawn(run ?? python, run ? [] : ['-m', 'nexa_scriptguard.gui'], {
    cwd: run ? folder : root,
    env: { ...process.env, PATH: processPath, PYTHONIOENCODING: 'utf-8', BROWSER: browser, NEXA_BROWSER_CAPTURE: capture },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const closed = new Promise<number | null>((resolve, reject) => {
    child.once('error', reject);
    child.once('close', resolve);
  });
  // Consume the private URL from stdout without logging it.
  child.stdout.resume();
  child.stderr.resume();
  let stopped = false;
  async function stop() {
    if (stopped) return;
    stopped = true;
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGINT');
    const timeout = setTimeout(() => child.kill('SIGKILL'), 5000);
    try {
      return await closed;
    } finally {
      clearTimeout(timeout);
      await rm(folder, { recursive: true, force: true });
    }
  }
  try {
    const url = await Promise.race([
      closed.then(() => { throw new Error('La GUI se cerró antes de abrir el navegador.'); }),
      expect.poll(async () => (await readFile(capture, 'utf-8').catch(() => '')).startsWith('http://127.0.0.1:'), {
        timeout: 15000,
      }).toBe(true).then(() => readFile(capture, 'utf-8')),
    ]);
    return { url: new URL(url), stop };
  } catch (error) {
    await stop();
    throw error;
  }
}

test('local GUI analyzes Bash and Python offline and saves physical reports', async ({ page, request }) => {
  const first = await service();
  let second: Awaited<ReturnType<typeof service>> | undefined;
  try {
    second = await service();
    expect(second.url.port).not.toBe(first.url.port);
    expect(second.url.hash).not.toBe(first.url.hash);
    const external: string[] = [];
    await page.route('**/*', async route => {
      if (new URL(route.request().url()).origin !== first.url.origin) {
        external.push(route.request().url());
        await route.abort();
      } else {
        await route.continue();
      }
    });
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error' && message.text().includes('Content Security Policy')) {
        errors.push(message.text());
      }
    });
    await page.setViewportSize({ width: 360, height: 640 });
    await page.goto(first.url.href);
    await expect(page.getByRole('heading', { name: 'NEXA ScriptGuard' })).toBeVisible();
    const shield = page.getByRole('img', { name: 'Escudo Infinity de NextGenAI' });
    await expect(shield).toBeVisible();
    expect(await shield.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
    expect(new URL(page.url()).hash).toBe('');
    expect((await request.get(second.url.origin)).ok()).toBe(true);
    const input = page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR');
    const analyze = page.getByRole('button', { name: 'Analizar archivo' });

    await input.setInputFiles({ name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('text') });
    await expect(page.getByRole('alert')).toContainText('Seleccione un archivo');
    await expect(analyze).toBeDisabled();
    await input.setInputFiles(join(root, 'demo_example.sh'));
    await analyze.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status')).toContainText('ANÁLISIS COMPLETO');
    await expect(page.getByRole('article')).toHaveCount(2);
    await page.getByRole('link', { name: 'Hallazgos', exact: true }).click();
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);

    await input.setInputFiles(join(root, 'tests/corpus/gui_incomplete.sh'));
    await analyze.click();
    await expect(page.getByRole('status')).toContainText('ANÁLISIS INCOMPLETO');
    await expect(page.getByRole('article')).toHaveCount(1);
    await expect(page.locator('#hallazgos img')).toHaveCount(0);

    await page.route('**/analyze', route => route.fulfill({ status: 500, json: { error: '<script>malicious</script>' } }), { times: 1 });
    await analyze.click();
    await expect(page.getByRole('alert')).toHaveText('Error del servidor (HTTP 500).');
    await expect(page.getByRole('button', { name: 'Exportar JSON' })).toHaveCount(0);

    await input.setInputFiles(join(root, 'tests/corpus/python_gui_example.py'));
    await analyze.click();
    await expect(page.getByRole('status')).toContainText('ANÁLISIS COMPLETO');
    await expect(page.getByRole('article')).toHaveCount(4);
    await expect(page.getByText('PY-005', { exact: true })).toBeVisible();
    for (const format of ['JSON', 'HTML', 'SARIF']) {
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name: `Exportar ${format}` }).click();
      const file = await download;
      expect(file.suggestedFilename()).toBe(`nexa-scriptguard-report.${format.toLowerCase()}`);
      const path = await file.path();
      const contents = await readFile(path, 'utf-8');
      expect(contents).not.toContain('sample_placeholder');
      if (format === 'JSON') expect(JSON.parse(contents).findings).toHaveLength(4);
      if (format === 'SARIF') expect(JSON.parse(contents).runs[0].results).toHaveLength(4);
      if (format === 'HTML') expect(contents).toContain('<!doctype html>');
    }
    expect(external).toEqual([]);
    expect(errors).toEqual([]);

    await page.goto(first.url.origin + '/legacy' + first.url.hash);
    await expect(page.getByRole('img', { name: 'Escudo Infinity de NextGenAI' })).toBeVisible();
    await expect(page).toHaveURL(first.url.origin + '/legacy');
    await page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR').setInputFiles(join(root, 'demo_example.sh'));
    await analyze.click();
    await expect(page.getByRole('status')).toContainText('2 HALLAZGOS');
  } finally {
    const stopped = await Promise.all([first.stop(), second?.stop()]);
    if (process.platform !== 'win32') expect(stopped.filter(value => value !== undefined)).toEqual([0, 0]);
  }
  await expect(request.get(first.url.origin)).rejects.toThrow();
  await expect(request.get(second.url.origin)).rejects.toThrow();
});

test('static bundle renders at a subpath without a backend', async ({ page }) => {
  const deploy = new URL('https://static.example.invalid/demo/');
  const assets = join(root, 'nexa_scriptguard/gui_assets/modern');
  const files = new Map([
    ['', 'index.html'], ['phase4.js', 'phase4.js'], ['phase4.css', 'phase4.css'],
    ['phase4-infinity-shield.svg', 'phase4-infinity-shield.svg'],
  ]);
  const requests: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    const file = files.get(url.pathname.slice(deploy.pathname.length));
    if (url.origin === deploy.origin && url.pathname.startsWith(deploy.pathname) && file) {
      await route.fulfill({ path: join(assets, file) });
    } else {
      requests.push(url.pathname);
      await route.abort();
    }
  });
  await page.goto(deploy.href + '#' + 'a'.repeat(43));
  await expect(page.getByRole('heading', { name: 'NEXA ScriptGuard' })).toBeVisible();
  const shield = page.getByRole('img', { name: 'Escudo Infinity de NextGenAI' });
  await expect.poll(() => shield.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  await page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR').setInputFiles(join(root, 'demo_example.sh'));
  await page.getByRole('button', { name: 'Analizar archivo' }).click();
  await expect(page.getByRole('alert')).toContainText('Sesión no autorizada.');
  expect(requests).toEqual([]);
});
