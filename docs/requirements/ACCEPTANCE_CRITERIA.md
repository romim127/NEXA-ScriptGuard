# Acceptance criteria

## Local analyzer

- `.sh` and `.py` inputs are read as data and are never executed or imported.
- Findings use the common model and include locations, severity, confidence,
  evidence, recommendations, status, and limitations.
- Syntax failures and resource limits are visible as incomplete.
- JSON and SARIF satisfy their versioned schemas; HTML escapes untrusted
  content; terminal output neutralizes control characters.
- Default shareable output is redacted, with the original/shared distinction
  preserved.

## GUI

- The local loopback GUI can select an allowed file, analyze it, and display
  result state and findings.
- The interface preserves the approved shield and visual identity.
- JSON, HTML, and SARIF export controls are present.
- Browser-managed download persistence and collision behavior must be tested
  in an ordinary desktop browser before that behavior is certified.

## Release evidence

- CI results must belong to the exact candidate commit.
- Tests on an OS or Python version not run locally must be attributed to CI,
  not to the local environment.
- An unverified SARIF consumer, hard limit, or platform-specific condition
  remains a documented limitation.
