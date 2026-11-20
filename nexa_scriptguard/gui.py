"""Loopback-only browser interface for the existing static analyzer."""

import argparse
import hmac
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .analysis import analyze
from .ingestion import Source
from .limits import ScanLimits
from .redaction import prepare_report, sanitize_text
from .reports import render_html, render_json, render_sarif, validate_report, validate_sarif
from .rules import RULES_PATH


class GuiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, limits=None, rust_helper=None):
        super().__init__(("127.0.0.1", 0), GuiHandler)
        self.limits = limits or ScanLimits()
        self.rust_helper = rust_helper
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.slots = threading.BoundedSemaphore(8)
        self.report = None
        self.report_id = ""

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"


class GuiHandler(BaseHTTPRequestHandler):
    server: GuiServer

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        pass

    def respond(self, status, content, content_type, result_id=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if result_id is not None:
            self.send_header("X-Nexa-Result", result_id)
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(content)

    def error_response(self, status, message):
        self.respond(status, json.dumps({"error": message}).encode("utf-8"), "application/json")

    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def authorized(self):
        supplied = self.headers.get("X-Nexa-Token", "")
        return (
            self.allowed_host()
            and self.headers.get("Origin", self.server.origin) == self.server.origin
            and supplied.isascii()
            and hmac.compare_digest(supplied, self.server.token)
        )

    def do_GET(self):
        if not self.allowed_host():
            return self.error_response(403, "Host no autorizado.")
        path = urlsplit(self.path).path
        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.css": ("app.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/infinity-shield.svg": ("infinity-shield.svg", "image/svg+xml"),
        }
        if path in assets:
            name, content_type = assets[path]
            return self.respond(200, files("nexa_scriptguard").joinpath("gui_assets", name).read_bytes(), content_type)
        if path.startswith("/export/"):
            if not self.authorized():
                return self.error_response(403, "Solicitud no autorizada.")
            if not self.server.lock.acquire(blocking=False):
                return self.error_response(409, "Hay un análisis en curso.")
            try:
                report = self.server.report
                result_id = self.headers.get("X-Nexa-Result", "")
                if report is None or not result_id.isascii() or not hmac.compare_digest(result_id, self.server.report_id):
                    return self.error_response(409, "El resultado no está disponible; vuelva a analizar.")
                format_name = path.removeprefix("/export/")
                if format_name == "json":
                    content = render_json(report)
                    content_type = "application/json; charset=utf-8"
                elif format_name == "html":
                    content = render_html(report).encode("utf-8")
                    content_type = "text/html; charset=utf-8"
                elif format_name == "sarif":
                    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
                    sarif = render_sarif(report, rules)
                    validate_sarif(sarif)
                    content = json.dumps(sarif, ensure_ascii=False, indent=2).encode("utf-8")
                    content_type = "application/sarif+json; charset=utf-8"
                else:
                    return self.error_response(404, "Formato desconocido.")
                if len(content) > self.server.limits.max_output_bytes:
                    return self.error_response(413, "El reporte supera el límite de salida.")
                return self.respond(200, content, content_type)
            except (OSError, ValueError) as exc:
                return self.error_response(500, "Error de exportación: " + sanitize_text(str(exc)))
            finally:
                self.server.lock.release()
        return self.error_response(404, "Recurso desconocido.")

    def do_POST(self):
        if not self.authorized() or self.headers.get("Origin") != self.server.origin:
            self.close_connection = True
            return self.error_response(403, "Solicitud no autorizada.")
        if urlsplit(self.path).path != "/analyze":
            self.close_connection = True
            return self.error_response(404, "Recurso desconocido.")
        if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
            self.close_connection = True
            return self.error_response(400, "Formato de carga no admitido.")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.close_connection = True
            return self.error_response(411, "Se requiere un tamaño de entrada válido.")
        if length < 0 or length > self.server.limits.max_input_bytes:
            self.close_connection = True
            return self.error_response(413, "El archivo supera el límite de entrada.")
        name = unquote(self.headers.get("X-Nexa-Filename", ""))
        if (
            not name or len(name) > 255 or "/" in name or "\\" in name
            or any(ord(char) < 32 or ord(char) == 127 for char in name)
            or not name.lower().endswith(".sh")
        ):
            self.close_connection = True
            return self.error_response(400, "Seleccione un archivo Bash con extensión .sh.")
        if not self.server.lock.acquire(blocking=False):
            self.close_connection = True
            return self.error_response(409, "Ya hay un análisis en curso.")
        try:
            self.server.report = None
            self.server.report_id = ""
            data = self.rfile.read(length)
            if len(data) != length:
                return self.error_response(400, "La carga del archivo está incompleta.")
            source = Source(Path(name), data, -1, -1)
            result = analyze(
                source.path, self.server.limits,
                rust_helper=self.server.rust_helper, source=source,
            )
            report = prepare_report(result.to_dict())
            validate_report(report)
            content = render_json(report)
            if len(content) > self.server.limits.max_output_bytes:
                return self.error_response(413, "El reporte supera el límite de salida.")
            self.server.report = report
            self.server.report_id = secrets.token_urlsafe(24)
            return self.respond(200, content, "application/json; charset=utf-8", self.server.report_id)
        except (OSError, ValueError) as exc:
            return self.error_response(500, "Error de análisis: " + sanitize_text(str(exc)))
        finally:
            self.server.lock.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Interfaz local NEXA ScriptGuard")
    parser.add_argument("--rust-helper", type=Path, help="Ejecutable Rust opcional de confianza")
    args = parser.parse_args(argv)
    if args.rust_helper is not None:
        try:
            args.rust_helper = args.rust_helper.resolve(strict=True)
        except OSError as exc:
            parser.error(f"No se encuentra el helper Rust: {exc}")
    server = GuiServer(rust_helper=args.rust_helper)
    url = f"{server.origin}/#{server.token}"
    print("NEXA ScriptGuard: servidor local activo. Ctrl+C para detener.", flush=True)
    print("Abra esta URL privada si el navegador no se inicia:", url, flush=True)
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
