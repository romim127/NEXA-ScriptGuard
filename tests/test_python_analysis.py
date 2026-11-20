import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nexa_scriptguard.analysis import analyze
from nexa_scriptguard.ingestion import Source
from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.python_analysis import python_rules
from nexa_scriptguard.redaction import prepare_report
from nexa_scriptguard.reports import render_html, render_sarif, rules_for_report, validate_report, validate_sarif
from nexa_scriptguard.rules import RULES_PATH


def scan(text, limits=None, name="example.py"):
    source = Source(Path(name), text.encode("utf-8"), -1, -1)
    return analyze(source.path, limits, source=source)


class PythonAnalysisTests(unittest.TestCase):
    def test_rules_positive_negative_and_aliases(self):
        examples = {
            "PY-001": ("exec('x')", "def exec(x): pass\nexec('x')"),
            "PY-002": ("import subprocess as sp\nsp.run('x', shell=True)", "import subprocess as sp\nsp.run(['x'], shell=False)"),
            "PY-003": ("from pickle import loads as decode\ndecode(data)", "obj.loads(data)"),
            "PY-004": ("import requests as r\nexec(r.get(url).text)", "exec('print(1)')"),
            "PY-005": ("API_TOKEN = 'fake_example_value'", "api_token = os.environ.get('TOKEN')"),
            "PY-006": ("from os import system as run\nrun('x')", "other.system('x')"),
            "PY-007": ("cursor.execute(f'SELECT {value}')", "cursor.execute('SELECT ?', (value,))"),
            "PY-008": ("import requests as r\nr.get(url, verify=False)", "import requests as r\nr.get(url, verify=True)"),
        }
        bash_ids = {item["id"] for item in json.loads(RULES_PATH.read_text(encoding="utf-8"))}
        self.assertFalse(bash_ids & {item["id"] for item in python_rules()})
        for rule, (positive, negative) in examples.items():
            with self.subTest(rule=rule):
                result = scan(positive)
                self.assertTrue(result.complete, result.incomplete_reasons)
                self.assertIn(rule, {f.rule_id for f in result.findings})
                self.assertNotIn(rule, {f.rule_id for f in scan(negative).findings})

    def test_alias_shadowing_is_not_resolved_as_library(self):
        text = "import subprocess as sp\nsp = custom\nsp.run('x', shell=True)\n"
        self.assertNotIn("PY-002", {f.rule_id for f in scan(text).findings})
        text = "def f(eval):\n    eval('x')\n"
        self.assertNotIn("PY-001", {f.rule_id for f in scan(text).findings})

    def test_network_assignment_and_reassignment(self):
        common = "import requests\nx = requests.get(url).text\n"
        result = scan(common + "exec(x)\n")
        correlation = next(f.correlation for f in result.findings if f.rule_id == "PY-004")
        self.assertEqual(correlation[0]["relationship"], "possible")
        self.assertEqual(correlation[0]["source"]["location"]["start"]["line"], 2)
        self.assertNotIn("PY-004", {f.rule_id for f in scan(common + "x = 'fixed'\nexec(x)\n").findings})

    def test_unicode_positions_and_empty_file(self):
        result = scan("é = 1; eval('x')\n")
        finding = next(f for f in result.findings if f.rule_id == "PY-001")
        self.assertEqual(finding.location.start_column, 8)
        self.assertTrue(scan("").complete)

    def test_errors_budgets_and_timeout_are_incomplete(self):
        self.assertFalse(scan("def broken(:").complete)
        self.assertFalse(scan("eval('x')", ScanLimits(max_ast_nodes=1)).complete)
        self.assertFalse(scan("eval('x')", ScanLimits(max_memory_bytes=1)).complete)
        with mock.patch("time.monotonic", side_effect=[0, 10, 10]):
            self.assertFalse(scan("x = 1", ScanLimits(timeout_seconds=10)).complete)
        limited = scan("eval('123456789012345')", ScanLimits(max_evidence_chars=5))
        self.assertFalse(limited.complete)
        self.assertLessEqual(len(limited.findings[0].instruction), 5)

    def test_redaction_and_export_contracts(self):
        text = "api_token: str = 'fake_example_value secondpart'\nexec('x')\n"
        report = prepare_report(scan(text).to_dict())
        self.assertTrue(validate_report(report))
        self.assertNotIn("fake_example_value", json.dumps(report))
        self.assertNotIn("secondpart", json.dumps(report))
        rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        sarif = render_sarif(report, rules_for_report(report, rules))
        validate_sarif(sarif)
        descriptors = {r["id"] for r in sarif["runs"][0]["tool"]["driver"]["rules"]}
        self.assertIn("PY-001", descriptors)
        self.assertIn("PY-005", descriptors)
        self.assertNotIn("fake_example_value", render_html(report))

    def test_source_is_never_executed_and_bash_still_works(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "executed"
            script = Path(temp) / "input.py"
            script.write_text(f"open({str(marker)!r}, 'w').write('bad')\n", encoding="utf-8")
            with mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
                report = analyze(script)
            self.assertTrue(report.complete)
            self.assertFalse(marker.exists())
            self.assertEqual(report.sha256, hashlib.sha256(script.read_bytes()).hexdigest())
        self.assertEqual(scan("echo hello\n", name="example.sh").parser, "tree-sitter-bash")
        with self.assertRaises(ValueError):
            scan("echo hello\n", name="example.txt")
