# Functional requirements

Status labels: **implemented** means present in the current repository;
**partial** means bounded or heuristic; **not implemented** means not
available.

| Requirement | Status | Notes |
|---|---|---|
| Analyze Bash and Python source without executing it | Implemented | Tree-sitter Bash and Python `ast` |
| Select `.sh` or `.py` in the local GUI | Implemented | Other extensions rejected |
| Show findings, severity, location, evidence, and recommendations | Implemented | Evidence is shared/redacted by default |
| Report complete versus incomplete analysis | Implemented | Reaching a known limit is not a clean result |
| Export JSON, HTML, and SARIF | Implemented | GUI uses browser downloads; browser collision behavior is external |
| Use optional Rust helper with a versioned JSON protocol | Implemented, limited | Rust capability subset is documented |
| Analyze installer binaries or execute scripts | Not implemented | Deliberately outside current scope |
| Provide hosted Vercel analysis | Not implemented | Evaluation only; no deployment or endpoint |
| Launch the local GUI from any working directory | Implemented | Platform launchers and an explicitly installed `RUN` command. [NGI-STD-002](../governance/NGI-STD-002_LOCAL_APPLICATION_LAUNCH_STANDARD.md) |

Rule coverage and semantics are documented in
[`../RULES.md`](../RULES.md) and
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).
