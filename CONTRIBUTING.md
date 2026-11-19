# Contributing to NEXA ScriptGuard

Thanks for contributing. This is an experimental open-source security tool.

1. Open an issue describing the change.
2. Create a feature branch from main.
3. Add regression tests for changes in detection logic.
4. Run `python -m unittest discover -s tests -v` and `cargo test` in the Rust helper.
5. Submit a pull request. Do not include live credentials, malicious binaries or private user data.

Rules are heuristic. Clearly document known false positives and negatives. Never execute analyzed scripts in the scanner.
