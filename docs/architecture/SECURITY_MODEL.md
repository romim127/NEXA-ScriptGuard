# Security model

## Assets and trust boundaries

The input script is untrusted data. The analyzer, parser, report renderers, and
browser display are in scope for robustness and safe output handling. The
analyst's operating system, Python environment, and optional Rust executable
are trusted dependencies and must be obtained from trusted sources.

The local GUI accepts requests only on loopback and checks the Host, Origin,
and per-run token. Uploaded bytes are bounded and passed to the existing
analysis engine. The file content is never executed, evaluated, imported, or
passed to a shell. HTML output escapes untrusted content; browser rendering
uses text nodes rather than interpreting findings as markup.

## Security properties

- Input and output size, finding count, evidence, AST nodes, estimated memory,
  and cooperative analysis time have configured limits.
- Exceeded budgets and parser errors produce an incomplete result, not a clean
  result.
- Report redaction and terminal-control sanitization are applied centrally
  unless a user explicitly requests sensitive evidence for local use.
- CLI output publication rejects existing names and uses exclusive creation;
  multi-file rollback is best-effort, not a transaction.
- The Rust helper receives bounded input over stdin and is invoked without a
  shell. Only a trusted helper path should be configured.

## Residual limitations

Redaction is heuristic and cannot guarantee removal of every secret, path, or
identifier. SHA-256 values can still enable correlation. The parser is not
preemptible while native parsing is in progress, and the memory budget is an
estimate rather than an operating-system quota. GUI download names and
collision behavior are controlled by the browser, not the CLI's no-clobber
writer. The GUI is not protected against malicious processes or extensions
already running as the same local user.

No hosted endpoint is configured. A Vercel deployment would transmit uploaded
source to a third party and therefore requires a separate privacy, security,
abuse-control, retention, and authorization decision. See
[`../decisions/ADR-0003-VERCEL-EVALUATION.md`](../decisions/ADR-0003-VERCEL-EVALUATION.md).
