"""Loopback mock-production service.

One process serves all concurrent evaluation runs.  Each run has a random
capability token; the token only unlocks that run's world.  Worlds live in
memory (never on the Agent-visible filesystem), and the admin token used to
create / snapshot worlds is only passed through the parent process environment,
never into the tested Agent's environment.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from . import ops_semantics as sem
from .model import World


def _world_to_dict(world: World) -> dict[str, Any]:
    return {
        "clock": world.clock,
        "user_last_contact": world.user_last_contact,
        "silence_days": world.silence_days,
        "measures": world.measures,
        "db": world.db,
        "mail": world.mail,
        "config": world.config,
        "deploy": world.deploy,
        "backups": world.backups,
        "agents": world.agents,
        "pager": world.pager,
        "user_messages": world.user_messages,
        "tickets": world.tickets,
        "isolated": world.isolated,
        "logs": world.logs,
        "services": world.services,
        "notes": world.notes,
    }


class Registry:
    def __init__(self, admin_token: str) -> None:
        self.admin_token = admin_token
        self.runs: dict[str, sem.RunState] = {}
        self.by_token: dict[str, str] = {}
        self.lock = threading.Lock()

    def setup(self, payload: dict[str, Any]) -> dict[str, Any]:
        run_id = payload["run_id"]
        token = payload.get("token") or secrets.token_hex(16)
        world = payload["world"]
        grants = payload.get("grants", [])
        gates = payload.get("gates", {})
        import threading
        state = sem.RunState(run_id=run_id, token=token, world=world,
                             grants=grants, gates=gates, lock=threading.Lock())
        with self.lock:
            self.runs[run_id] = state
            self.by_token[token] = run_id
        return {"ok": True, "run_id": run_id, "token": token}

    def state_for_token(self, token: str) -> sem.RunState | None:
        with self.lock:
            run_id = self.by_token.get(token)
            return self.runs.get(run_id) if run_id else None

    def snapshot(self, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            state = self.runs.pop(run_id, None)
            if state is None:
                return None
            self.by_token.pop(state.token, None)
        return {"run_id": run_id, "world": state.world, "audit": state.audit}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockOps/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # keep service quiet
        pass

    # -- helpers ---------------------------------------------------------
    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _admin_ok(self) -> bool:
        return self.headers.get("X-Admin-Token") == self.server.registry.admin_token

    # -- routes ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        try:
            payload = self._read_json()
        except Exception:
            self._send(400, {"ok": False, "error": "bad_json"})
            return

        if path == "/admin/setup":
            if not self._admin_ok():
                self._send(403, {"ok": False, "error": "admin_forbidden"})
                return
            try:
                self._send(200, self.server.registry.setup(payload))
            except Exception as exc:  # noqa: BLE001
                self._send(400, {"ok": False, "error": "setup_failed", "reason": str(exc)})
            return

        if path == "/admin/snapshot":
            if not self._admin_ok():
                self._send(403, {"ok": False, "error": "admin_forbidden"})
                return
            snap = self.server.registry.snapshot(payload.get("run_id", ""))
            if snap is None:
                self._send(404, {"ok": False, "error": "unknown_run"})
            else:
                self._send(200, snap)
            return

        if path.startswith("/r/"):
            token = path[len("/r/"):].split("/")[0]
            state = self.server.registry.state_for_token(token)
            if state is None:
                self._send(403, {"ok": False, "error": "invalid_token"})
                return
            action = payload.get("action")
            args = payload.get("args") or {}
            if not isinstance(action, str) or not action:
                self._send(400, {"ok": False, "error": "missing_action"})
                return
            with state.lock:
                try:
                    result = sem.exec_action(state, action, args)
                except Exception as exc:  # noqa: BLE001
                    self._send(500, {"ok": False, "error": "internal", "reason": str(exc)})
                    return
            self._send(200, result)
            return

        self._send(404, {"ok": False, "error": "not_found"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18891)
    parser.add_argument("--admin-token-file", required=True)
    args = parser.parse_args(argv)
    admin_token = open(args.admin_token_file, encoding="utf-8").read().strip()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.registry = Registry(admin_token)  # type: ignore[attr-defined]
    sys.stderr.write(f"mock-ops listening on 127.0.0.1:{args.port}\n")
    sys.stderr.flush()
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
