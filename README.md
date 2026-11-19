# NEXA ScriptGuard ♾️

Open-source, **experimental** static analysis of shell scripts by NextGenAI Infinity.

> AI assists. Human verifies. Human decides.

## Status
**v0.4.0-alpha — development.** The full Python alpha is being validated for publication. The independent Rust helper is an early prototype, not a complete Bash parser. Findings are leads for human review, not proof of maliciousness.

## Rust helper (experimental)
```bash
cd rust/nexa-scriptguard-helper
cargo test
cargo run -- ../../demo_example.sh
```
The helper reads input only, limits it to 5 MiB, and never executes the inspected script.

## Security
Never run untrusted samples. Review findings and reports before sharing because they may contain sensitive commands or paths. Do not use this prototype as the sole protection for production systems.

## License
MIT.

**THERE IS NO FINAL VERSION. THERE IS ONLY EVOLUTION.**
