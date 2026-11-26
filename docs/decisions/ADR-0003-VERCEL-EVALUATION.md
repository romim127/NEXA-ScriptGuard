# ADR-0003: Evaluate Vercel without adopting it

- **Status:** Evaluation complete; deployment not adopted
- **Decision date:** 2026-11-25

## Context

The local server is a long-lived loopback `ThreadingHTTPServer`, uses a
per-process token and retains the latest report in memory. Vercel serves
functions per invocation and has different runtime, request, filesystem,
privacy, and operational constraints.

## Options considered

1. **Browser-only static application:** would require porting or duplicating
   Bash and Python parsing, rules, redaction, and reports into browser
   technology. This risks drift and does not reuse the existing analyzer.
2. **Python Function API:** could reuse Python modules after creating a
   request/response adapter, but would transfer uploaded scripts to Vercel,
   replace local session assumptions, and require rate, privacy, and abuse
   controls. It would also require testing native parser wheels and the
   optional Rust process on Vercel's build/runtime environment.
3. **Keep local mode:** preserves existing behavior and does not introduce a
   remote data boundary.

## Decision

Do not add Vercel configuration, deploy an endpoint, or change the local
architecture in this consolidation. Keep local mode as the supported product.
If a future hosted prototype is approved, begin with a non-production
synthetic-only deployment and a separate threat/privacy review. Do not send
real user scripts until data handling and consent are approved.

## Verified provider constraints (2026-11-25)

- Vercel documents Python runtimes 3.12, 3.13, and 3.14. Official pages
  reviewed during this evaluation disagree on the default: the version page
  says 3.12, while the 2026-02-02 changelog says 3.14 is the new-project
  default. Pin the runtime explicitly and verify it during deployment rather
  than relying on a default. This project still supports Python 3.10 locally.
- Function request and response payloads are limited to 4.5 MB by default.
  The local maximum input setting is 5 MiB, so an API would need a lower
  effective request limit or a separately approved upload design. Do not rely
  on the documented public-beta larger payload option.
- Python function bundles have a 500 MB uncompressed limit.
- The Functions limits for Hobby with Fluid compute list 2 GB of memory,
  one vCPU, and a maximum duration of 300 seconds. Set a substantially
  shorter application deadline and test on the target runtime.
- Function filesystem is read-only except for up to 500 MB of `/tmp` scratch
  space; files there are instance-local and do not persist after an instance
  stops.
- The Hobby plan is free within included usage but restricted by Vercel's
  terms to personal or non-commercial use. Its published limits and terms can
  change; confirm the intended project use and current plan before adopting.
- Function execution and storage usage may incur cost on paid plans; no
  billing plan has been selected.

## Required gates before a hosted implementation

1. Confirm current Vercel terms, pricing, region, account, and commercial-use
   eligibility with the project owner.
2. Obtain approval for source-file transfer, retention, access, and disclosure.
3. Design stateless request/result/export behavior; do not assume memory or
   `/tmp` survives between invocations.
4. Set server-side request, time, output, and abuse limits below provider
   maxima and handle every exceeded limit as incomplete/error.
5. Verify the exact supported Python runtime and Tree-sitter wheels, and decide
   whether Rust is excluded or built and tested for the target runtime.
6. Add deployment security review, privacy notice, rate limiting, observability
   without source logging, and integration tests before public exposure.

## Proposed deployment contract

Keep the existing HTML, CSS, JavaScript and approved assets as the frontend
baseline. A browser-only prototype would run parsers inside a bounded worker,
produce reports locally as blobs, and use the shared synthetic corpus to
measure rule, redaction and export parity. The current frontend depends on
local analysis and export routes, so hosting the assets alone cannot analyze
scripts. A static demonstration can display precomputed synthetic reports and
label every screen as a demonstration with no upload or analysis capability.
The [synthetic demonstration](../demo/index.html) is prepared as a static
artifact that uses the existing approved assets.

A future remote adapter would validate extension, size and encoding before
parsing. It would use request-local state and produce bounded outputs in the
same invocation. Apply authentication where required, rate and concurrency
limits, isolation, time and memory budgets, and generic errors. Treat filenames
as display metadata, forbid user-controlled paths and outbound requests,
never execute inspected code, escape output, and exclude scripts, evidence,
tokens and secrets from logs. Keep source in memory when feasible and remove
any scratch data on every exit path.

## Phase 4 update

The Vite build produces relative static asset links and can be served as static
files by Vercel. The analyzer uses same-origin `/analyze` and `/export/*`
endpoints and a local-session token, so static hosting exposes a shell only.
A separate experimental serverless adapter would still need its own trust
boundary and verification. The existing synthetic demo remains the candidate
for a public demonstration. [Vercel Vite documentation](https://vercel.com/docs/frameworks/frontend/vite)

## Official sources

Reviewed 2026-11-25:

- [Python runtime versions](https://vercel.com/docs/functions/runtimes/python/python-version)
- [Python 3.13 and 3.14 availability/default announcement](https://vercel.com/changelog/python-3-13-and-3-14-are-now-available)
- [Function limits](https://vercel.com/docs/functions/limitations)
- [Filesystem and runtimes](https://vercel.com/docs/functions/runtimes)
- [Hobby plan usage](https://vercel.com/docs/plans/hobby)
- [Vercel Terms of Service](https://vercel.com/legal/terms)

La Fase 5 agrega configuración de Vercel exclusivamente para la demostración sintética y registra mediciones de viabilidad del navegador. El servidor local se mantiene independiente. [ADR 0005](ADR-0005-STATIC-DEMO-WASM-PROBE.md)
