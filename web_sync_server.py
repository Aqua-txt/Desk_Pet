from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


class LocalWebServer:
    """提供静态网页和轻量同步 API。"""

    def __init__(
        self,
        project_root: Path,
        stats_provider: Callable[[], dict],
        checkins_provider: Callable[[], list] | None = None,
        checkin_adder: Callable[[dict], list] | None = None,
        host: str = "127.0.0.1",
        port: int = 8765,
    ):
        self.project_root = Path(project_root).resolve()
        self.stats_provider = stats_provider
        self.checkins_provider = checkins_provider
        self.checkin_adder = checkin_adder
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None and self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return

        stats_provider = self.stats_provider
        checkins_provider = self.checkins_provider
        checkin_adder = self.checkin_adder
        directory = str(self.project_root)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/api/learning-stats":
                    try:
                        payload = stats_provider()
                    except Exception as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                        return
                    self._send_json({"ok": True, "data": payload})
                    return
                if parsed.path == "/api/passion-checkins":
                    if checkins_provider is None:
                        self._send_json({"ok": False, "error": "checkins provider unavailable"}, status=HTTPStatus.NOT_FOUND)
                        return
                    try:
                        payload = checkins_provider()
                    except Exception as exc:
                        self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                        return
                    self._send_json({"ok": True, "data": payload})
                    return
                return super().do_GET()

            def do_POST(self):
                parsed = urlparse(self.path)
                if parsed.path != "/api/passion-checkins":
                    self._send_json({"ok": False, "error": "not found"}, status=HTTPStatus.NOT_FOUND)
                    return
                if checkin_adder is None:
                    self._send_json({"ok": False, "error": "checkin adder unavailable"}, status=HTTPStatus.NOT_FOUND)
                    return

                length = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(body.decode("utf-8"))
                except Exception:
                    self._send_json({"ok": False, "error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
                    return

                record = payload.get("record")
                if not isinstance(record, dict):
                    self._send_json({"ok": False, "error": "record must be object"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    new_list = checkin_adder(record)
                except ValueError as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.CONFLICT)
                    return
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                    return
                self._send_json({"ok": True, "data": new_list})

            def log_message(self, format, *args):
                # 保持控制台简洁，避免刷屏
                return

            def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status.value)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    def build_url(self, relative_path: str) -> str:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        return f"http://{self.host}:{self.port}/{normalized}"
