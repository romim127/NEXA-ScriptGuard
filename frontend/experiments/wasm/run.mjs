/* global setTimeout, clearTimeout, Worker */
import assert from 'node:assert/strict';
import console from 'node:console';
import { spawnSync } from 'node:child_process';
import { readFile, readdir, stat } from 'node:fs/promises';
import { createServer } from 'node:http';
import { join } from 'node:path';
import process from 'node:process';
import { fileURLToPath, URL } from 'node:url';
import { chromium } from '@playwright/test';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const vendors = process.env.NEXA_WASM_VENDOR ?? join(root, '.venv/phase5-probe/node_modules');
const wasm = join(root, 'rust/nexa-scriptguard-helper/target/wasm32-wasip1/release/nexa-scriptguard-helper.wasm');
const python = process.env.NEXA_PYTHON ?? 'python';
const pythonFixture = 'value = eval("1+1")\n';
const bashFixture = 'echo synthetic\n';
const canonical = join(root, 'nexa_scriptguard');
const moduleFiles = (await readdir(canonical)).filter(name => /\.(?:py|json)$/.test(name));
const pyFiles = Object.fromEntries(await Promise.all(moduleFiles.map(async name =>
  [name, await readFile(join(canonical, name), 'utf8')])));

const assets = new Map([
  ['/', ['text/html', '<!doctype html><title>Local synthetic WASM probe</title>']],
  ['/worker.mjs', ['text/javascript', await readFile(new URL('./worker.mjs', import.meta.url))]],
  ['/python-modules.json', ['application/json', JSON.stringify(pyFiles)]],
]);
const binaries = [
  ['pyodide/pyodide.asm.wasm', 'application/wasm'],
  ['pyodide/pyodide.asm.mjs', 'text/javascript'],
  ['pyodide/pyodide.mjs', 'text/javascript'],
  ['pyodide/python_stdlib.zip', 'application/zip'],
  ['pyodide/pyodide-lock.json', 'application/json'],
  ['web-tree-sitter/tree-sitter.js', 'text/javascript'],
  ['web-tree-sitter/tree-sitter.wasm', 'application/wasm'],
  ['tree-sitter-bash/tree-sitter-bash.wasm', 'application/wasm'],
];
for (const [name, mime] of binaries) assets.set('/' + name, [mime, await readFile(join(vendors, name))]);
assets.set('/helper.wasm', ['application/wasm', await readFile(wasm)]);

const nativeProbe = spawnSync(python, ['-c', `
import json
from pathlib import Path
from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.ingestion import Source
from tree_sitter import Language, Parser
import tree_sitter_bash
path = Path("synthetic.py")
report = analyze(path, source=Source(path, ${JSON.stringify(pythonFixture)}.encode(), -1, -1)).to_dict()
parser = Parser(Language(tree_sitter_bash.language()))
print(json.dumps({"python_rules": [x["rule_id"] for x in report["findings"]],
                  "bash_tree": str(parser.parse(${JSON.stringify(bashFixture)}.encode()).root_node)}))
`], { cwd: root, encoding: 'utf8' });
assert.equal(nativeProbe.status, 0, nativeProbe.stderr);
const native = JSON.parse(nativeProbe.stdout);
const local = createServer((req, res) => {
  const entry = assets.get(req.url);
  if (!entry) return res.writeHead(404).end();
  res.writeHead(200, { 'Content-Type': entry[0] }).end(entry[1]);
});
await new Promise(resolve => local.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${local.address().port}`;
try {
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL });
  try {
    const page = await browser.newPage();
    await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await page.goto(origin);
    const result = await page.evaluate(fixtures => new Promise((resolve, reject) => {
      const worker = new Worker('/worker.mjs', { type: 'module' });
      const timeout = setTimeout(() => { worker.terminate(); reject(new Error('worker deadline')); }, 30000);
      worker.onmessage = ({ data }) => {
        clearTimeout(timeout);
        worker.terminate();
        if (data.error) reject(new Error(data.error)); else resolve(data);
      };
      worker.onerror = event => { clearTimeout(timeout); worker.terminate(); reject(new Error(event.message)); };
      worker.postMessage(fixtures);
    }), { pythonFixture, bashFixture });
    assert.deepEqual(result.pythonRules, native.python_rules);
    assert.equal(result.bashTree, native.bash_tree);
    assert(result.rustImports.includes('wasi_snapshot_preview1'));
    const sizes = Object.fromEntries(await Promise.all(binaries.map(async ([name]) =>
      [name, (await stat(join(vendors, name))).size])));
    console.log(JSON.stringify({ ...result, sizes, rustWasmBytes: (await stat(wasm)).size }, null, 2));
  } finally {
    await browser.close();
  }
} finally {
  local.close();
}
