import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from nexa_scriptguard.ingestion import (
    OutputError,
    read_source,
    write_reports,
)
from nexa_scriptguard.limits import ScanLimits


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source_path = self.root / "source.sh"
        self.source_path.write_text("echo safe\n", encoding="utf-8")
        self.limits = ScanLimits()
        self.source = read_source(self.source_path, self.limits)

    def test_refuses_hardlink_alias_of_input(self):
        output = self.root / "report.json"
        try:
            os.link(self.source_path, output)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        with self.assertRaises(OutputError):
            write_reports({output: b"{}"}, self.source, self.limits)
        self.assertEqual(self.source_path.read_text(encoding="utf-8"), "echo safe\n")

    def test_refuses_symlink_destination(self):
        output = self.root / "report.json"
        target = self.root / "target.json"
        target.write_text("preserve", encoding="utf-8")
        try:
            output.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")
        with self.assertRaises(OutputError):
            write_reports({output: b"{}"}, self.source, self.limits)
        self.assertEqual(target.read_text(encoding="utf-8"), "preserve")

    def test_refuses_existing_destination_without_overwrite(self):
        output = self.root / "report.json"
        output.write_bytes(b"existing")
        with self.assertRaises(OutputError):
            write_reports({output: b"replacement"}, self.source, self.limits)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_rejects_equivalent_output_names(self):
        output = self.root / "report.json"
        alias = self.root / "subdir" / ".." / "report.json"
        (self.root / "subdir").mkdir()
        with self.assertRaisesRegex(OutputError, "Duplicate"):
            write_reports({output: b"one", alias: b"two"}, self.source, self.limits)
        self.assertFalse(output.exists())

    def test_racing_destination_is_not_overwritten(self):
        output = self.root / "report.json"
        original_link = os.link

        def racing_link(temporary, destination):
            output.write_bytes(b"other writer")
            return original_link(temporary, destination)

        with mock.patch("nexa_scriptguard.ingestion.os.link", side_effect=racing_link):
            with self.assertRaisesRegex(OutputError, "publication failed"):
                write_reports({output: b"our report"}, self.source, self.limits)
        self.assertEqual(output.read_bytes(), b"other writer")
        self.assertEqual(self.source_path.read_text(encoding="utf-8"), "echo safe\n")

    def test_atomic_no_clobber_under_concurrent_writers(self):
        output = self.root / "shared.json"
        barrier = threading.Barrier(2)
        outcomes = []

        def publish(content):
            barrier.wait()
            try:
                write_reports({output: content}, self.source, self.limits)
                outcomes.append("published")
            except OutputError:
                outcomes.append("rejected")

        workers = [
            threading.Thread(target=publish, args=(b'{"writer":1}',)),
            threading.Thread(target=publish, args=(b'{"writer":2}',)),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=5)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertCountEqual(outcomes, ["published", "rejected"])
        self.assertIn(output.read_bytes(), (b'{"writer":1}', b'{"writer":2}'))

    def test_output_byte_limit_is_enforced(self):
        limits = ScanLimits(max_output_bytes=2)
        with self.assertRaises(OutputError):
            write_reports(
                {self.root / "report.json": b"long"},
                self.source,
                limits,
            )
        self.assertFalse((self.root / "report.json").exists())

    def test_partial_multi_report_publication_rolls_back_first_output(self):
        first = self.root / "first.json"
        second = self.root / "second.json"
        original_link = os.link
        with mock.patch(
            "nexa_scriptguard.ingestion.os.link",
            side_effect=[original_link, OSError("synthetic second-link failure")],
        ):
            with self.assertRaisesRegex(OutputError, "rolled back"):
                write_reports(
                    {first: b"first", second: b"second"},
                    self.source,
                    self.limits,
                )
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())

    def test_rollback_preserves_replaced_output(self):
        first = self.root / "first.json"
        second = self.root / "second.json"
        original_link = os.link
        calls = 0

        def replace_before_failure(temporary, destination):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_link(temporary, destination)
            first.unlink()
            first.write_bytes(b"replacement")
            raise OSError("synthetic second-link failure")

        with mock.patch("nexa_scriptguard.ingestion.os.link", side_effect=replace_before_failure):
            with self.assertRaises(OutputError):
                write_reports({first: b"first", second: b"second"}, self.source, self.limits)
        self.assertEqual(first.read_bytes(), b"replacement")
        self.assertFalse(second.exists())

    def test_input_limit_is_enforced_before_analysis(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            read_source(
                self.source_path,
                ScanLimits(max_input_bytes=2),
            )

    def test_distinct_hardlink_rejected_and_input_unchanged(self):
        first = self.root / "first.json"
        second = self.root / "second.json"
        try:
            os.link(self.source_path, second)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        with self.assertRaises(OutputError):
            write_reports(
                {first: b"{}", second: b"{}"},
                self.source,
                self.limits,
            )
        self.assertFalse(first.exists())
        self.assertEqual(self.source_path.read_text(encoding="utf-8"), "echo safe\n")
