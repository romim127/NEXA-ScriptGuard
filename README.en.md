# ♾ NEXA ScriptGuard

**NextGenAI Infinity** · *AI assists. Human verifies. Human decides.*

NEXA ScriptGuard is an experimental static analyzer for Bash and Python scripts. It does not execute or import the inspected file or execute investigation commands it recommends. A clean analysis **does not** prove a script is safe.

## Installation

Requires Python 3.10 or later. The package installs the Tree-sitter runtime and official Bash grammar:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

On Linux/macOS, activate with `source .venv/bin/activate`. The [`tree-sitter-bash`](https://github.com/tree-sitter/tree-sitter-bash) grammar is MIT licensed; its Python binding publishes wheels for Windows, Linux, and macOS. It provides syntax trees and source positions, but does not model all Bash semantics or evaluate expansions.

## Usage

### Local graphical interface on Windows

From the repository root, after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m nexa_scriptguard.gui
```

The browser opens automatically; otherwise use the private URL printed in the console. Select a `.sh` or `.py` file, click **Analizar archivo**, and review the detected language, status, redacted evidence and recommendations. JSON, HTML and SARIF are offered as browser downloads. The analyzer does not execute the script and preserves incomplete status. Keep the console open; `Ctrl+C` stops the server.

The server binds only to `127.0.0.1` on a random port and uses a session token: do not share the URL or console. Only the latest result is retained; if another tab runs a scan, the previous tab must scan again to export. The browser chooses the download location and handles name collisions; CLI no-overwrite guarantees do not apply to downloads. Redaction is best-effort, not a guarantee. The GUI uses the default budgets described below; time and memory are not hard quotas. An optional trusted Rust executable can be enabled using `--rust-helper`.

### Command line

```text
python -m nexa_scriptguard script.sh --view plain --json report.json
python -m nexa_scriptguard script.sh --html report.html --sarif report.sarif
python -m nexa_scriptguard script.sh --fail-on high
python -m nexa_scriptguard script.py --json report.json --sarif report.sarif
```

Report destinations must be new. NEXA does not replace existing files; each destination is atomically created without overwrite, but publishing multiple formats is not a transaction across abrupt process or system failure. Create the reports directory first.

Best-effort secret and sensitive-path redaction is enabled by default for terminal and file outputs. `--include-sensitive-evidence` is an explicit opt-out; terminal control characters remain escaped. Even a redacted report retains a SHA-256 hash that can be correlated with a known file. Review reports before sharing.

Configure limits with `--max-input-bytes`, `--max-findings`, `--max-evidence-chars`, `--max-total-evidence-chars`, `--max-output-bytes`, `--max-memory-bytes`, `--max-ast-nodes`, and `--timeout-seconds`. Tree-sitter parsing cannot be preempted; the memory budget is an estimate, not a hard cap on native allocations. Reaching a limit, a parse error, or a missing parser yields `analysis_status: incomplete` and exit code `3`, never a clean result.

## Compatibility and Rust

`--compat-heuristics` explicitly enables the previous regex heuristics; the result is labeled `legacy-regex-compatibility` and is always incomplete. The Rust helper is an optional independent process:

```powershell
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
python -m nexa_scriptguard script.sh --rust-helper rust\nexa-scriptguard-helper\target\debug\nexa-scriptguard-helper.exe
```

Python sends the already bounded Bash input bytes over `stdin`; Rust returns findings using JSON protocol `1.0` / `json-v1-stdin`. Both engines therefore use the same snapshot and hash without a temporary copy of user input. Rust supports only SG-001 and SG-002 line-level signals; it does not share the Python parser or data-flow analysis. It is not applied to `.py` files.

## Current scope

Bash commands are parsed with the Tree-sitter grammar; the [rule catalog](docs/RULES.md) is applied and selected literal assignments and multi-hop variables are correlated with pipelines/interpreters and file uploads. Flows are labeled possible or indeterminate, not proof of execution.

The analyzer does not fully model expansions, environment values, `source`, every scope, branch, external command, operating-system behavior, or dynamic syntax. Tree-sitter syntax errors and constructs it cannot parse mark analysis incomplete; accepted syntax may still require human review.

For `.py` files, the standard-library `ast` parser uses the running Python version. Eight initial AST rules use limited alias resolution and local approximate network correlation; they do not model all scopes, branches, types, libraries, indirect calls or data flow. Syntax errors and budget exhaustion are reported as incomplete. AST parsing is not preemptible by the cooperative timeout.

## Security, architecture, and contribution

- [Architecture and limits](docs/ARCHITECTURE.md)
- [Rule catalog](docs/RULES.md)
- [Ollama installer procedure](docs/Ollama-analysis.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture, requirements, and governance map](docs/architecture/PROJECT_TREE.md)
- [Vercel evaluation decision](docs/decisions/ADR-0003-VERCEL-EVALUATION.md) — documentation only; no hosted service or deployment exists.
- [Consolidation and pending work report](docs/reports/NEXA_SCRIPTGUARD_CONSOLIDATION_REPORT.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [README en español](README.md)

Do not execute `demo_example.sh`; it contains deliberately suspicious instructions. Analyze it only as text.

## Quality

Install test dependencies with `python -m pip install ".[test]"`, then run `python -m unittest discover -s tests -v` and the Rust `cargo test`/`cargo clippy` commands. Schema tests fetch the official SARIF schema over HTTPS and verify its hash; set `NEXA_SARIF_SCHEMA_PATH` to an identical local copy for offline validation. The NEXA JSON report uses its own versioned schema, not an external standard. CI declares Windows, Linux, and macOS jobs. Workflow configuration alone does not demonstrate that every remote run passed.

**THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.**
