import hashlib

from .limits import ScanLimits
from .model import Finding
from .rules import SEVERITY_ORDER


def classify_findings(findings: list[Finding], file_path: str, sha256: str,
                      limits: ScanLimits):
    seen = set()
    result = []
    incomplete = []
    ordered = sorted(
        findings,
        key=lambda item: (
            -SEVERITY_ORDER.get(item.severity, 0),
            item.location.start_line,
            item.location.start_column,
            item.rule_id,
        ),
    )
    remaining_evidence = limits.max_total_evidence_chars
    for finding in ordered:
        identity = (
            finding.rule_id,
            finding.location.start_line,
            finding.location.start_column,
            finding.location.end_line,
            finding.location.end_column,
        )
        if identity in seen:
            continue
        seen.add(identity)
        if len(result) >= limits.max_findings:
            incomplete.append(f"Finding limit reached ({limits.max_findings}).")
            break
        if finding.evidence_truncated:
            incomplete.append(
                f"Evidence was truncated for {finding.rule_id} at "
                f"{finding.location.start_line}:{finding.location.start_column}."
            )
        per_finding_remaining = limits.max_evidence_chars

        def bound_evidence(value):
            nonlocal remaining_evidence, per_finding_remaining
            budget = min(per_finding_remaining, remaining_evidence)
            if len(value) > budget:
                marker = "[TRUNCATED]"
                if len(marker) > budget:
                    marker = marker[:budget]
                value = value[: max(0, budget - len(marker))] + marker
                finding.evidence_truncated = True
            used = min(len(value), budget)
            per_finding_remaining -= used
            remaining_evidence -= used
            return value

        original_instruction = finding.instruction
        finding.instruction = bound_evidence(finding.instruction)
        if finding.instruction != original_instruction:
            incomplete.append(
                f"Evidence truncated for {finding.rule_id} at "
                f"{finding.location.start_line}:{finding.location.start_column}."
            )
        for field in ("context_before", "context_after"):
            sanitized = []
            for line in getattr(finding, field):
                if per_finding_remaining <= 0 or remaining_evidence <= 0:
                    finding.evidence_truncated = True
                    incomplete.append(
                        f"Context truncated for {finding.rule_id} at "
                        f"{finding.location.start_line}:{finding.location.start_column}."
                    )
                    break
                bounded = bound_evidence(line)
                if bounded != line:
                    sanitized.append(bounded)
                    finding.evidence_truncated = True
                    incomplete.append(
                        f"Context truncated for {finding.rule_id} at "
                        f"{finding.location.start_line}:{finding.location.start_column}."
                    )
                    break
                sanitized.append(bounded)
            setattr(finding, field, sanitized)
        stable = "|".join((
            finding.rule_id,
            file_path,
            sha256,
            str(finding.location.start_line),
            str(finding.location.start_column),
            str(finding.location.end_line),
            str(finding.location.end_column),
        ))
        finding.finding_id = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]
        result.append(finding)
    return result, list(dict.fromkeys(incomplete))
