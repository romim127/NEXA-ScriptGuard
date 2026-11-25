# Project charter

## Purpose

NEXA ScriptGuard provides explainable, static security signals for Bash and
Python scripts so a human reviewer can decide what to investigate.

## Principles

- Analyze source as data; do not execute or import it.
- Prefer explicit evidence and limitations over claims of certainty.
- Treat findings as review signals, not proof of malicious intent.
- Keep the supported local workflow available independently of any hosting
  provider.
- Preserve the approved NextGenAI Infinity identity and shield.
- Human reviewers decide whether findings are relevant and what actions to
  take.

## Scope

The project includes a local GUI and CLI, Bash and Python static analysis,
optional Rust helper, safe report generation, tests, and contributor
documentation. It does not currently provide a hosted service, binary
installer analysis, dynamic execution, or complete language semantics.

## Project status

Version `0.5.0a1` is experimental. A clean result is not a safety
certification. Release readiness and residual work are recorded in
[`../reports/NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md`](../reports/NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md).
