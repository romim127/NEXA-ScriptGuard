import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nexa_scriptguard.redaction import prepare_report, sanitize_text


ROOT = Path(__file__).resolve().parents[1]


class RedactionTests(unittest.TestCase):
    def test_synthetic_credentials_paths_and_controls(self):
        examples = [
            ("password=synthetic_password_123", "synthetic_password_123"),
            ("api_key='synthetic_api_key_123'", "synthetic_api_key_123"),
            ("Authorization: Bearer synthetic_bearer_123", "synthetic_bearer_123"),
            ("https://synthetic_user:synthetic_password@example.invalid/a", "synthetic_password"),
            ("/home/synthetic_person/.aws/credentials", "synthetic_person"),
            (r"C:\Users\synthetic_person\.ssh\id_rsa", "synthetic_person"),
            ("/root/.ssh/id_ed25519", "/root/.ssh/id_ed25519"),
            ("~/.env", "~/.env"),
        ]
        for value, sensitive in examples:
            with self.subTest(category=value.split("=")[0]):
                sanitized = sanitize_text(value)
                self.assertNotIn(sensitive, sanitized)
                self.assertIn("[REDACTED", sanitized)
        sanitized = sanitize_text("a\x1b\x00\r\u202eb")
        for character in ("\x1b", "\x00", "\r", "\u202e"):
            self.assertNotIn(character, sanitized)
        self.assertIn(r"\u001b", sanitized)
        self.assertIn(r"\u202e", sanitized)

    def test_recursive_redaction_and_explicit_opt_out(self):
        source = {
            "file": "/home/synthetic_person/scan.sh",
            "findings": [{
                "file": "/home/synthetic_person/scan.sh",
                "evidence": {
                    "original": "token=synthetic_token_123\x1b",
                    "correlation": [{"reason": "Authorization: Bearer synthetic_bearer_123"}],
                },
            }],
        }
        protected = prepare_report(source)
        self.assertNotIn("synthetic_token_123", json.dumps(protected))
        self.assertNotIn("synthetic_bearer_123", json.dumps(protected))
        self.assertNotIn("original", protected["findings"][0]["evidence"])
        self.assertFalse(protected["findings"][0]["evidence"]["original_available_in_this_report"])
        self.assertEqual(source["findings"][0]["evidence"]["original"], "token=synthetic_token_123\x1b")

        unredacted = prepare_report(source, redact_secrets=False)
        self.assertIn("synthetic_token_123", unredacted["findings"][0]["evidence"]["original"])
        self.assertTrue(unredacted["findings"][0]["evidence"]["original_available_in_this_report"])
        self.assertNotIn("\x1b", unredacted["findings"][0]["evidence"]["original"])

    def test_all_cli_formats_protect_synthetic_content(self):
        source = (
            'eval "echo ok" # password=synthetic_password_123 '
            'Authorization: Bearer synthetic_bearer_123 '
            '/home/synthetic_person/.aws/credentials \x1b]0;title\u202e\n'
        )
        for view in ("plain", "neon"):
            with self.subTest(view=view), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                script = root / "input.sh"
                script.write_bytes(source.encode("utf-8"))
                outputs = [root / "out.json", root / "out.html", root / "out.sarif"]
                env = dict(os.environ, PYTHONIOENCODING="utf-8")
                result = subprocess.run(
                    [
                        sys.executable, "-m", "nexa_scriptguard", str(script),
                        "--view", view, "--json", str(outputs[0]),
                        "--html", str(outputs[1]), "--sarif", str(outputs[2]),
                    ],
                    cwd=ROOT, env=env, capture_output=True, timeout=30, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
                report = json.loads(outputs[0].read_text(encoding="utf-8"))
                self.assertTrue(report["findings"])
                texts = [result.stdout.decode("utf-8")]
                texts.extend(path.read_text(encoding="utf-8") for path in outputs)
                for text in texts:
                    for sensitive in (
                        "synthetic_password_123", "synthetic_bearer_123",
                        "synthetic_person", "\x1b", "\u202e",
                    ):
                        self.assertNotIn(sensitive, text)


if __name__ == "__main__":
    unittest.main()
