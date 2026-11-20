import datetime as dt
import json
import re
import time
from pathlib import Path

from .contextual import correlated_findings
from .limits import ScanLimits
from .classification import classify_findings
from .model import AnalysisReport, Finding, Location


_RULES = json.loads(Path(__file__).with_name("bash.json").read_text(encoding="utf-8"))
def analyze_compat(source, path, sha256, limits: ScanLimits, deadline):
    text = source.decode("utf-8", errors="replace")
    lines = text.splitlines()
    findings = []
    reasons = []
    for line_number, line in enumerate(lines, 1):
        if time.monotonic() >= deadline:
            reasons.append("Analysis time limit reached during compatibility scanning.")
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for rule in _RULES:
            pattern = rule.get("pattern")
            if not pattern:
                continue
            for match in re.finditer(pattern, line, re.IGNORECASE):
                findings.append(Finding(
                    rule_id=rule["id"],
                    title=rule["title"],
                    severity=rule["severity"],
                    location=Location(line_number, match.start() + 1, line_number, match.end() + 1),
                    instruction=line,
                    explanation=rule["why"],
                    recommendation=rule["recommendation"],
                    verification_commands=rule["checks"],
                    confidence="low",
                    confidence_reason="Legacy regular-expression match on physical line; no syntax parsing.",
                    context_before=lines[max(0, line_number - 3) : line_number - 1],
                    context_after=lines[line_number : min(len(lines), line_number + 2)],
                ))
                if len(findings) >= limits.max_findings:
                    reasons.append(f"Finding limit reached ({limits.max_findings}).")
                    break
            if reasons:
                break
    if time.monotonic() < deadline:
        for item in correlated_findings(lines):
            findings.append(Finding(
                rule_id=item["rule_id"],
                title=item["title"],
                severity=item["severity"],
                location=Location(
                    item["line"], item["column"], item["end_line"],
                    len(lines[item["end_line"] - 1]) + 1,
                ),
                instruction=item["instruction"],
                explanation=item["explanation"],
                recommendation=item["recommendation"],
                verification_commands=item["verification_commands"],
                confidence="low",
                confidence_reason="Legacy text substitution; branch and quoting semantics are not modeled.",
                context_before=item["context_before"],
                context_after=item["context_after"],
                engine="compatibility",
            ))
            if len(findings) >= limits.max_findings:
                reasons.append(f"Finding limit reached ({limits.max_findings}).")
                break
    findings, classification_reasons = classify_findings(
        findings, str(path), sha256, limits
    )
    reasons.extend(classification_reasons)
    return AnalysisReport(
        file_path=str(path),
        sha256=sha256,
        line_count=len(lines),
        findings=findings,
        limitations=[
            "Compatibility heuristics scan physical lines and are not Bash syntax analysis.",
            "Legacy correlation does not model scopes, control flow, or complete shell expansion.",
            "A clean heuristic result does not imply safety.",
        ],
        complete=False,
        incomplete_reasons=list(dict.fromkeys(
            reasons + ["Compatibility mode is heuristic and incomplete by design."]
        )),
        parser="legacy-regex-compatibility",
        analyzed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
