# Release and change policy

NEXA ScriptGuard is experimental; version `0.5.0a1` is not a security
certification. A release candidate must:

1. Pass the Python test suite and Rust formatting, tests, Clippy, and build
   on the declared local validation environment.
2. Have successful CI checks for every declared platform and Python version
   on the exact candidate commit.
3. Preserve incomplete-analysis signaling, output escaping, and default
   redaction.
4. Include changes to schemas, rule catalogs, architecture, and limitations in
   their directly related documentation.
5. Record untested platforms, known blockers, and residual risks in a release
   report.

Do not announce support based only on workflow configuration. Never include
`.venv/`, `.vscode/`, `target/`, caches, local reports, secrets, or user input
in a release commit. Keep `Cargo.lock` versioned for the Rust executable.

The human maintainer reviews and approves changes before they are published.
