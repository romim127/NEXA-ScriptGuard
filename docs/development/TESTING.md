# Testing and validation

## Local commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
cargo fmt --manifest-path rust\nexa-scriptguard-helper\Cargo.toml -- --check
cargo clippy --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path rust\nexa-scriptguard-helper\Cargo.toml --all-targets
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
```

Tests use synthetic data. They must not execute a script under inspection or
any investigation command from a finding. The Python suite includes parser,
rules, data flow, GUI HTTP integration, redaction, report schemas, ingestion,
and Rust bridge tests. The Rust suite exercises the helper's declared subset.

## CI

`../../.github/workflows/tests.yml` declares six Python jobs (Windows, Ubuntu, and
macOS × Python 3.10 and 3.12). `.github/workflows/rust.yml` declares three
Rust jobs (Windows, Ubuntu, and macOS). A successful workflow definition is
not evidence of a successful run; record exact commit checks in the release
report.

`../../tests/test_report_schemas.py` validates NEXA JSON against the project schema
and SARIF against the official OASIS schema. This does not substitute for
testing a real SARIF consumer. Fuzz testing is not a sustained, coverage-guided
campaign; current smoke tests must not be described as such.
