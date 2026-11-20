import datetime as dt
import hashlib
import time
from dataclasses import replace
from pathlib import Path

from .classification import classify_findings
from .compat import analyze_compat
from .dataflow import analyze_dataflow
from .ingestion import Source, read_source
from .limits import ScanLimits
from .model import AnalysisReport
from .parser import ParseLimitError, ParserUnavailable, parse_bash
from .rules import analyze_rules, load_rules
from .rust_bridge import RustIntegrationError, scan_with_rust


def _empty_report(source: Source, digest, parser, reason):
    line_count = len(source.data.decode("utf-8", errors="replace").splitlines())
    return AnalysisReport(
        file_path=str(source.path),
        sha256=digest,
        line_count=line_count,
        findings=[],
        limitations=["Analysis could not complete; no clean result is implied."],
        complete=False,
        incomplete_reasons=[reason],
        parser=parser,
        analyzed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    )


def analyze(
    path: Path,
    limits: ScanLimits | None = None,
    compatibility=False,
    rust_helper: Path | None = None,
    source: Source | None = None,
):
    limits = limits or ScanLimits()
    started = time.monotonic()
    deadline = started + limits.timeout_seconds
    source = source or read_source(path, limits)
    digest = hashlib.sha256(source.data).hexdigest()

    extension = source.path.suffix.lower()
    if extension not in {".sh", ".py"}:
        raise ValueError("Unsupported file type; expected .sh or .py.")
    if len(source.data) > limits.max_memory_bytes:
        return _empty_report(
            source, digest, "not-started",
            f"Input size exceeds the configured memory budget ({limits.max_memory_bytes} bytes).",
        )
    if extension == ".py":
        if compatibility:
            raise ValueError("Bash compatibility mode is not available for Python files.")
        from .python_analysis import analyze_python

        report = analyze_python(source, digest, limits, deadline)
        if rust_helper is not None:
            report.limitations.append("Rust helper supports Bash signals only and was not used for Python.")
        return report
    if compatibility:
        report = analyze_compat(source.data, source.path, digest, limits, deadline)
        report.incomplete_reasons.append("Compatibility mode does not use a Bash parser.")
        if rust_helper is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                report.incomplete_reasons.append("No execution time remained for Rust helper.")
            else:
                try:
                    findings, complete = scan_with_rust(
                        rust_helper,
                        source.path,
                        digest,
                        replace(limits, timeout_seconds=remaining),
                        source.data,
                    )
                    report.findings.extend(findings)
                    classified, more_reasons = classify_findings(
                        report.findings, str(source.path), digest, limits
                    )
                    report.findings = classified
                    report.incomplete_reasons.extend(more_reasons)
                    if not complete:
                        report.incomplete_reasons.append(
                            "Rust helper reported an incomplete scan."
                        )
                except RustIntegrationError as exc:
                    report.incomplete_reasons.append(str(exc))
            report.incomplete_reasons = list(dict.fromkeys(report.incomplete_reasons))
        return report

    try:
        document = parse_bash(source.data, limits)
    except ParserUnavailable as exc:
        report = _empty_report(source, digest, "unavailable", str(exc))
        if rust_helper is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                report.incomplete_reasons.append(
                    "No execution time remained for Rust helper."
                )
            else:
                try:
                    findings, complete = scan_with_rust(
                        rust_helper,
                        source.path,
                        digest,
                        replace(limits, timeout_seconds=remaining),
                        source.data,
                    )
                    report.findings = findings
                    classified, more_reasons = classify_findings(
                        report.findings, str(source.path), digest, limits
                    )
                    report.findings = classified
                    report.incomplete_reasons.extend(more_reasons)
                    if not complete:
                        report.incomplete_reasons.append(
                            "Rust helper reported an incomplete scan."
                        )
                except RustIntegrationError as rust_error:
                    report.incomplete_reasons.append(str(rust_error))
            report.incomplete_reasons = list(dict.fromkeys(report.incomplete_reasons))
        return report
    except ParseLimitError as exc:
        return _empty_report(source, digest, "tree-sitter-bash", str(exc))
    except ValueError as exc:
        return _empty_report(source, digest, "tree-sitter-bash", str(exc))

    estimated_memory = len(source.data) + document.node_count * 256
    memory_limited = estimated_memory > limits.max_memory_bytes
    if memory_limited:
        return _empty_report(
            source,
            digest,
            document.parser_name,
            "Estimated analysis memory budget exceeded "
            f"({estimated_memory} > {limits.max_memory_bytes} bytes); "
            "parser native allocations cannot be hard-limited.",
        )
    source_text = source.data.decode("utf-8")
    lines = source_text.splitlines()
    rules = load_rules()
    raw_findings, limitations = analyze_rules(
        document, rules, lines, deadline, limits
    )
    flow_findings, flow_limitations = analyze_dataflow(
        document, rules, lines, deadline, limits
    )
    raw_findings.extend(flow_findings)
    limitations.extend(flow_limitations)
    if rust_helper is not None:
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RustIntegrationError("No execution time remained for Rust helper")
            rust_findings, rust_complete = scan_with_rust(
                rust_helper, source.path, digest,
                replace(limits, timeout_seconds=remaining),
                source.data,
            )
            python_lines = {
                (finding.rule_id, finding.location.start_line)
                for finding in raw_findings
            }
            raw_findings.extend(
                finding for finding in rust_findings
                if (finding.rule_id, finding.location.start_line) not in python_lines
            )
            if not rust_complete:
                limitations.append("Rust helper reported an incomplete scan.")
        except RustIntegrationError as exc:
            limitations.append(str(exc))
    if document.errors:
        limitations.append(
            f"Bash parser reported {len(document.errors)} syntax error or missing node(s)."
        )
    if document.node_count > limits.max_ast_nodes:
        limitations.append(f"AST node limit reached ({limits.max_ast_nodes}).")
    classified, classify_limitations = classify_findings(
        raw_findings, str(source.path), digest, limits
    )
    limitations.extend(classify_limitations)
    incomplete = list(dict.fromkeys(limitations))
    report = AnalysisReport(
        file_path=str(source.path),
        sha256=digest,
        line_count=len(lines),
        findings=classified,
        limitations=[
            "tree-sitter-bash parses syntax but does not model all runtime expansion, sourced files, or external commands.",
            "Findings are static indicators; they do not prove execution or malicious intent.",
            "Memory budget is an estimate; parser native allocations cannot be hard-limited by this process.",
        ],
        complete=not incomplete,
        incomplete_reasons=incomplete,
        parser=document.parser_name,
        analyzed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
    )
    if time.monotonic() >= deadline:
        report.complete = False
        report.incomplete_reasons.append(
            "Analysis deadline exceeded; parser execution itself is not preemptible."
        )
    return report
