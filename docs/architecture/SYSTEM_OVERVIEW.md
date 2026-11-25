# System overview

NEXA ScriptGuard is a local-first static analyzer for Bash and Python source.
It reads scripts as data and never imports or executes the file being analyzed.
Investigation commands are explanatory recommendations and are not run.

## Local analysis path

1. The local GUI or CLI accepts a `.sh` or `.py` path and applies input limits.
2. `ingestion.py` reads and hashes the input; `analysis.py` selects the engine.
3. Bash uses Tree-sitter Bash and syntax-node rules. Python uses the standard
   library `ast` and the PY rule catalog.
4. Context and data-flow analysis add conservative correlations; they do not
   prove runtime reachability or execution.
5. A common finding model is classified, bounded, and redacted for sharing.
6. JSON, HTML, SARIF, and terminal renderers consume that report model.
7. An optional Rust helper is invoked as a separate process with a versioned
   JSON protocol. It analyzes the same bounded input snapshot and is not a
   replacement for the Python Bash parser.

The local GUI binds to `127.0.0.1`, requires a per-run token, and retains only
the current result in memory. It is not a network service.

## Implemented boundaries

- Bash: Tree-sitter grammar, syntax-node rules, and limited flow correlations.
- Python: AST-based rules PY-001 through PY-008, with limited alias and
  source/sink handling.
- Rust: optional helper with only the capabilities listed in
  [`../ARCHITECTURE.md`](../ARCHITECTURE.md).
- Reports: shared output model, JSON contract, and SARIF 2.1.0.

See the detailed module and resource-limit description in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md), and the identifiers in
[`../RULES.md`](../RULES.md). This overview does not claim complete shell or
Python semantic analysis.
