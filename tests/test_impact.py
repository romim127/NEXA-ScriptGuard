import tempfile
import unittest
from pathlib import Path

from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.impact import SIGNALS, enrich
from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.python_analysis import python_rules
from nexa_scriptguard.redaction import prepare_report
from nexa_scriptguard.rules import load_rules


class ImpactTests(unittest.TestCase):
    def report(self, text, limits=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_bytes(text.encode("utf-8"))
            return analyze(path, limits)

    def test_catalogs_have_explicit_coverage(self):
        self.assertEqual(set(SIGNALS), set(load_rules()) | {rule["id"] for rule in python_rules()})

    def test_unknown_origin_and_unicode_coordinates(self):
        model = self.report('if True:\r\n\tmessage = "😀"; eval(message)\r\n')
        finding = prepare_report(model.to_dict())["findings"][0]
        impact = finding["impact_analysis"]
        self.assertEqual(impact["coverage"], "syntax")
        self.assertEqual(impact["flows"], [])
        self.assertEqual([resource["id"] for resource in impact["resources"]], ["SYS-13"])
        self.assertEqual(impact["cia"]["availability"]["status"], "not_established")
        span = impact["references"][1]["range"]
        self.assertEqual(finding["evidence"]["shared"][span["start"]:span["end"]], "eval")

    def test_correlated_origin_and_cia(self):
        model = self.report('import requests\neval(requests.get("https://example.invalid").text)\n')
        findings = {finding["rule_id"]: finding for finding in prepare_report(model.to_dict())["findings"]}
        impact = findings["PY-004"]["impact_analysis"]
        self.assertEqual(impact["coverage"], "correlated")
        self.assertEqual([resource["id"] for resource in impact["resources"]], ["SYS-13", "SYS-07"])
        self.assertEqual([boundary["id"] for boundary in impact["boundaries"]], ["TB-02"])
        self.assertEqual(impact["flows"][0]["relationship"], "possible")

    def test_redaction_invalidates_ranges_and_preserves_cia(self):
        model = self.report('eval("api_token=sample-private-value")\napi_token = "sample-private-value"\n')
        report = prepare_report(model.to_dict())
        findings = {finding["rule_id"]: finding for finding in report["findings"]}
        self.assertNotIn("sample-private-value", str(report))
        self.assertIsNone(findings["PY-001"]["impact_analysis"]["references"][1]["range"])
        self.assertEqual(findings["PY-005"]["impact_analysis"]["cia"]["confidentiality"]["status"], "potential")

    def test_truncation_and_deadline_do_not_invent_evidence(self):
        model = self.report('eval("long evidence")\n', ScanLimits(max_evidence_chars=5))
        finding = model.findings[0]
        self.assertIsNone(finding.impact_analysis.references[1].range)
        expired = enrich(finding, model.parser, 0)
        self.assertEqual(expired.coverage, "not_evaluated")
        self.assertEqual(expired.resources, [])

    def test_output_budget_reports_separate_partial_coverage(self):
        report = self.report('eval("1+1")\n', ScanLimits(max_output_bytes=1024))
        self.assertTrue(report.complete)
        self.assertIsNone(report.findings[0].impact_analysis)
        self.assertTrue(any("presupuesto de reporte" in text for text in report.limitations))

    def test_bash_pipeline_order_is_not_inferred_from_node_presence(self):
        source = 'bash | curl https://example.invalid/sample\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.sh"
            path.write_text(source, encoding="utf-8")
            report = analyze(path)
        impact = next(f.impact_analysis for f in report.findings if f.rule_id == "SG-001")
        self.assertEqual(impact.flows[0].relationship, "indeterminate")
        self.assertEqual(impact.boundaries, [])
