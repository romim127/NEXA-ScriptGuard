# ♾ NEXA ScriptGuard

**NextGenAI Infinity** · *AI assists. Human verifies. Human decides.*

Open-source **experimental** static analysis of shell scripts. This repository contains a Python CLI and a separate Rust helper prototype. **Neither engine executes the inspected script.**

## Install and run in VS Code

Python 3.10+:

```bash
git clone https://github.com/romim127/NEXA-ScriptGuard.git
cd NEXA-ScriptGuard
code .
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
nexa-scriptguard demo_example.sh --view neon --html report.html --json report.json --sarif report.sarif
```

On Ubuntu use `python3` if needed. Do not execute `demo_example.sh`; it contains deliberately suspicious sample instructions.

### Rust helper (independent prototype)

```bash
cd rust/nexa-scriptguard-helper
cargo test
cargo run -- ../../demo_example.sh
```

Rust currently flags only two basic patterns. The Python scanner currently ships **five example regex rules** plus two limited contextual correlations. The previous, broader local alpha is not yet fully synchronized with this repository; the next engineering milestone is to restore and review its remaining rules and tests. The two engines are **not yet integrated**.

## Output formats

```bash
nexa-scriptguard script.sh --view plain
nexa-scriptguard script.sh --redact --html report.html --json report.json --sarif report.sarif
nexa-scriptguard script.sh --fail-on high
```

`--redact` covers only a limited set of credential patterns. Inspect all reports manually before sharing: source instructions and paths may contain sensitive information.

## Security and scope

- **Alpha**, not production ready. No complete Bash parser, interprocedural dataflow or comprehensive malicious-code detection.
- False positives and false negatives are expected. No findings **does not** mean the script is safe.
- Python CLI runs on supported Windows, Linux and macOS; analysis currently targets shell syntax, not PowerShell or other languages.
- The input limit is 5 MiB. Analysis is read-only; verification commands are **not executed**.
- The HTML report is self-contained and escapes source text.

## Quality

GitHub Actions includes Python tests on Windows, macOS and Linux and Rust tests/clippy on Ubuntu. A configured workflow is not evidence that all jobs have passed; check the Actions tab.

## License

MIT. See [LICENSE](LICENSE), [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

**THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.**
