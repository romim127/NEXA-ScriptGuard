/* global self, fetch, performance, WebAssembly */
import { loadPyodide } from '/pyodide/pyodide.mjs';
import { Language, Parser } from '/web-tree-sitter/tree-sitter.js';

self.onmessage = async ({ data }) => {
  try {
    const start = performance.now();
    const pyodide = await loadPyodide({ indexURL: '/pyodide/' });
    const pythonReady = performance.now();
    const modules = await (await fetch('/python-modules.json')).json();
    pyodide.FS.mkdir('/home/pyodide/nexa_scriptguard');
    for (const [name, source] of Object.entries(modules)) {
      pyodide.FS.writeFile('/home/pyodide/nexa_scriptguard/' + name, source);
    }
    pyodide.globals.set('synthetic_text', data.pythonFixture);
    const pythonRules = JSON.parse(pyodide.runPython(`
import json, sys
sys.path.insert(0, "/home/pyodide")
from pathlib import Path
from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.ingestion import Source
path = Path("synthetic.py")
report = analyze(path, source=Source(path, synthetic_text.encode(), -1, -1)).to_dict()
json.dumps([x["rule_id"] for x in report["findings"]])
`));
    const pythonFinished = performance.now();
    await Parser.init({ locateFile: () => '/web-tree-sitter/tree-sitter.wasm' });
    const parser = new Parser();
    parser.setLanguage(await Language.load('/tree-sitter-bash/tree-sitter-bash.wasm'));
    const tree = parser.parse(data.bashFixture);
    const bashTree = tree.rootNode.toString();
    tree.delete();
    parser.delete();
    const bashFinished = performance.now();
    const rust = await WebAssembly.compileStreaming(fetch('/helper.wasm'));
    self.postMessage({
      pythonRules, bashTree,
      rustImports: [...new Set(WebAssembly.Module.imports(rust).map(entry => entry.module))],
      pythonLoadMs: Math.round(pythonReady - start),
      pythonSampleMs: Math.round(pythonFinished - pythonReady),
      bashLoadAndSampleMs: Math.round(bashFinished - pythonFinished),
      pythonLinearMemoryBytes: pyodide._module.HEAPU8.buffer.byteLength,
    });
  } catch (error) {
    self.postMessage({ error: String(error) });
  }
};
