# Project tree and documentation map

This map describes the committed project layout. Local `.vscode/`, `.venv/`,
`target/`, caches, and package build artifacts are excluded by `.gitignore`.
`Cargo.lock` is tracked for the Rust executable.

```text
.
├── .github/workflows/       CI matrices for Python and Rust
├── design/archive/          Approved original visual reference
├── docs/
│   ├── architecture/        System, security model, output contracts
│   ├── decisions/            Accepted ADRs and Vercel evaluation
│   ├── development/          Setup, tests, project map
│   ├── governance/           Charter, data handling, releases
│   ├── requirements/         Functional, quality, acceptance criteria
│   ├── audits/               Baseline technical audit
│   └── reports/              Implementation and readiness reports
├── nexa_scriptguard/         Python analyzer, GUI assets, reports
├── rust/nexa-scriptguard-helper/
│   ├── Cargo.toml
│   ├── Cargo.lock
│   └── src/main.rs
├── tests/
│   ├── corpus/
│   ├── schemas/
│   └── test_*.py
├── demo_example.sh
├── pyproject.toml
├── README.md
└── README.en.md
```

Existing detailed references: [`../ARCHITECTURE.md`](../ARCHITECTURE.md),
[`../RULES.md`](../RULES.md), [`../ROADMAP.md`](../ROADMAP.md), and
[`../Ollama-analysis.md`](../Ollama-analysis.md). The archive HTML is a design
reference and is not a live analysis report.
