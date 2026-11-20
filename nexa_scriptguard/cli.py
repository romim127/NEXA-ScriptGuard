import argparse
import io
import json
import os
import sys
from pathlib import Path

from .analysis import analyze
from .ingestion import InputError, OutputError, read_source, write_reports
from .limits import ScanLimits
from .redaction import prepare_report
from .reports import (
    render_html,
    render_json,
    render_sarif,
    render_terminal,
    rules_for_report,
    validate_report,
    validate_sarif,
)
from .rules import RULES_PATH


def _limits(args):
    return ScanLimits(
        max_input_bytes=args.max_input_bytes,
        max_findings=args.max_findings,
        max_evidence_chars=args.max_evidence_chars,
        max_total_evidence_chars=args.max_total_evidence_chars,
        max_output_bytes=args.max_output_bytes,
        max_memory_bytes=args.max_memory_bytes,
        timeout_seconds=args.timeout_seconds,
        max_ast_nodes=args.max_ast_nodes,
    )


def _make_parser():
    parser = argparse.ArgumentParser(
        description="Read-only static Bash and Python analyzer; inspected scripts are never executed."
    )
    parser.add_argument("script", type=Path)
    for output_format in ("json", "html", "sarif"):
        parser.add_argument("--" + output_format, dest=output_format + "_path", type=Path)
    parser.add_argument("--view", choices=("neon", "plain"), default="neon")
    parser.add_argument("--fail-on", choices=("critical", "high", "medium", "low"))
    parser.add_argument(
        "--compat-heuristics",
        action="store_true",
        help="Use identified legacy regex heuristics instead of the Bash parser.",
    )
    parser.add_argument(
        "--rust-helper",
        type=Path,
        help="Run the independent Rust helper using the json-v1 process contract.",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Explicitly redact secrets and user paths in every output (default).",
    )
    parser.add_argument(
        "--include-sensitive-evidence",
        dest="redact",
        action="store_false",
        help="Opt out of best-effort secret and path redaction; terminal controls remain escaped.",
    )
    parser.set_defaults(redact=True)
    parser.add_argument("--max-input-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--max-findings", type=int, default=2_000)
    parser.add_argument("--max-evidence-chars", type=int, default=4_096)
    parser.add_argument(
        "--max-total-evidence-chars",
        type=int,
        default=8 * 1024 * 1024,
    )
    parser.add_argument("--max-output-bytes", type=int, default=20 * 1024 * 1024)
    parser.add_argument("--max-memory-bytes", type=int, default=128 * 1024 * 1024)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-ast-nodes", type=int, default=250_000)
    return parser


def main(argv=None):
    parser = _make_parser()
    args = parser.parse_args(argv)
    try:
        limits = _limits(args)
    except ValueError as exc:
        parser.error(str(exc))

    output_paths = [
        path for path in (args.json_path, args.html_path, args.sarif_path)
        if path is not None
    ]
    try:
        destination_keys = []
        for path in output_paths:
            parent = path.expanduser().parent.resolve(strict=True)
            destination_keys.append(os.path.normcase(str(parent / path.name)))
        if len(destination_keys) != len(set(destination_keys)):
            raise OutputError("Report output paths must be distinct")
        source = read_source(args.script, limits)
        rust_helper = (
            args.rust_helper.expanduser().resolve(strict=True)
            if args.rust_helper is not None else None
        )
        report_model = analyze(
            source.path,
            limits,
            compatibility=args.compat_heuristics,
            rust_helper=rust_helper,
            source=source,
        )
        report = prepare_report(report_model.to_dict(), args.redact)
        validate_report(report)
        rendered = {}
        if args.json_path:
            rendered[args.json_path] = render_json(report)
        if args.html_path:
            rendered[args.html_path] = render_html(report).encode("utf-8")
        if args.sarif_path:
            rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
            sarif = render_sarif(report, rules_for_report(report, rules))
            validate_sarif(sarif)
            rendered[args.sarif_path] = json.dumps(
                sarif, ensure_ascii=False, indent=2
            ).encode("utf-8")
        for output_path, content in rendered.items():
            if len(content) > limits.max_output_bytes:
                raise OutputError(
                    f"Report {output_path} exceeds the {limits.max_output_bytes}-byte limit"
                )
        terminal_output = ""
        if args.view == "neon":
            from rich.console import Console

            buffer = io.StringIO()
            render_terminal(
                report,
                Console(file=buffer, highlight=False, force_terminal=False),
            )
            terminal_output = buffer.getvalue()
        else:
            state = "complete" if report["complete"] else "INCOMPLETE"
            rows = [
                f"NEXA ScriptGuard | {report['file']} | {state}",
                f"SHA-256 {report['sha256']} | {len(report['findings'])} finding(s)",
            ]
            for finding in report["findings"]:
                rows.append(
                    f"[{finding['severity']}] {finding['rule_id']} "
                    f"L{finding['line']}:C{finding['column']} "
                    f"{finding['confidence']} {finding['status']} ID {finding['id']} "
                    f"{finding['instruction']}"
                )
                rows.append("  " + finding["explanation"])
                rows.append("  " + finding["recommendation"])
                rows.extend(
                    "  Verify (not executed): " + command
                    for command in finding["verification_commands"]
                )
                rows.extend(
                    "  Flow: " + json.dumps(item, ensure_ascii=False)
                    for item in finding["evidence"]["correlation"]
                )
            rows.extend(
                "ANALYSIS INCOMPLETE: " + reason
                for reason in report["incomplete_reasons"]
            )
            terminal_output = "\n".join(rows) + "\n"
        terminal_bytes = terminal_output.encode("utf-8")
        if len(terminal_bytes) > limits.max_output_bytes:
            raise OutputError(
                f"Terminal output exceeds the {limits.max_output_bytes}-byte limit"
            )
        if rendered:
            write_reports(rendered, source, limits)
        sys.stdout.write(terminal_output)
        if not report["complete"]:
            return 3
        if args.fail_on and any(
            {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(
                finding["severity"], 0
            )
            >= {"critical": 4, "high": 3, "medium": 2, "low": 1}[args.fail_on]
            for finding in report["findings"]
        ):
            return 2
        return 0
    except (InputError, OutputError, OSError, ValueError) as exc:
        print(f"NEXA ScriptGuard error: {exc}", file=sys.stderr)
        return 4
