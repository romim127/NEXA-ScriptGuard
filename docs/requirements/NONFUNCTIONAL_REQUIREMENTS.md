# Non-functional requirements

| Area | Requirement | Current status |
|---|---|---|
| Safety | Never execute or import inspected source | Implemented and tested |
| Integrity | Stable identifiers, source hash, and exact locations | Implemented within parser/model limitations |
| Resource use | Bound input, findings, evidence, output, AST nodes, time, and estimated memory | Implemented; parser time and memory are not hard quotas |
| Privacy | Local by default; redact shareable output | Implemented; redaction is heuristic |
| Availability | Preserve existing local CLI/GUI if hosting is later considered | Required architectural constraint |
| Portability | Declare Windows/Linux/macOS and supported Python versions | CI matrix declares all three OS and Python 3.10/3.12 |
| Interoperability | Validate JSON and SARIF contracts | Schema tests pass; consumer interoperability remains unverified |
| Maintainability | Modular engines, tests, documentation, and stable contracts | Implemented with documented semantic gaps |

Exact test results and environment limitations belong in the
consolidation report, not inferred from these requirements.

Phase 5 keeps local runtime dependencies and limits. Static demo assets use a separate output and a CSP without connections. Browser-side analysis remains experimental. [ADR 0005](../decisions/ADR-0005-STATIC-DEMO-WASM-PROBE.md)

SITA-03 requiere funcionamiento local dentro de los límites compartidos, sin ejecución y con rangos verificados sobre evidencia compartible. [Presupuestos](../architecture/SITA.md#presupuestos-y-validación).
