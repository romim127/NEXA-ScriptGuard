import json
import subprocess
from pathlib import Path

from .limits import ScanLimits
from .model import Finding, Location
from .rules import load_rules


class RustIntegrationError(RuntimeError):
    pass


def scan_with_rust(
    executable: Path,
    source: Path,
    digest: str,
    limits: ScanLimits,
    source_data: bytes | None = None,
):
    source_bytes = source_data if source_data is not None else source.read_bytes()
    try:
        completed = subprocess.run(
            [
                str(executable),
                "--protocol",
                "json-v1-stdin",
                str(source),
                digest,
            ],
            input=source_bytes,
            capture_output=True,
            timeout=limits.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RustIntegrationError("Rust helper exceeded its execution timeout") from exc
    except OSError as exc:
        raise RustIntegrationError(f"Unable to start Rust helper: {exc}") from exc
    if len(completed.stdout) > limits.max_output_bytes:
        raise RustIntegrationError("Rust helper response exceeded output limit")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = completed.stderr.decode("utf-8", errors="replace")[:1024]
        raise RustIntegrationError(
            f"Rust helper returned invalid JSON: {message}"
        ) from exc
    if "error" in payload:
        error = payload["error"]
        raise RustIntegrationError(
            f"Rust helper error {error.get('code', 'UNKNOWN')}: "
            f"{error.get('message', 'unspecified error')}"
        )
    if payload.get("schema_version") != "1.0":
        raise RustIntegrationError("Rust helper uses an unsupported protocol version")
    if payload.get("rules_version") != "1.0.0" or payload.get("engine") != "rust":
        raise RustIntegrationError("Rust helper returned incompatible metadata")
    if payload.get("sha256") != digest or payload.get("file") != str(source):
        raise RustIntegrationError("Rust helper response does not match the input")
    if completed.returncode not in (0, 3):
        message = completed.stderr.decode("utf-8", errors="replace")[:1024]
        raise RustIntegrationError(
            f"Rust helper failed with exit code {completed.returncode}: {message}"
        )
    definitions = load_rules()
    findings = []
    for item in payload.get("findings", []):
        rule = definitions.get(item.get("rule_id"))
        if rule is None:
            raise RustIntegrationError(
                f"Rust helper returned unknown rule ID {item.get('rule_id')!r}"
            )
        line = int(item["line"])
        start_column = int(item.get("column", 1))
        end_line = int(item.get("end_line", line))
        end_column = int(item.get("end_column", start_column + 1))
        if (
            item.get("sha256") != digest
            or item.get("file") != str(source)
            or item.get("rule", {}).get("version") != "1.0.0"
        ):
            raise RustIntegrationError("Rust finding metadata does not match the contract")
        findings.append(Finding(
            rule_id=rule.id,
            title=rule.title,
            severity=rule.severity,
            location=Location(line, start_column, end_line, end_column),
            instruction=str(item.get("instruction", "")),
            explanation=rule.explanation,
            recommendation=rule.recommendation,
            verification_commands=list(rule.checks),
            confidence="low",
            confidence_reason=str(item.get("confidence_reason", "Rust supplementary heuristic.")),
            status="requires_review",
            engine="rust",
            evidence_truncated=bool(item.get("evidence_truncated", False)),
        ))
    return findings, bool(payload.get("complete", False))
