import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Locator, type Page } from '@playwright/test';
import { build } from 'vite';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const probe = fileURLToPath(new URL('./browser_probe.py', import.meta.url)).replaceAll('\\', '/');
const python = process.env.NEXA_PYTHON ?? 'python';

async function service() {
  const folder = await mkdtemp(join(tmpdir(), 'nexa-e2e-'));
  const capture = join(folder, 'browser.txt');
  const run = process.env.NEXA_RUN;
  const browser = `"${python.replaceAll('\\', '/')}" "${probe}" %s`;
  const processPath = run && process.platform !== 'win32' ? folder : process.env.PATH;
  const child = spawn(run ?? python, run ? ['scriptguard'] : ['-m', 'nexa_scriptguard.gui'], {
    cwd: run ? folder : root,
    env: { ...process.env, PATH: processPath, PYTHONIOENCODING: 'utf-8', BROWSER: browser, NEXA_BROWSER_CAPTURE: capture },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const closed = new Promise<number | null>((resolve, reject) => {
    child.once('error', reject);
    child.once('close', resolve);
  });
  // Drain diagnostics. The browser probe receives the private URL separately.
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

test('local acceptance file completes analysis and exports in the same session', async ({ page }) => {
  const sample = process.env.NEXA_ACCEPTANCE_FILE;
  test.skip(!sample, 'Optional acceptance file stays outside the test fixtures.');
  const instance = await service();
  try {
    await page.goto(instance.url.href);
    const file = page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR');
    const analyze = page.getByRole('button', { name: 'Analizar archivo' });
    await file.setInputFiles(sample!);
    const firstResult = page.waitForResponse(response => response.url().endsWith('/analyze'));
    await analyze.click();
    expect((await firstResult).status()).toBe(200);
    await verifyImpactNavigation(page, 'local');
    for (const format of ['JSON', 'HTML', 'SARIF']) {
      const download = page.waitForEvent('download');
      await page.getByRole('button', { name: `Exportar ${format}` }).click();
      expect(await (await download).failure()).toBeNull();
    }
    await file.setInputFiles({ name: 'second.py', mimeType: 'text/plain', buffer: Buffer.from('value = 1\n') });
    const secondResult = page.waitForResponse(response => response.url().endsWith('/analyze'));
    await analyze.click();
    expect((await secondResult).status()).toBe(200);
  } finally {
    await instance.stop();
  }
});

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
    const exportJson = page.getByRole('button', { name: 'Exportar JSON' });
    await expect(page.getByRole('navigation', { name: 'Navegación del reporte' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Capacidades del producto' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Hallazgos', exact: true })).toBeVisible();
    await expect(exportJson).toBeDisabled();
    await expect(page.locator('.dashboard-metrics')).toHaveCount(0);
    if (process.env.NEXA_VISUAL_DIR) {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.screenshot({ path: join(process.env.NEXA_VISUAL_DIR, 'local-inicio.png'), fullPage: true });
      await page.setViewportSize({ width: 360, height: 640 });
    }

    await input.setInputFiles({ name: 'invalid.txt', mimeType: 'text/plain', buffer: Buffer.from('text') });
    await expect(page.getByRole('alert')).toContainText('Seleccione un archivo');
    await expect(analyze).toBeDisabled();
    const chooser = page.waitForEvent('filechooser');
    await expect(input).toBeVisible();
    await input.press('Enter');
    await (await chooser).setFiles(join(root, 'demo_example.sh'));
    await expect(page.getByText('demo_example.sh', { exact: true })).toBeVisible();
    await analyze.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status')).toContainText('ANÁLISIS COMPLETO');
    await expect(page.getByRole('article')).toHaveCount(2);
    await expect(exportJson).toBeEnabled();
    await expect(page.locator('.dashboard-metrics dd')).toHaveText(['2', '2']);
    if (process.env.NEXA_VISUAL_DIR) {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.screenshot({ path: join(process.env.NEXA_VISUAL_DIR, 'local-reporte.png'), fullPage: true });
      await page.setViewportSize({ width: 360, height: 640 });
    }
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
    await expect(page.getByRole('button', { name: 'Exportar JSON' })).toBeDisabled();

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
        const languageArea = route === '/' ? page.locator('#archivo') : page.locator('main');
        await expect(languageArea.getByText(language, { exact: true })).toBeVisible();
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
    await expect(page.locator('.ngi-disclosure[open] .ngi-code')).toBeVisible();
  } finally {
    await instance.stop();
  }
});

test('premium demo fits each viewport and downloads only synthetic reports', async ({ page }) => {
  const origin = 'https://demo.example.invalid';
  const location = join(root, 'frontend/demo/dist');
  const deploy = JSON.parse(await readFile(join(root, 'vercel.json'), 'utf-8'));
  expect(deploy.outputDirectory).toBe('frontend/demo/dist');
  expect(deploy.buildCommand).toBe('npm run build:demo');
  const requests: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || !/^\/(?:assets\/[a-zA-Z0-9_.-]+|reports\/synthetic\.(?:json|html|sarif))?$/.test(url.pathname)) {
      requests.push(url.pathname);
      return route.abort();
    }
    await route.fulfill({ path: join(location, url.pathname === '/' ? 'index.html' : url.pathname.slice(1)),
      headers: Object.fromEntries(deploy.headers[0].headers.map(({ key, value }: { key: string; value: string }) => [key, value])) });
  });
  await page.goto(origin);
  await expect(page.getByRole('note')).toHaveText('DEMO MODE — SYNTHETIC DATA');
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByText('¿Querés analizar tu archivo?', { exact: true })).toHaveCount(0);
  expect(await page.locator('html').evaluate(element => getComputedStyle(element).overflowY)).toBe('scroll');
  await expect(page.getByRole('article')).toHaveCount(2);
  await expect(page.locator('.dashboard-metrics dd')).toHaveText(['2', '1', '1']);
  await expect(page.getByRole('list', { name: 'Motores disponibles en la aplicación local' })).toContainText('Rust');
  await expect(page.getByRole('button', { name: 'Analizar archivo' })).toHaveCount(0);
  const contrast = await page.locator('.demo-banner, .dashboard-metrics > div, .ngi-navigation a, .dashboard-panel button')
    .evaluateAll(elements => elements.map(element => {
      function luminance(color: string) {
        const channels = color.match(/\d+(?:\.\d+)?/g)?.slice(0, 3).map(Number) ?? [];
        return channels.reduce((total, channel, index) => {
          const value = channel / 255;
          const linear = value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
          return total + linear * [0.2126, 0.7152, 0.0722][index];
        }, 0);
      }
      const style = getComputedStyle(element);
      const [low, high] = [luminance(style.color), luminance(style.backgroundColor)].sort((a, b) => a - b);
      return (high + 0.05) / (low + 0.05);
    }));
  expect(Math.min(...contrast)).toBeGreaterThanOrEqual(4.5);

  for (const viewport of [
    { name: 'escritorio', width: 1440, height: 1000 },
    { name: 'tablet', width: 820, height: 1060 },
    { name: 'movil', width: 390, height: 844 },
    { name: 'movil-estrecho', width: 320, height: 740 },
  ]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const dimensions = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewport);
    const cards = await page.getByRole('article').evaluateAll(elements => elements.map(element => ({
      x: element.getBoundingClientRect().x,
      border: getComputedStyle(element).borderTopColor,
    })));
    expect(cards[0].border).not.toBe(cards[1].border);
    if (viewport.width > 750) expect(cards[1].x).toBeGreaterThan(cards[0].x);
    else expect(cards[1].x).toBe(cards[0].x);
    if (process.env.NEXA_VISUAL_DIR && viewport.width >= 390) {
      await page.screenshot({ path: join(process.env.NEXA_VISUAL_DIR, viewport.name + '.png'), fullPage: true });
    }
  }
  await page.keyboard.press('Tab');
  const firstLink = page.getByRole('link', { name: 'Resumen' });
  await expect(firstLink).toBeFocused();
  expect(await firstLink.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe('none');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Hallazgos', exact: true })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#hallazgos$/);
  await expect.poll(() => page.getByRole('note').evaluate(element => element.getBoundingClientRect().top)).toBe(0);
  await page.getByLabel('Criticidad').selectOption('MEDIUM');
  await expect(page.getByRole('article')).toHaveCount(1);
  await page.getByText('EVIDENCIA COMPARTIBLE').press('Enter');
  await expect(page.locator('.ngi-disclosure[open] .ngi-code')).toBeVisible();
  for (const format of ['JSON', 'HTML', 'SARIF']) {
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: `Exportar ${format}` }).click();
    const contents = await readFile(await (await download).path(), 'utf-8');
    expect(contents).toContain('DEMO MODE — SYNTHETIC DATA');
    expect(contents).not.toContain('synthetic_example');
  }
  await page.getByLabel('Criticidad').selectOption('');
  await verifyImpactNavigation(page, 'demo');
  expect(requests).toEqual([]);
});

const scrollViewports = [360, 390, 768, 1366, 1920];

async function verifyImpactNavigation(page: Page, mode: 'local' | 'demo') {
  const finding = page.getByRole('article').filter({ hasText: 'PY-001' }).first();
  const sita = finding.locator('.sita');
  const details = sita.getByText('Ver impacto, confianza y evidencia');
  const target = sita.getByRole('button', { name: /Destino sensible/ }).first();
  await expect(sita).toContainText('IMPACTO NO OBSERVADO');
  await expect(sita.getByText('Cobertura sintáctica', { exact: true })).toBeVisible();
  await details.press('Enter');
  await expect(sita.getByRole('heading', { name: 'Confidencialidad', exact: true })).toBeVisible();
  await target.press('Enter');
  await expect(finding.getByRole('region', { name: 'Instrucción detectada' })).toBeFocused();
  await expect(finding.locator('mark')).toHaveText('eval');
  for (const width of scrollViewports) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    if (process.env.NEXA_SITA_VISUAL_DIR && [390, 1366].includes(width)) {
      await sita.screenshot({ path: join(process.env.NEXA_SITA_VISUAL_DIR, `${mode}-${width}.png`) });
    }
  }
  await details.click();
}
const longInstruction = 'eval(\n    "' + '0123456789  '.repeat(70) + '"\n)';
const fixtureEvidence = '\t  primera línea\n' + longInstruction + '\n  última línea  ';

async function verifyCodeScroll(page: Page, block: Locator, expected: string) {
  await expect(block).toBeVisible();
  expect(await block.textContent()).toBe(expected);
  await block.scrollIntoViewIfNeeded();
  await block.evaluate(element => { element.scrollLeft = 0; });
  const dimensions = await block.evaluate(element => {
    const style = getComputedStyle(element);
    const node = element.firstChild!;
    const text = node.textContent!;
    const longest = text.split('\n').reduce((a, b) => a.length > b.length ? a : b);
    const start = text.indexOf(longest);
    const range = document.createRange();
    range.setStart(node, start);
    range.setEnd(node, start + longest.length);
    return { clientWidth: element.clientWidth, scrollWidth: element.scrollWidth, lines: range.getClientRects().length,
      before: element.scrollLeft, whiteSpace: style.whiteSpace };
  });
  expect(dimensions.scrollWidth).toBeGreaterThan(dimensions.clientWidth);
  expect(dimensions.whiteSpace).toBe('pre');
  expect(dimensions.lines).toBe(1);
  await block.focus();
  await expect(block).toBeFocused();
  await page.keyboard.press('ArrowRight');
  await expect.poll(() => block.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
  return { ...dimensions, after: await block.evaluate(element => element.scrollLeft) };
}

async function verifyTouchScroll(page: Page, block: Locator) {
  await block.evaluate(element => {
    element.scrollIntoView({ block: 'center' });
    element.scrollLeft = 0;
  });
  const box = await block.boundingBox();
  expect(box).not.toBeNull();
  const touch = await page.context().newCDPSession(page);
  try {
    await touch.send('Emulation.setTouchEmulationEnabled', { enabled: true });
    const x = Math.floor(box!.x + box!.width * 0.8);
    const y = Math.floor(box!.y + box!.height / 2);
    expect(await block.evaluate((element, point) =>
      element.contains(document.elementFromPoint(point.x, point.y)), { x, y })).toBe(true);
    await touch.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
    for (const distance of [20, 45, 75, 105, 140, 175]) {
      await touch.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x - distance, y }] });
    }
    await touch.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await expect.poll(() => block.evaluate(element => element.scrollLeft)).toBeGreaterThan(0);
    return await block.evaluate(element => element.scrollLeft);
  } finally {
    await touch.send('Emulation.setTouchEmulationEnabled', { enabled: false });
    await touch.detach();
  }
}

async function verifyScrollMatrix(page: Page, mode: 'local' | 'demo', expectedInstruction: string, expectedEvidence: string) {
  const card = page.getByRole('article').filter({ has: page.locator('.rule').filter({ hasText: /^PY-001$/ }) });
  const instruction = card.getByRole('region', { name: 'Instrucción detectada' });
  await card.locator('summary').filter({ hasText: 'EVIDENCIA COMPARTIBLE' }).click();
  const evidence = card.getByRole('region', { name: 'EVIDENCIA COMPARTIBLE' });
  for (const width of scrollViewports) {
    await page.setViewportSize({ width, height: 720 });
    const code = await verifyCodeScroll(page, instruction, expectedInstruction);
    const shared = await verifyCodeScroll(page, evidence, expectedEvidence);
    const horizontalPage = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(horizontalPage).toBeLessThanOrEqual(0);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect.poll(() => page.evaluate(() =>
      Math.abs(document.documentElement.scrollHeight - innerHeight - scrollY))).toBeLessThanOrEqual(2);
    expect(await page.evaluate(() => scrollY)).toBeGreaterThan(0);
    const touch = width === 390 ? await verifyTouchScroll(page, evidence) : null;
    console.log('SG-UI-001 ' + JSON.stringify({ mode, width, code, evidence: shared, horizontalPage, touch }));
    if (process.env.NEXA_SCROLL_VISUAL_DIR && [390, 1366].includes(width)) {
      await instruction.evaluate(element => { element.scrollLeft = 100; });
      await evidence.evaluate(element => { element.scrollLeft = 100; });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: join(process.env.NEXA_SCROLL_VISUAL_DIR, `${mode}-${width}.png`), fullPage: true });
    }
  }
}

test('SG-UI-001: installed local dashboard preserves long code and does not execute samples', async ({ page }) => {
  test.setTimeout(90000);
  const instance = await service();
  const temp = await mkdtemp(join(tmpdir(), 'nexa-acceptance-'));
  const marker = join(temp, 'executed.txt').replaceAll(String.fromCharCode(92), '/');
  let posts = 0;
  page.on('request', req => {
    if (req.method() === 'POST' && new URL(req.url()).pathname === '/analyze') posts++;
  });
  try {
    await page.goto(instance.url.href);
    const input = page.getByLabel('ARCHIVO DE SCRIPT PARA ANALIZAR');
    const analyze = page.getByRole('button', { name: 'Analizar archivo' });
    await expect(input).toBeVisible();
    expect(await input.evaluate((el: HTMLInputElement) => el.files?.length)).toBe(0);
    await expect(analyze).toBeDisabled();
    const chooser = page.waitForEvent('filechooser');
    await input.press('Enter');
    await (await chooser).setFiles({ name: 'acceptance.py', mimeType: 'text/plain',
      buffer: Buffer.from(`open(${JSON.stringify(marker)}, "w").write("test")\nvalue = ${longInstruction}\n`) });
    await expect(analyze).toBeEnabled();
    await expect(page.getByRole('article')).toHaveCount(0);
    expect(posts).toBe(0);
    await analyze.click();
    await expect(page.getByRole('status').first()).toContainText('ANÁLISIS COMPLETO');
    await expect(page.locator('.flag')).toContainText('HIGH');
    await expect(page.locator('.metadata')).toContainText('Línea 2 · Columna 9');
    await verifyScrollMatrix(page, 'local', '0002 │ ' + longInstruction, longInstruction);
    await verifyImpactNavigation(page, 'local');
    const shellPath = "'" + marker.replaceAll("'", "'\\''") + "'";
    await input.setInputFiles({ name: 'acceptance.sh', mimeType: 'text/plain',
      buffer: Buffer.from(`printf test > ${shellPath}\neval 'echo sample'\n`) });
    expect(posts).toBe(1);
    await analyze.click();
    await expect(page.locator('.rule')).toHaveText('SG-005');
    expect(posts).toBe(2);
    expect(new URL(page.url()).origin).toBe(instance.url.origin);
    await expect(readFile(marker)).rejects.toMatchObject({ code: 'ENOENT' });
  } finally {
    await instance.stop();
    await rm(temp, { recursive: true, force: true });
  }
});

test('SG-UI-001: static demo preserves synthetic evidence at the same viewports', async ({ page }, testInfo) => {
  test.setTimeout(90000);
  const output = testInfo.outputPath('demo-scroll');
  await build({
    configFile: join(root, 'frontend/demo/vite.config.ts'),
    build: { outDir: output, emptyOutDir: false },
    logLevel: 'error',
    plugins: [{
      name: 'nexa-test-long-evidence',
      enforce: 'pre',
      transform(code, id) {
        if (!id.endsWith('/public/reports/synthetic.json')) return;
        const report = JSON.parse(code);
        report.findings[0].instruction = longInstruction;
        report.findings[0].evidence.shared = fixtureEvidence;
        return JSON.stringify(report);
      },
    }],
  });
  const origin = 'https://demo-scroll.example.invalid';
  const unexpected: string[] = [];
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || !/^\/(?:assets\/[a-zA-Z0-9_.-]+)?$/.test(url.pathname)) {
      unexpected.push(url.pathname);
      return route.abort();
    }
    await route.fulfill({ path: join(output, url.pathname === '/' ? 'index.html' : url.pathname.slice(1)) });
  });
  await page.goto(origin);
  await expect(page.getByRole('note')).toHaveText('DEMO MODE — SYNTHETIC DATA');
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Analizar archivo' })).toHaveCount(0);
  await verifyScrollMatrix(page, 'demo', '0002 │ ' + longInstruction, fixtureEvidence);
  expect(unexpected).toEqual([]);
});
