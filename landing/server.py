from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WAITLIST_FILE = DATA_DIR / "waitlist.json"
ANALYTICS_DEBUG_FILE = DATA_DIR / "analytics-debug.jsonl"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _read_waitlist() -> list[dict]:
    if not WAITLIST_FILE.exists():
        return []

    try:
        with WAITLIST_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
    except json.JSONDecodeError:
        pass

    return []


def _write_waitlist(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with WAITLIST_FILE.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _append_analytics_debug(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with ANALYTICS_DEBUG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_analytics_debug(limit: int = 100) -> list[dict]:
    if not ANALYTICS_DEBUG_FILE.exists():
        return []

    rows: list[dict] = []
    with ANALYTICS_DEBUG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)

    return rows[-limit:]


def _clear_analytics_debug() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DEBUG_FILE.write_text("", encoding="utf-8")


class LandingHandler(SimpleHTTPRequestHandler):
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json_pretty(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _build_analytics_debug_page(self, events: list[dict]) -> str:
        rows: list[str] = []
        for idx, event in enumerate(reversed(events), start=1):
            props = json.dumps(event.get("props", {}), ensure_ascii=False, indent=2)
            rows.append(
                "<tr>"
                f"<td>{idx}</td>"
                f"<td>{event.get('received_at', '')}</td>"
                f"<td>{event.get('event_name', '')}</td>"
                f"<td>{event.get('remote_addr', '')}</td>"
                f"<td><details><summary>props</summary><pre>{props}</pre></details></td>"
                "</tr>"
            )

        table_rows = "\n".join(rows) if rows else "<tr><td colspan='5'>No events yet</td></tr>"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Analytics Debug</title>
  <style>
    body {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin: 24px; background:#0c1022; color:#dce3ff; }}
    h1 {{ margin: 0 0 14px; font-size: 20px; }}
    .meta {{ margin-bottom: 14px; color: #96a2d8; font-size: 13px; }}
    a {{ color: #88b4ff; }}
    table {{ width: 100%; border-collapse: collapse; background:#121735; border:1px solid #2f365f; }}
    th, td {{ border:1px solid #2f365f; padding: 8px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background:#181f46; position: sticky; top: 0; }}
    pre {{ margin: 8px 0 0; white-space: pre-wrap; word-break: break-word; color:#c7f0d4; }}
    details > summary {{ cursor: pointer; color: #8eb8ff; }}
  </style>
</head>
<body>
  <h1>Landing Analytics Debug</h1>
  <div class="meta">
    Events: {len(events)} | JSON API: <a href="/api/analytics-debug?pretty=1">/api/analytics-debug?pretty=1</a>
    <button id="clear-events-btn" type="button" style="margin-left:12px;padding:6px 10px;border-radius:8px;border:1px solid #405097;background:#1e295c;color:#e4ebff;cursor:pointer;">Clear events</button>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>received_at</th>
        <th>event_name</th>
        <th>remote_addr</th>
        <th>props</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
  <script>
    const clearBtn = document.getElementById("clear-events-btn");
    if (clearBtn) {{
      clearBtn.addEventListener("click", async () => {{
        const ok = window.confirm("Clear all analytics debug events?");
        if (!ok) return;
        clearBtn.disabled = true;
        try {{
          const response = await fetch("/api/analytics-debug/clear", {{ method: "POST" }});
          if (!response.ok) throw new Error("clear failed");
          window.location.reload();
        }} catch {{
          alert("Failed to clear events.");
          clearBtn.disabled = false;
        }}
      }});
    }}
  </script>
</body>
</html>"""

    def _read_json_payload(self) -> tuple[dict | None, str | None]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, "Invalid content length"

        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None, "Invalid JSON"

        if not isinstance(payload, dict):
            return None, "JSON body must be object"

        return payload, None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/analytics-debug/view":
            events = _read_analytics_debug(limit=300)
            self._send_html(200, self._build_analytics_debug_page(events))
            return

        if parsed.path == "/api/analytics-debug":
            query = parse_qs(parsed.query)
            try:
                limit = int((query.get("limit") or ["120"])[0])
            except ValueError:
                limit = 120
            limit = max(1, min(limit, 1000))

            events = _read_analytics_debug(limit=limit)
            payload = {"ok": True, "count": len(events), "events": events}
            if (query.get("pretty") or ["0"])[0] in {"1", "true", "yes"}:
                self._send_json_pretty(200, payload)
            else:
                self._send_json(200, payload)
            return

        super().do_GET()

    def _handle_waitlist(self) -> None:
        payload, error = self._read_json_payload()
        if error:
            self._send_json(400, {"ok": False, "error": error})
            return

        assert payload is not None
        email = str(payload.get("email", "")).strip().lower()
        source = str(payload.get("source", "landing"))
        submitted_at = str(payload.get("submitted_at", "")).strip()

        if not EMAIL_PATTERN.match(email):
            self._send_json(400, {"ok": False, "error": "Invalid email"})
            return

        if not submitted_at:
            submitted_at = datetime.now(timezone.utc).isoformat()

        records = _read_waitlist()

        if any(str(item.get("email", "")).lower() == email for item in records):
            self._send_json(200, {"ok": True, "saved": False, "message": "already_exists"})
            return

        record = {
            "email": email,
            "source": source,
            "submitted_at": submitted_at,
        }
        records.append(record)
        _write_waitlist(records)

        self._send_json(200, {"ok": True, "saved": True})

    def _handle_analytics_debug(self) -> None:
        payload, error = self._read_json_payload()
        if error:
            self._send_json(400, {"ok": False, "error": error})
            return

        assert payload is not None
        event_name = str(payload.get("event_name", "")).strip()
        props = payload.get("props")

        if not event_name:
            self._send_json(400, {"ok": False, "error": "event_name is required"})
            return
        if not isinstance(props, dict):
            self._send_json(400, {"ok": False, "error": "props must be object"})
            return

        entry = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "event_name": event_name,
            "props": props,
            "user_agent": self.headers.get("User-Agent", ""),
            "remote_addr": self.client_address[0] if self.client_address else "",
        }
        _append_analytics_debug(entry)
        self._send_json(200, {"ok": True, "saved": True})

    def do_POST(self) -> None:
        if self.path == "/api/waitlist":
            self._handle_waitlist()
            return

        if self.path == "/api/analytics-debug":
            self._handle_analytics_debug()
            return

        if self.path == "/api/analytics-debug/clear":
            _clear_analytics_debug()
            self._send_json(200, {"ok": True, "cleared": True})
            return

        self._send_json(404, {"ok": False, "error": "Not found"})


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    port = int(os.environ.get("PORT", "8081"))
    server = ThreadingHTTPServer(("127.0.0.1", port), LandingHandler)
    print(f"Landing server running on http://127.0.0.1:{port}")
    print(f"Waitlist file: {WAITLIST_FILE}")
    print(f"Analytics debug file: {ANALYTICS_DEBUG_FILE}")
    server.serve_forever()
