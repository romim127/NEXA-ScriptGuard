# Reporting contracts

All renderers use the same normalized finding model. A finding includes a
stable rule identifier and version, source hash and location, instruction,
context, severity, confidence, review status, evidence, explanation,
recommendation, verification guidance, and analysis limitations.

## Formats

| Format | Contract | Validation |
|---|---|---|
| NEXA JSON | Project schema `nexa-report-1.0` | Automated schema tests in `../../tests/test_report_schemas.py` |
| SARIF | SARIF 2.1.0, OASIS Errata 01 schema | Automated validation against the official schema |
| HTML | Escaped standalone report | GUI and report tests; no remote assets |
| Terminal | Rich/plain output with control sanitization | CLI and redaction tests |

JSON is a project-specific contract, not an external standard. SARIF schema
validation does not establish compatibility with every SARIF consumer; local
consumer interoperability has not been verified because no SARIF viewer or
CodeQL consumer is installed.

The Rust helper uses contract version `1.0` and protocol
`json-v1-stdin`. It has a smaller capability set than the Python engine.
Protocol and schema changes must update producer, consumer, fixtures, and
compatibility documentation together.

By default, shareable reports use redacted evidence and preserve a distinction
between original and shared evidence. Redaction remains best-effort.

JSON 1.0 admite `impact_analysis` opcional. SARIF lo conserva en `result.properties.impactAnalysis`. Véase el [ADR 0006](../decisions/ADR-0006-SITA.md).
