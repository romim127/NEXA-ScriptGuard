# ADR-0002: Emit SARIF 2.1.0

- **Status:** Accepted
- **Decision date:** 2026-11-25

## Context

NEXA provides shareable findings in JSON, HTML, and SARIF. SARIF 2.1.0 has an
OASIS schema and can be consumed by compatible code-scanning tools, but schema
validity alone does not demonstrate consumer interoperability.

## Decision

Keep SARIF 2.1.0 as the interchange format. Validate generated documents
against the official OASIS Errata 01 schema in automated tests. Keep the NEXA
JSON contract explicitly project-specific.

## Consequences

- Rule identifiers, locations, evidence, severity, and state map from the
  shared finding model.
- Any consumer-specific incompatibility must be covered by an integration
  test and documented.
- No local SARIF consumer is installed in this environment; consumer
  interoperability is therefore still unverified.
