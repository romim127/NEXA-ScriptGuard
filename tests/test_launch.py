import contextlib
import http.client
import io
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import venv
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from nexa_scriptguard import gui


ROOT = Path(__file__).resolve().parents[1]


class GuiLaunchTests(unittest.TestCase):
    def test_browser_open_and_keyboard_interrupt_close_the_server(self):
        for browser_result in (True, False, OSError("browser unavailable")):
            with self.subTest(browser_result=browser_result), contextlib.ExitStack() as stack:
                server = stack.enter_context(mock.patch.object(gui, "GuiServer")).return_value
                server.origin = "http://127.0.0.1:54321"
                server.token = "private-token"
                server.serve_forever.side_effect = KeyboardInterrupt
                browser = stack.enter_context(mock.patch.object(gui.webbrowser, "open"))
                if isinstance(browser_result, Exception):
                    browser.side_effect = browser_result
                else:
                    browser.return_value = browser_result
                output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                errors = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                self.assertEqual(gui.main([]), 0)
                url = f"{server.origin}/#{server.token}"
                browser.assert_called_once_with(url)
                self.assertIn(url, output.getvalue())
                self.assertEqual("manualmente" in errors.getvalue(), browser_result is not True)
                server.server_close.assert_called_once()

    def test_startup_errors_do_not_open_browser(self):
        for stage in ("parse_bash", "GuiServer"):
            with self.subTest(stage=stage), mock.patch.object(gui, stage, side_effect=OSError):
                with mock.patch.object(gui.webbrowser, "open") as browser:
                    with contextlib.redirect_stderr(io.StringIO()) as errors:
                        self.assertEqual(gui.main([]), 1)
                    self.assertIn("NEXA ScriptGuard:", errors.getvalue())
                    browser.assert_not_called()


class LauncherProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = tempfile.TemporaryDirectory(prefix="nexa launch ")
        cls.addClassCleanup(folder.cleanup)
        cls.work = Path(folder.name)
        cls.env = dict(os.environ)
        active = Path(sys.prefix)
        if sys.prefix == sys.base_prefix:
            active = cls.work / "active env"
            venv.EnvBuilder(system_site_packages=True).create(active)
        cls.env["VIRTUAL_ENV"] = str(active)
        if os.name == "nt":
            cls.launcher = ["cmd.exe", "/d", "/c", "call", str(ROOT / "run-windows.bat")]
        else:
            cls.launcher = ["bash", str(ROOT / "run-linux.sh")]

    def test_launcher_from_another_directory(self):
        result = subprocess.run(
            [*self.launcher, "--help"], cwd=self.work, env=self.env,
            capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"--rust-helper", result.stdout)

    @unittest.skipUnless(sys.platform == "linux", "Linux signal and BROWSER integration")
    def test_browser_handoff_dynamic_ports_and_controlled_shutdown(self):
        browser = self.work / "browser.py"
        browser.write_text(
            "import os, sys\nfrom pathlib import Path\n"
            "Path(os.environ['NEXA_BROWSER_CAPTURE']).write_text(sys.argv[1], encoding='utf-8')\n",
            encoding="utf-8",
        )
        with socket.socket() as occupied, contextlib.ExitStack() as stack:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            reserved = occupied.getsockname()[1]
            ports = set()
            tokens = set()
            for index in range(2):
                cwd = self.work / f"caller {index}"
                cwd.mkdir()
                capture = cwd / "url"
                env = dict(self.env, BROWSER=shlex.join([sys.executable, str(browser), "%s"]),
                           NEXA_BROWSER_CAPTURE=str(capture))
                log = stack.enter_context((cwd / "server.log").open("w+b"))
                process = subprocess.Popen(self.launcher, cwd=cwd, env=env, stdout=log, stderr=log)
                stack.callback(self.stop_process, process)
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and process.poll() is None:
                    if capture.exists() and capture.stat().st_size:
                        break
                    time.sleep(0.05)
                details = (cwd / "server.log").read_bytes()
                self.assertTrue(capture.exists(), details)
                url = capture.read_text(encoding="utf-8")
                parts = urlsplit(url)
                self.assertEqual(parts.hostname, "127.0.0.1")
                self.assertRegex(parts.fragment, re.compile(r"^[A-Za-z0-9_-]{40,}$"))
                self.assertNotIn(parts.port, ports | {reserved})
                self.assertNotIn(parts.fragment, tokens)
                ports.add(parts.port)
                tokens.add(parts.fragment)
                connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=5)
                try:
                    connection.request("GET", "/")
                    with connection.getresponse() as response:
                        self.assertEqual(response.status, 200)
                        self.assertIn(b"NEXA ScriptGuard", response.read())
                finally:
                    connection.close()
            stack.close()
            for port in ports:
                with self.assertRaises(ConnectionRefusedError):
                    socket.create_connection(("127.0.0.1", port), timeout=2).close()

    def stop_process(self, process):
        try:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            self.assertEqual(process.wait(timeout=5), 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
