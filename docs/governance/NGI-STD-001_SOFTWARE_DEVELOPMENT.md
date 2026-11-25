# NGI-STD-001 — Software development and frontend standard

Status: approved technology direction; incremental implementation, not a claim of completed migration.

## Principles
COMPLETE BY DESIGN. INCREMENTAL BY IMPLEMENTATION.
Local-first, security by design, human verification, backwards compatibility, modular contracts, traceability. GitHub is the source of truth: commit, push, PR and merge after required checks; no ZIP delivery, no force push, no secrets. Preserve approved visual identity.

## Preferred stack
React + TypeScript (TSX) + Vite; CSS/CSS Modules; Python + FastAPI for APIs where needed; Pydantic, OpenAPI and JSON Schema; Rust for justified specialized processing; PostgreSQL or SQLite when persistence is required; pytest/unittest, Vitest, Playwright; ESLint, TypeScript, rustfmt, Clippy; SCA, SAST, secret scanning; Git/GitHub Actions; Docker where justified; Vercel or GitHub Pages for compatible frontend deployments, local/Render/compatible Vercel functions for backend; local AI models when appropriate. These are preferences, not mandatory dependencies for every project. HTML remains appropriate for standalone reports.

## Shared design system (planned)
```
nextgenai-ui/
├── components/
│   ├── InfinityShield.tsx
│   ├── FindingCard.tsx
│   ├── SeverityBadge.tsx
│   ├── FileUploader.tsx
│   ├── ExportPanel.tsx
│   ├── Dashboard.tsx
│   ├── EvidenceViewer.tsx
│   ├── Sidebar.tsx
│   └── StatusIndicator.tsx
├── themes/
│   └── infinity.css
├── types/
├── tests/
└── package.json
```
Use typed props, accessible controls, responsive layout, reusable design tokens, semantic versioning and tests. Preserve the approved Infinity shield asset. Render untrusted evidence as text; avoid unsafe HTML injection. Lock dependencies and audit them.

## Adoption gates — NEXA ScriptGuard
First finish existing Bash/Python integration, physical export and collision checks, SARIF consumer validation, CI and PR/merge into main. Do not bypass blockers or claim unperformed tests. Preserve the local launch command, existing engines, reports, shield and security controls. Then record an ADR and incrementally introduce a TSX frontend behind a stable typed API, with parity and regression tests before replacing any existing UI. No execution or import of inspected scripts. Keep standalone HTML reports. Evaluate Vercel separately; do not send scripts or evidence remotely without explicit consent and appropriate safeguards. A public demo must be labeled as such. Update governance, architecture, requirements traceability, roadmap and implementation status. Do not implement this migration before the consolidation gate.

THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.
AI assists. Human verifies. Human decides.
