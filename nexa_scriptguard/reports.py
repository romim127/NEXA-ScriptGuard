import html
import json
import re
from pathlib import Path
from urllib.parse import quote


def render_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")


def validate_report(report):
    required = {
        "schema_version", "tool", "version", "file", "sha256", "lines",
        "complete", "analysis_status", "incomplete_reasons", "parser",
        "redaction_applied", "findings",
    }
    if not required <= report.keys() or report["schema_version"] != "1.0":
        raise ValueError("Invalid NEXA JSON report schema")
    if not isinstance(report["complete"], bool):
        raise ValueError("Report completeness must be boolean")
    if report["analysis_status"] != (
        "complete" if report["complete"] else "incomplete"
    ):
        raise ValueError("Report status disagrees with completeness")
    if not isinstance(report["findings"], list):
        raise ValueError("Report findings must be an array")
    report_hash = report["sha256"]
    if not isinstance(report_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", report_hash):
        raise ValueError("Report SHA-256 must contain 64 lowercase hexadecimal characters")
    identifiers = set()
    for finding in report["findings"]:
        for key in (
            "id", "rule", "rule_id", "title", "file", "sha256", "location",
            "instruction", "context", "severity", "confidence",
            "confidence_reason", "status", "evidence", "explanation",
            "recommendation", "verification_commands", "limitations",
            "engine",
        ):
            if key not in finding:
                raise ValueError(f"Finding is missing required field: {key}")
        if finding["id"] in identifiers or not finding["id"]:
            raise ValueError("Finding identifiers must be non-empty and unique")
        identifiers.add(finding["id"])
        if finding["rule"]["id"] != finding["rule_id"]:
            raise ValueError("Finding rule metadata is inconsistent")
        if finding["sha256"] != report_hash or finding["file"] != report["file"]:
            raise ValueError("Finding source metadata disagrees with report")
        if finding["severity"] not in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}:
            raise ValueError("Finding severity is not recognized")
        start = finding["location"]["start"]
        end = finding["location"]["end"]
        if min(start["line"], start["column"], end["line"], end["column"]) < 1:
            raise ValueError("Finding locations must use positive one-based coordinates")
        evidence = finding["evidence"]
        if not isinstance(evidence.get("shared"), str):
            raise ValueError("Finding must distinguish shared evidence")
        if report["redaction_applied"] and "original" in evidence:
            raise ValueError("Redacted reports must not contain original evidence")
    return True


def render_sarif(report, rules):
    levels = {
        "CRITICAL": "error",
        "HIGH": "error",
        "MEDIUM": "warning",
        "LOW": "note",
        "INFO": "note",
    }
    descriptors = [
        {
            "id": rule["id"],
            "shortDescription": {"text": rule["title"]},
            "fullDescription": {"text": rule["why"]},
            "defaultConfiguration": {"level": levels[rule["severity"]]},
            "properties": {"version": "1.0.0"},
        }
        for rule in rules
    ]
    results = []
    for finding in report["findings"]:
        location = finding["location"]
        artifact = report["file"].replace("\\", "/")
        if Path(artifact).is_absolute():
            uri = Path(artifact).as_uri()
        else:
            uri = quote(artifact, safe="/.")
        results.append({
            "ruleId": finding["rule_id"],
            "level": levels[finding["severity"]],
            "message": {"text": finding["explanation"]},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {
                        "startLine": location["start"]["line"],
                        "startColumn": location["start"]["column"],
                        "endLine": location["end"]["line"],
                        "endColumn": location["end"]["column"],
                    },
                },
            }],
            "properties": {
                "findingId": finding["id"],
                "sha256": finding["sha256"],
                "severity": finding["severity"],
                "confidence": finding["confidence"],
                "confidenceReason": finding["confidence_reason"],
                "status": finding["status"],
                "evidence": finding["evidence"],
                "context": finding["context"],
                "recommendation": finding["recommendation"],
                "verificationCommands": finding["verification_commands"],
                "limitations": finding["limitations"],
            },
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "columnKind": "unicodeCodePoints",
            "tool": {
                "driver": {
                    "name": report["tool"],
                    "version": report["version"],
                    "rules": descriptors,
                },
            },
            "results": results,
            "properties": {
                "schemaVersion": report["schema_version"],
                "analysisStatus": report["analysis_status"],
                "incompleteReasons": report["incomplete_reasons"],
            },
        }],
    }


def validate_sarif(value):
    if (
        value.get("$schema") != "https://json.schemastore.org/sarif-2.1.0.json"
        or value.get("version") != "2.1.0"
        or not isinstance(value.get("runs"), list)
    ):
        raise ValueError("Invalid SARIF 2.1.0 top-level shape")
    for run in value["runs"]:
        driver = run["tool"]["driver"]
        driver_rules = {item["id"] for item in driver["rules"]}
        if len(driver_rules) != len(driver["rules"]):
            raise ValueError("SARIF driver rule IDs must be unique")
        for result in run["results"]:
            if result["ruleId"] not in driver_rules:
                raise ValueError(f"SARIF result has no rule descriptor: {result['ruleId']}")
            if result.get("level") not in {"error", "warning", "note", "none"}:
                raise ValueError("SARIF result level is invalid")
            if not isinstance(result.get("message", {}).get("text"), str):
                raise ValueError("SARIF result message is required")
            region = result["locations"][0]["physicalLocation"]["region"]
            if min(region["startLine"], region["startColumn"]) < 1:
                raise ValueError("SARIF locations must use positive one-based coordinates")
            if region.get("endLine", region["startLine"]) < region["startLine"]:
                raise ValueError("SARIF end line cannot precede start line")


def render_html(report):
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    colors = {
        "CRITICAL": "#ff3e51", "HIGH": "#ff765c", "MEDIUM": "#ffc36e",
        "LOW": "#40d5ed", "INFO": "#98a6c8",
    }
    for finding in report["findings"]:
        checks = "".join(
            "<li><code>" + esc(command) + "</code></li>"
            for command in finding["verification_commands"]
        )
        location = finding["location"]
        before = "".join(
            "<p><code>" + esc(line) + "</code></p>"
            for line in finding["context"]["before"]
        )
        after = "".join(
            "<p><code>" + esc(line) + "</code></p>"
            for line in finding["context"]["after"]
        )
        cards.append(f"""<article class="finding" style="--sev:{colors[finding['severity']]}">
          <h2>⚠ {esc(finding['severity'])} · {esc(finding['rule_id'])} · {esc(finding['title'])}</h2>
          <p>Hallazgo {esc(finding['id'])} · LÍNEA {location['start']['line']} · COLUMNA {location['start']['column']}</p>
          <p>SHA-256 {esc(finding['sha256'])} · CONFIANZA {esc(finding['confidence'])} · ESTADO {esc(finding['status'])}</p>
          <p>{esc(finding['confidence_reason'])}</p>
          <h3>INSTRUCCIÓN</h3><pre>{esc(finding['instruction'])}</pre>
          <h3>CONTEXTO</h3><div>{before}<strong>Instrucción correlacionada:</strong>{after}</div>
          <h3>FLUJO / CORRELACIÓN</h3><pre>{esc(json.dumps(finding['evidence']['correlation'], ensure_ascii=False))}</pre>
          <h3>ANÁLISIS</h3><p>{esc(finding['explanation'])}</p>
          <h3>RECOMENDACIÓN</h3><p>{esc(finding['recommendation'])}</p>
          <h3>VERIFICACIÓN — NO EJECUTADA</h3><ul>{checks}</ul>
          <p>Limitaciones: {esc('; '.join(finding['limitations']))}</p></article>""")
    findings = "\n".join(cards) or "<p>Sin coincidencias; esto no garantiza seguridad.</p>"
    status = "COMPLETO" if report["complete"] else "INCOMPLETO"
    return f"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>NEXA ScriptGuard</title><style>
    body{{background:radial-gradient(ellipse at top,#211039,#050912 65%);color:#f5f7ff;font:15px/1.6 system-ui,sans-serif;margin:0}}
    main{{max-width:1080px;margin:auto;padding:35px}}header{{border-bottom:1px solid #00d9ff;padding:24px 0}}
    h1{{font-size:42px;color:#00d9ff}}.finding{{border:1px solid var(--sev);box-shadow:0 0 14px var(--sev);border-radius:18px;padding:22px;margin:25px 0;background:#080e1b}}
    h2{{color:var(--sev)}}h3{{color:#00d9ff;font-size:13px;letter-spacing:.1em}}
    pre{{background:#020711;border:1px solid #00b9ef;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;border-radius:9px}}
    </style><main><header><h1>♾ NEXA ScriptGuard</h1><p>NextGenAI Infinity · AI assists. Human verifies. Human decides.</p></header>
    <p>Estado: {status} · Archivo: {esc(report['file'])} · SHA-256: {esc(report['sha256'])}</p>
    <p>Parser: {esc(report['parser'])} · Hallazgos: {len(report['findings'])}</p>
    {findings}<p>Las verificaciones no se ejecutan. Los hallazgos requieren revisión humana.</p></main></html>"""


def render_terminal(report, console):
    from rich import box
    from rich.panel import Panel
    from rich.text import Text

    banner = Text("∞ NEXA SCRIPTGUARD", style="bold bright_cyan", justify="center")
    banner.append("\nNEXTGENAI INFINITY", style="bright_magenta")
    banner.append("\nAI assists. Human verifies. Human decides.", style="italic white")
    console.print(Panel(banner, border_style="bright_cyan", box=box.DOUBLE))
    state = "COMPLETO" if report["complete"] else "INCOMPLETO"
    console.print(Text(
        f"ESTADO {state}\nARCHIVO {report['file']}\nSHA-256 {report['sha256']}\n"
        f"HALLAZGOS {len(report['findings'])}",
        style="cyan",
    ))
    colors = {"CRITICAL": "bright_red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "cyan", "INFO": "white"}
    for finding in report["findings"]:
        text = Text()
        text.append(
            f"{finding['severity']} · {finding['rule_id']} · {finding['title']}\n",
            style="bold",
        )
        text.append(
            f"{finding['location']['start']['line']}:{finding['location']['start']['column']} · "
            f"{finding['confidence']} · {finding['status']} · ID {finding['id']}\n",
            style="bright_cyan",
        )
        text.append(f"SHA-256 {finding['sha256']}\n{finding['confidence_reason']}\n\n")
        for label, value in (
            ("INSTRUCCIÓN", finding["instruction"]),
            ("ANÁLISIS", finding["explanation"]),
            ("RECOMENDACIÓN", finding["recommendation"]),
        ):
            text.append(label + "\n", style="bold bright_cyan")
            text.append(value + "\n\n")
        correlation = finding["evidence"]["correlation"]
        if correlation:
            text.append("EVIDENCIA DE FLUJO\n", style="bold bright_cyan")
            for step in correlation:
                text.append(json.dumps(step, ensure_ascii=False) + "\n")
        if finding["context"]["before"] or finding["context"]["after"]:
            text.append("CONTEXTO\n", style="bold bright_cyan")
            for line in finding["context"]["before"] + finding["context"]["after"]:
                text.append(line + "\n")
        text.append(
            "LIMITACIONES\n" + "; ".join(finding["limitations"]) + "\n",
            style="yellow",
        )
        text.append("VERIFICACIONES — NO EJECUTADAS\n", style="bright_cyan")
        for command in finding["verification_commands"]:
            text.append("• " + command + "\n")
        console.print(Panel(text, border_style=colors[finding["severity"]], box=box.DOUBLE))
    for reason in report["incomplete_reasons"]:
        console.print(Text("ANÁLISIS INCOMPLETO: " + reason, style="bold yellow"))
