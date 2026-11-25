# ADR-0001: Keep analysis local-first

- **Status:** Accepted
- **Decision date:** 2026-11-25

## Context

The selected scripts may contain credentials, paths, or proprietary logic.
The existing GUI and CLI operate locally and require no hosted account. A
remote implementation would change the privacy boundary and add operational
controls.

## Decision

Keep the supported product local-first. The local CLI and GUI remain the
reference implementation. A hosted experiment must not replace, silently
redirect, or disable local analysis.

## Consequences

- Source remains on the user's machine in the default workflow.
- A remote analyzer requires a separate decision and explicit data-flow
  disclosure.
- Tests and releases continue to verify local functionality regardless of
  hosting experiments.
