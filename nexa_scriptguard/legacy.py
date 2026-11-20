import datetime as dt
import hashlib
import html
import re
from pathlib import Path

from .contextual import correlated_findings
_SEVERITY = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def inspect(target, rules):
    with target.open("rb") as stream:
        data = stream.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("Input exceeds the 5 MiB limit")
    lines = data.decode("utf-8", errors="replace").splitlines()
    findings = []
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for rule in rules:
            if "pattern" not in rule:
                continue
            for match in re.finditer(rule["pattern"], line, re.IGNORECASE):
                findings.append({
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "title": rule["title"],
                    "line": number,
                    "column": match.start() + 1,
                    "instruction": line,
                    "matched_fragment": match.group(0),
                    "explanation": rule["why"],
                    "recommendation": rule["recommendation"],
                    "verification_commands": rule["checks"],
                    "confidence": "heuristic",
                    "status": "requires_review",
                    "context_before": lines[max(0, number - 3) : number - 1],
                    "context_after": lines[number : min(len(lines), number + 2)],
                })
    findings.extend(correlated_findings(lines))
    findings.sort(key=lambda item: (
        -_SEVERITY[item["severity"]], item["line"], item["column"]
    ))
    return {
        "tool": "NEXA ScriptGuard",
        "version": "0.4.0-alpha",
        "analyzed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "file": str(target),
        "sha256": hashlib.sha256(data).hexdigest(),
        "lines": len(lines),
        "findings": findings,
        "limitations": "Compatibility heuristics; not a Bash parser. No findings do not prove safety.",
    }


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for finding in report["findings"]:
        cards.append(
            "<article><h2>"
            + esc(finding["severity"]) + " · " + esc(finding["rule_id"])
            + "</h2><pre>" + esc(finding["instruction"]) + "</pre><p>"
            + esc(finding["explanation"]) + "</p></article>"
        )
    return (
        "<!doctype html><html lang=\"es\"><meta charset=\"utf-8\"><title>NEXA ScriptGuard</title>"
        "<main><h1>♾ NEXA ScriptGuard</h1><p>Archivo: "
        + esc(report["file"]) + " · SHA-256: " + esc(report["sha256"])
        + "</p>" + ("".join(cards) or "<p>Sin coincidencias; no garantiza seguridad.</p>")
        + "</main></html>"
    )


def render_sarif(report, rules):
    levels = {"CRITICAL": "error", "HIGH": "error", "MEDIUM": "warning", "LOW": "note", "INFO": "note"}
    findings = []
    for item in report["findings"]:
        findings.append({
            "ruleId": item["rule_id"],
            "level": levels[item["severity"]],
            "message": {"text": item["explanation"]},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": Path(report["file"]).as_uri()},
                    "region": {"startLine": item["line"], "startColumn": item["column"]},
                },
            }],
            "properties": {"confidence": item["confidence"]},
        })
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": report["tool"],
                    "version": report["version"],
                    "rules": [
                        {"id": rule["id"], "shortDescription": {"text": rule["title"]}}
                        for rule in rules
                    ],
                },
            },
            "results": findings,
        }],
    }
