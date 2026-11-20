import hashlib
from unittest import mock
import json
import tempfile
import unittest
from pathlib import Path

from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.classification import classify_findings
from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.model import Finding, Location
from nexa_scriptguard.redaction import prepare_report
from nexa_scriptguard.reports import (
    render_html,
    render_sarif,
    validate_report,
    validate_sarif,
)
from nexa_scriptguard.rules import load_rules
from nexa_scriptguard.parser import ParserUnavailable, parse_bash


class AnalysisCoreTests(unittest.TestCase):
    def test_compatibility_result_is_never_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(
                "curl https://example.invalid/a | bash\n", encoding="utf-8"
            )
            result = analyze(script, compatibility=True)
        self.assertFalse(result.complete)
        self.assertEqual(result.parser, "legacy-regex-compatibility")
        self.assertTrue(result.findings)
        self.assertTrue(result.findings[0].finding_id)

    def test_parser_failure_is_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text("echo safe\n", encoding="utf-8")
            with mock.patch(
                "nexa_scriptguard.analysis.parse_bash",
                side_effect=ParserUnavailable("parser unavailable"),
            ):
                result = analyze(script)
        self.assertFalse(result.complete)
        self.assertTrue(result.incomplete_reasons)

    def test_json_report_contract_validator_accepts_complete_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text("chmod 777 file\n", encoding="utf-8")
            model = analyze(script)
            report = prepare_report(model.to_dict())
        self.assertTrue(validate_report(report))

    def test_invalid_utf8_is_incomplete_not_clean(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_bytes(b"echo \xff\n")
            result = analyze(script)
        self.assertFalse(result.complete)
        self.assertTrue(result.incomplete_reasons)
        self.assertEqual(result.sha256, hashlib.sha256(b"echo \xff\n").hexdigest())

    def test_ast_and_memory_budgets_are_visible_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text("echo safe\n", encoding="utf-8")
            ast_limited = analyze(
                script, ScanLimits(max_ast_nodes=1)
            )
            memory_limited = analyze(
                script, ScanLimits(max_memory_bytes=1)
            )
        self.assertFalse(ast_limited.complete)
        self.assertFalse(memory_limited.complete)
        self.assertTrue(ast_limited.incomplete_reasons)
        self.assertTrue(memory_limited.incomplete_reasons)

    def test_estimated_memory_budget_stops_rule_matching(self):
        source_data = b"echo safe\n"
        document = parse_bash(source_data, ScanLimits())
        budget = len(source_data) + document.node_count * 128
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_bytes(source_data)
            result = analyze(script, ScanLimits(max_memory_bytes=budget))
        self.assertFalse(result.complete)
        self.assertTrue(any(
            "Estimated analysis memory budget exceeded" in reason
            for reason in result.incomplete_reasons
        ))

    def test_total_evidence_budget_is_shared_across_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(
                "chmod 777 file\nrm -rf tmp\n", encoding="utf-8"
            )
            result = analyze(
                script,
                ScanLimits(max_evidence_chars=100, max_total_evidence_chars=5),
            )
        total_chars = sum(
            len(finding.instruction)
            + sum(map(len, finding.context_before))
            + sum(map(len, finding.context_after))
            for finding in result.findings
        )
        self.assertFalse(result.complete)
        self.assertLessEqual(total_chars, 5)
        self.assertTrue(any("truncated" in item.lower() for item in result.incomplete_reasons))

    def test_dataflow_expansion_limit_is_explicit(self):
        source = (
            "A=curl\n"
            "B=$A$A$A$A$A$A$A$A\n"
            "C=$B$B$B$B$B$B$B$B\n"
            "D=$C$C$C$C$C$C$C$C\n"
            'bash -c "$D"\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(source, encoding="utf-8")
            result = analyze(
                script,
                ScanLimits(max_total_evidence_chars=32),
            )
        self.assertFalse(result.complete)
        self.assertTrue(any(
            "Data-flow expansion character limit reached" in reason
            for reason in result.incomplete_reasons
        ))

    def test_per_finding_evidence_truncation_marks_scan_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text('eval "' + ("x" * 100) + '"\n', encoding="utf-8")
            result = analyze(script, ScanLimits(max_evidence_chars=12))
        self.assertFalse(result.complete)
        self.assertTrue(result.findings[0].evidence_truncated)
        self.assertLessEqual(len(result.findings[0].instruction), 12)
        self.assertTrue(any("truncated" in item.lower() for item in result.incomplete_reasons))

    def test_finding_limit_is_visible_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(
                "chmod 777 file\nrm -fr tmp\neval \"$INPUT\"\n",
                encoding="utf-8",
            )
            result = analyze(script, ScanLimits(max_findings=1))
        self.assertFalse(result.complete)
        self.assertEqual(len(result.findings), 1)
        self.assertTrue(any("Finding limit" in item for item in result.incomplete_reasons))

    def test_time_limit_is_visible_as_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text("echo safe\n", encoding="utf-8")
            result = analyze(script, ScanLimits(timeout_seconds=1e-12))
        self.assertFalse(result.complete)
        self.assertTrue(result.incomplete_reasons)

    def test_redaction_applies_recursively_and_sanitizes_controls(self):
        report = {
            "file": r"C:\Users\synthetic\secret.sh",
            "redaction_applied": False,
            "findings": [{
                "file": r"C:\Users\synthetic\secret.sh",
                "instruction": "Authorization: Bearer synthetic_secret_987\x1b]0;title",
                "evidence": {"original": "token=synthetic_secret_987"},
            }],
        }
        protected = prepare_report(report)
        encoded = json.dumps(protected)
        self.assertNotIn("synthetic_secret_987", encoded)
        self.assertNotIn("\x1b", encoded)
        self.assertEqual(protected["file"], "secret.sh")
        self.assertTrue(protected["redaction_applied"])

    def test_sarif_includes_flow_rule_catalog_and_valid_coordinates(self):
        rules = json.loads(
            Path(__file__).resolve().parents[1]
            .joinpath("nexa_scriptguard", "bash.json")
            .read_text(encoding="utf-8")
        )
        report = {
            "schema_version": "1.0",
            "tool": "NEXA ScriptGuard",
            "version": "0.5.0-alpha",
            "file": "sample.sh",
            "complete": True,
            "analysis_status": "complete",
            "incomplete_reasons": [],
            "context": {"before": [], "after": []},
            "findings": [{
                "id": "test-id",
                "rule_id": "SG-FLOW-001",
                "severity": "CRITICAL",
                "explanation": "possible flow",
                "recommendation": "review",
                "verification_commands": [],
                "limitations": [],
                "confidence": "low",
                "confidence_reason": "static test",
                "status": "requires_review",
                "sha256": "0" * 64,
                "evidence": {"correlation": []},
                "context": {"before": [], "after": []},
                "location": {
                    "start": {"line": 1, "column": 1},
                    "end": {"line": 1, "column": 10},
                },
            }],
        }
        sarif = render_sarif(report, rules)
        validate_sarif(sarif)
        ids = {rule["id"] for rule in sarif["runs"][0]["tool"]["driver"]["rules"]}
        self.assertIn("SG-FLOW-001", ids)
        self.assertEqual(sarif["runs"][0]["results"][0]["ruleId"], "SG-FLOW-001")

    def test_html_escapes_all_source_fields(self):
        report = {
            "complete": True,
            "parser": "tree-sitter-bash",
            "file": "sample.sh",
            "sha256": "0" * 64,
            "findings": [{
                "severity": "HIGH",
                "rule_id": "SG-005",
                "title": "<script>alert(1)</script>",
                "id": "id",
                "location": {
                    "start": {"line": 1, "column": 1},
                    "end": {"line": 1, "column": 10},
                },
                "confidence": "low",
                "confidence_reason": "heuristic",
                "status": "requires_review",
                "sha256": "0" * 64,
                "instruction": "<script>alert(1)</script>",
                "context": {"before": [], "after": []},
                "evidence": {"correlation": []},
                "limitations": [],
                "explanation": "test",
                "recommendation": "review",
                "verification_commands": [],
            }],
        }
        html = render_html(report)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_rule_ids_are_stable_and_unique(self):
        rules = load_rules()
        self.assertEqual(len(rules), len(set(rules)))
        self.assertTrue({"SG-001", "SG-012", "SG-FLOW-001"} <= set(rules))

    def test_classification_marks_truncated_evidence_incomplete(self):
        finding = Finding(
            rule_id="SG-001",
            title="title",
            severity="CRITICAL",
            location=Location(1, 1, 1, 10),
            instruction="x" * 30,
            explanation="why",
            recommendation="review",
            verification_commands=[],
        )
        result, limitations = classify_findings(
            [finding], "sample.sh", "0" * 64,
            ScanLimits(max_evidence_chars=10),
        )
        self.assertTrue(result[0].evidence_truncated)
        self.assertTrue(limitations)
        self.assertLessEqual(len(result[0].instruction), 10)
