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
    await expect(page.locator('.rule').filter({ hasText: 'PY-005' })).toBeVisible();
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

test('modern and legacy have semantic parity across complete and incomplete reports', async ({ page }) => {
  const instance = await service();
  try {
    await page.setViewportSize({ width: 375, height: 650 });
    const samples = [
      ['demo_example.sh', 'Bash', 'COMPLETO'],
      ['tests/corpus/python_gui_example.py', 'Python', 'COMPLETO'],
      ['tests/corpus/gui_incomplete.sh', 'Bash', 'INCOMPLETO'],
    ] as const;
    for (const [sample, language, status] of samples) {
      const snapshots = [];
      for (const route of ['/', '/legacy']) {
        await page.goto(instance.url.origin + route + instance.url.hash);
        const selector = page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR');
        await selector.setInputFiles(join(root, sample));
        const analyze = page.getByRole('button', { name: 'Analizar archivo' });
        await analyze.focus();
        await page.keyboard.press('Enter');
        await expect(page.getByRole('status').first()).toContainText(`ANÁLISIS ${status}`);
        await expect(page.getByText(language, { exact: true })).toBeVisible();
        const json = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Exportar JSON' }).click();
        const report = JSON.parse(await readFile(await (await json).path(), 'utf-8'));
        delete report.analyzed_at_utc;
        const cards = page.locator('.finding');
        await expect(cards).toHaveCount(report.findings.length);
        for (const [index, finding] of report.findings.entries()) {
          const card = cards.nth(index);
          const evidence = card.locator('summary').filter({ hasText: 'EVIDENCIA COMPARTIBLE' });
          if (route === '/') await evidence.click();
          await expect(card.locator('.rule')).toHaveText(finding.rule_id);
          await expect(card.locator('.flag')).toContainText(finding.severity);
          await expect(card.locator('.metadata')).toContainText(new RegExp(`línea ${finding.line} · columna ${finding.column}`, 'i'));
          await expect(card).toContainText(finding.explanation);
          await expect(card).toContainText(finding.recommendation);
          await expect(card).toContainText(finding.evidence.shared);
        }
        await page.mouse.wheel(0, 700);
        await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
        const reports: unknown[] = [];
        for (const format of ['HTML', 'SARIF']) {
          const started = page.waitForEvent('download');
          await page.getByRole('button', { name: `Exportar ${format}` }).click();
          const contents = await readFile(await (await started).path(), 'utf-8');
          if (format === 'HTML') {
            reports.push(contents);
          } else {
            const parsed = JSON.parse(contents);
            delete parsed.analyzed_at_utc;
            reports.push(parsed);
          }
        }
        snapshots.push({ report, reports });
      }
      expect(snapshots[0]).toEqual(snapshots[1]);
    }

    for (const route of ['/', '/legacy']) {
      await page.goto(instance.url.origin + route + instance.url.hash);
      const input = page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR');
      const analyze = page.getByRole('button', { name: 'Analizar archivo' });
      await input.setInputFiles({ name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('example') });
      if (route === '/legacy') await analyze.click();
      await expect(page.getByText('Seleccione un archivo Bash (.sh) o Python (.py).', { exact: false })).toBeVisible();
      await input.setInputFiles({ name: 'limite.py', mimeType: 'text/plain', buffer: Buffer.alloc(5 * 1024 * 1024 + 1, 32) });
      await expect(analyze).toBeDisabled();
      await expect(page.getByText(/supera el límite/)).toBeVisible();
    }
  } finally {
    await instance.stop();
  }
});

test('modern explorer filters, sorts and navigates to expandable evidence', async ({ page }) => {
  const instance = await service();
  try {
    await page.goto(instance.url.href);
    await page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR').setInputFiles(join(root, 'tests/corpus/python_gui_example.py'));
    await page.getByRole('button', { name: 'Analizar archivo' }).click();
    await expect(page.getByRole('article')).toHaveCount(4);
    await expect(page.getByText(/Parser: python-ast/)).toBeVisible();
    await expect(page.getByText(/Motores de hallazgos: python/)).toBeVisible();
    await page.getByLabel('Criticidad').selectOption('MEDIUM');
    await expect(page.getByRole('article')).toHaveCount(1);
    await page.getByLabel('Regla').selectOption('PY-001');
    await expect(page.getByText('Ningún hallazgo coincide con los filtros.')).toBeVisible();
    await page.getByLabel('Criticidad').selectOption('');
    await expect(page.getByRole('article')).toHaveCount(1);
    await page.getByLabel('Regla').selectOption('');
    await page.getByLabel('Buscar hallazgos').fill('PY-005');
    await expect(page.getByRole('article')).toHaveCount(1);
    await page.getByLabel('Buscar hallazgos').clear();
    await page.getByLabel('Orden').selectOption('line');
    await expect(page.getByRole('article').first()).toContainText('PY-005');
    await page.getByText('Ir a una ubicación detectada').click();
    await page.getByRole('link', { name: /PY-005/ }).click();
    await expect(page).toHaveURL(/#finding-0$/);
    await page.getByText('EVIDENCIA COMPARTIBLE').first().click();
    await expect(page.locator('.ngi-disclosure[open] p')).toBeVisible();
  } finally {
    await instance.stop();
  }
});

test('static demo shares the local design and downloads only synthetic reports', async ({ page }) => {
  const origin = 'https://demo.example.invalid';
  const location = join(root, 'frontend/demo/dist');
  const requests: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || !/^\/(?:assets\/[a-zA-Z0-9_.-]+|reports\/synthetic\.(?:json|html|sarif))?$/.test(url.pathname)) {
      requests.push(url.pathname);
      return route.abort();
    }
    await route.fulfill({ path: join(location, url.pathname === '/' ? 'index.html' : url.pathname.slice(1)) });
  });
  await page.goto(origin);
  await expect(page.getByRole('note')).toHaveText('DEMO MODE — SYNTHETIC DATA');
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByRole('article')).toHaveCount(2);
  const instance = await service();
  const local = await page.context().newPage();
  try {
    await local.goto(instance.url.href);
    await local.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR').setInputFiles(join(root, 'tests/corpus/python_gui_example.py'));
    await local.getByRole('button', { name: 'Analizar archivo' }).click();
    await expect(local.getByRole('article')).toHaveCount(4);
    const styles = () => ['body', 'main', 'header', 'h1 b', '.shield', '.summary', '.finding', '.flag', '[aria-label="Exportaciones"] button']
      .map(selector => {
        const element = document.querySelector(selector);
        if (!element) throw new Error(`Missing element: ${selector}`);
        const css = getComputedStyle(element);
        return [css.backgroundImage, css.backgroundColor, css.color, css.fontSize, css.padding,
          css.borderColor, css.borderRadius, css.boxShadow, css.maxWidth];
      });
    for (const width of [780, 1440]) {
      const viewport = { width, height: 800 };
      await page.setViewportSize(viewport);
      await local.setViewportSize(viewport);
      expect(await page.evaluate(styles)).toEqual(await local.evaluate(styles));
    }
  } finally {
    await local.close();
    await instance.stop();
  }
  await page.getByLabel('Criticidad').selectOption('MEDIUM');
  await expect(page.getByRole('article')).toHaveCount(1);
  await page.getByText('EVIDENCIA COMPARTIBLE').click();
  await expect(page.locator('.ngi-disclosure[open] p')).toBeVisible();
  for (const format of ['JSON', 'HTML', 'SARIF']) {
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: `Exportar ${format}` }).click();
    const contents = await readFile(await (await download).path(), 'utf-8');
    expect(contents).toContain('DEMO MODE — SYNTHETIC DATA');
    expect(contents).not.toContain('synthetic_example');
  }
  expect(requests).toEqual([]);
});
