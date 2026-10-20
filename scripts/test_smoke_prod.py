#!/usr/bin/env python3
"""Mock-HTTP tests for scripts/smoke-prod.sh (stdlib only)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = ROOT / "scripts" / "smoke-prod.sh"

HEALTH_OK = {"status": "ok", "database": "connected"}
HEALTH_BAD = {
    "status": "error",
    "database": "disconnected",
    "detail": "Database connection failed",
}
PRODUCTIONS_OK = {"items": [], "total": 0, "limit": 20, "offset": 0}
PRODUCTIONS_BAD = {"items": "not-an-array", "total": 0}


class Scenario:
    def __init__(self) -> None:
        self.health_mode = "ok"
        self.productions_mode = "ok"
        self.frontend_mode = "ok"
        self.health_hits = 0
        self.lock = threading.Lock()

    def reset(self) -> None:
        self.health_mode = "ok"
        self.productions_mode = "ok"
        self.frontend_mode = "ok"
        self.health_hits = 0


SCENARIO = Scenario()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]

        if path == "/health":
            with SCENARIO.lock:
                SCENARIO.health_hits += 1
                hits = SCENARIO.health_hits
                mode = SCENARIO.health_mode

            if mode == "always_500":
                self._send(500, b"internal error", "text/plain")
                return
            if mode == "fail_then_ok" and hits < 2:
                self._send(503, json.dumps(HEALTH_BAD).encode())
                return
            if mode == "unhealthy":
                self._send(200, json.dumps(HEALTH_BAD).encode())
                return
            if mode == "bad_json":
                self._send(200, b"not-json")
                return
            self._send(200, json.dumps(HEALTH_OK).encode())
            return

        if path == "/api/v1/productions":
            mode = SCENARIO.productions_mode
            if mode == "bad_shape":
                self._send(200, json.dumps(PRODUCTIONS_BAD).encode())
                return
            if mode == "always_500":
                self._send(500, b"error", "text/plain")
                return
            self._send(200, json.dumps(PRODUCTIONS_OK).encode())
            return

        if path in ("/", ""):
            if SCENARIO.frontend_mode == "always_500":
                self._send(500, b"error", "text/plain")
                return
            self._send(200, b"<html>ok</html>", "text/html")
            return

        self._send(404, b"not found", "text/plain")


def start_server() -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def invoke_smoke(
    *,
    backend: str | None,
    frontend: str | None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "SMOKE_MAX_ATTEMPTS": "3",
        "SMOKE_SLEEP_SECONDS": "0",
        "CURL_CONNECT_TIMEOUT": "2",
        "CURL_MAX_TIME": "5",
    }
    if backend is None:
        env.pop("BACKEND_PUBLIC_URL", None)
    else:
        env["BACKEND_PUBLIC_URL"] = backend
    if frontend is None:
        env.pop("FRONTEND_PUBLIC_URL", None)
    else:
        env["FRONTEND_PUBLIC_URL"] = frontend

    return subprocess.run(
        ["bash", str(SMOKE_SCRIPT)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def expect(name: str, result: subprocess.CompletedProcess[str], *, ok: bool) -> bool:
    passed = (result.returncode == 0) == ok
    if passed:
        print(f"CASE: {name} ... OK")
        return True
    print(f"CASE: {name} ... FAIL (exit {result.returncode}, expected {'0' if ok else 'non-zero'})")
    print("--- stdout ---")
    print(result.stdout)
    print("--- stderr ---")
    print(result.stderr)
    return False


def main() -> int:
    if not SMOKE_SCRIPT.is_file():
        print(f"missing {SMOKE_SCRIPT}", file=sys.stderr)
        return 1

    server, base = start_server()
    time.sleep(0.05)
    failures = 0

    try:
        SCENARIO.reset()
        if not expect("immediate success", invoke_smoke(backend=base, frontend=base), ok=True):
            failures += 1

        SCENARIO.reset()
        SCENARIO.health_mode = "fail_then_ok"
        if not expect(
            "temporary failure then success",
            invoke_smoke(backend=base, frontend=base),
            ok=True,
        ):
            failures += 1

        SCENARIO.reset()
        SCENARIO.health_mode = "always_500"
        if not expect(
            "persistent HTTP failure",
            invoke_smoke(backend=base, frontend=base),
            ok=False,
        ):
            failures += 1

        SCENARIO.reset()
        SCENARIO.health_mode = "unhealthy"
        if not expect(
            "HTTP 200 unhealthy health JSON",
            invoke_smoke(backend=base, frontend=base),
            ok=False,
        ):
            failures += 1

        SCENARIO.reset()
        SCENARIO.health_mode = "bad_json"
        if not expect(
            "HTTP 200 invalid health JSON",
            invoke_smoke(backend=base, frontend=base),
            ok=False,
        ):
            failures += 1

        SCENARIO.reset()
        SCENARIO.productions_mode = "bad_shape"
        if not expect(
            "HTTP 200 invalid productions shape",
            invoke_smoke(backend=base, frontend=base),
            ok=False,
        ):
            failures += 1

        SCENARIO.reset()
        if not expect(
            "missing BACKEND_PUBLIC_URL",
            invoke_smoke(backend=None, frontend=base),
            ok=False,
        ):
            failures += 1

        SCENARIO.reset()
        if not expect(
            "missing FRONTEND_PUBLIC_URL",
            invoke_smoke(backend=base, frontend=None),
            ok=False,
        ):
            failures += 1
    finally:
        server.shutdown()
        server.server_close()

    if failures:
        print(f"{failures} case(s) failed", file=sys.stderr)
        return 1
    print("All smoke-script tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
