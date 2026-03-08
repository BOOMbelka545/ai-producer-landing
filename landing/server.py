from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WAITLIST_FILE = DATA_DIR / "waitlist.json"
ANALYTICS_DEBUG_FILE = DATA_DIR / "analytics-debug.jsonl"
ANALYTICS_ACCESS_LOG_FILE = DATA_DIR / "analytics-access.jsonl"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

MIXPANEL_TRACK_URL = "https://api-js.mixpanel.com/track?verbose=1&ip=1"
MIXPANEL_TOKEN_DEV = os.environ.get("MIXPANEL_TOKEN_DEV", "").strip()
MIXPANEL_TOKEN_STAGE = os.environ.get("MIXPANEL_TOKEN_STAGE", "").strip()
MIXPANEL_TOKEN_PROD = os.environ.get("MIXPANEL_TOKEN_PROD", "").strip()
SSL_CTX = ssl.create_default_context()

LANDING_ALERT_TG_BOT_TOKEN = (
    os.environ.get("LANDING_ALERT_TG_BOT_TOKEN", "").strip()
    or os.environ.get("LANDING_TG_BOT_TOKEN", "").strip()
    or os.environ.get("TG_BOT_TOKEN", "").strip()
)
LANDING_ALERT_TG_CHAT_ID = (
    os.environ.get("LANDING_ALERT_TG_CHAT_ID", "").strip()
    or os.environ.get("LANDING_TG_CHAT_ID", "").strip()
    or os.environ.get("TG_CHAT_ID", "").strip()
)
LANDING_ALERTS_ENABLED = os.environ.get("LANDING_ALERTS_ENABLED", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LANDING_ALERT_VISIT_EVENT = "landing_view"
LANDING_ALERT_ERROR_SUFFIX = "_error"
TELEGRAM_SEND_MESSAGE_URL_TMPL = "https://api.telegram.org/bot{token}/sendMessage"

ANALYTICS_BASIC_USER = os.environ.get("ANALYTICS_BASIC_USER", "owner").strip()
_ANALYTICS_BASIC_PASSWORD = os.environ.get("ANALYTICS_BASIC_PASSWORD", "").strip()
_ANALYTICS_BASIC_PASSWORD_HASH = os.environ.get("ANALYTICS_BASIC_PASSWORD_HASH", "").strip().lower()

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "owner@broox.group").strip().lower()
OWNER_USER_ID = os.environ.get("OWNER_USER_ID", "owner").strip()

ANALYTICS_IP_ALLOWLIST_ENABLED = os.environ.get("ANALYTICS_IP_ALLOWLIST_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ANALYTICS_IP_ALLOWLIST = {
    item.strip() for item in os.environ.get("ANALYTICS_IP_ALLOWLIST", "").split(",") if item.strip()
}

ANALYTICS_AUTH_MAX_ATTEMPTS = max(1, int(os.environ.get("ANALYTICS_AUTH_MAX_ATTEMPTS", "6")))
ANALYTICS_AUTH_WINDOW_SEC = max(30, int(os.environ.get("ANALYTICS_AUTH_WINDOW_SEC", "300")))
ANALYTICS_AUTH_LOCKOUT_SEC = max(30, int(os.environ.get("ANALYTICS_AUTH_LOCKOUT_SEC", "900")))
ANALYTICS_SESSION_TTL_SEC = max(60, int(os.environ.get("ANALYTICS_SESSION_TTL_SEC", "43200")))
ANALYTICS_SESSION_COOKIE = "analytics_owner_session"
ANALYTICS_SESSION_SECRET = os.environ.get("ANALYTICS_SESSION_SECRET", secrets.token_hex(32))

# In-memory anti-bruteforce state
_FAILED_AUTH: dict[str, list[float]] = {}
_LOCKED_UNTIL: dict[str, float] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_password_hash(raw: str, plain: str) -> str:
    if raw:
        normalized = raw.strip().lower()
        if normalized.startswith("sha256$"):
            return normalized.split("$", 1)[1]
        return normalized
    if plain:
        return _sha256_hex(plain)
    return ""


ANALYTICS_BASIC_PASSWORD_HASH = _normalize_password_hash(_ANALYTICS_BASIC_PASSWORD_HASH, _ANALYTICS_BASIC_PASSWORD)


def _safe_json_dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _append_jsonl(file_path: Path, payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as file:
        file.write(_safe_json_dumps(payload) + "\n")


def _log_access(route: str, ip: str, result: str, reason: str) -> None:
    _append_jsonl(
        ANALYTICS_ACCESS_LOG_FILE,
        {
            "timestamp": _now_iso(),
            "route": route,
            "ip": ip,
            "result": result,
            "reason": reason,
        },
    )


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
    _append_jsonl(ANALYTICS_DEBUG_FILE, entry)


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


def _sanitize_event_for_output(event: dict) -> dict:
    sanitized = dict(event)
    props = dict(sanitized.get("props", {}))
    if "email" in props:
        props["email"] = "[redacted]"
    sanitized["props"] = props
    return sanitized


def _resolve_mixpanel_token(props: dict) -> str:
    page_url = str(props.get("page_url", "")).strip().lower()
    host = ""
    if page_url:
        try:
            host = (urlparse(page_url).hostname or "").lower()
        except ValueError:
            host = ""

    if host in {"localhost", "127.0.0.1"} or host.endswith(".local"):
        return MIXPANEL_TOKEN_STAGE or MIXPANEL_TOKEN_DEV

    if "stage" in host or "staging" in host:
        return MIXPANEL_TOKEN_STAGE or MIXPANEL_TOKEN_DEV

    return MIXPANEL_TOKEN_PROD or MIXPANEL_TOKEN_STAGE or MIXPANEL_TOKEN_DEV


def _forward_to_mixpanel(event_name: str, props: dict) -> tuple[bool, str]:
    token = _resolve_mixpanel_token(props)
    if not token:
        return False, "missing_mixpanel_token"

    payload = {
        "event": event_name,
        "properties": {
            "token": token,
            **props,
        },
    }

    encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode({"data": encoded}).encode("utf-8")
    req = urllib.request.Request(
        MIXPANEL_TRACK_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=1.5, context=SSL_CTX) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            if attempt == 1:
                return False, f"url_error:{exc.reason}"
            continue
        except Exception as exc:
            if attempt == 1:
                return False, f"unexpected:{exc}"
            continue

        try:
            parsed = json.loads(raw)
            status = int(parsed.get("status", 0))
            if status == 1:
                return True, ""
            if attempt == 1:
                return False, f"mixpanel_status:{status}"
        except Exception:
            if raw.strip() == "1":
                return True, ""
            if attempt == 1:
                return False, f"bad_response:{raw[:120]}"

    return False, "unknown_failure"


def _forward_to_mixpanel_async(event_name: str, props: dict) -> None:
    def _worker() -> None:
        ok, err = _forward_to_mixpanel(event_name, props)
        if not ok:
            print(f"[mixpanel-relay] failed event={event_name} err={err}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _send_telegram_message(text: str) -> tuple[bool, str]:
    if not LANDING_ALERTS_ENABLED:
        return False, "alerts_disabled"
    if not LANDING_ALERT_TG_BOT_TOKEN or not LANDING_ALERT_TG_CHAT_ID:
        return False, "telegram_not_configured"

    body = urllib.parse.urlencode(
        {
            "chat_id": LANDING_ALERT_TG_CHAT_ID,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TELEGRAM_SEND_MESSAGE_URL_TMPL.format(token=LANDING_ALERT_TG_BOT_TOKEN),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=2.5, context=SSL_CTX) as response:
            status = int(response.getcode() or 0)
            if 200 <= status < 300:
                return True, ""
            return False, f"http_status:{status}"
    except Exception as exc:
        return False, f"telegram_send_failed:{exc}"


def _send_telegram_message_async(text: str) -> None:
    def _worker() -> None:
        ok, err = _send_telegram_message(text)
        if not ok:
            print(f"[landing-alert] failed err={err}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def _format_landing_alert_title(kind: str) -> str:
    if kind == "visit":
        return "[Landing] Новое посещение"
    if kind == "lead":
        return "[Landing] Оставил почту"
    return "[Landing] Критическая ошибка"


def _format_landing_alert(kind: str, details: dict[str, str]) -> str:
    title = _format_landing_alert_title(kind)
    lines = [title]
    for key, value in details.items():
        safe = str(value).strip()
        if not safe:
            continue
        lines.append(f"{key}: {safe}")
    return "\n".join(lines)


def _notify_landing_event(event_name: str, props: dict, remote_addr: str) -> None:
    kind = ""
    details: dict[str, str] = {
        "event": event_name,
        "ip": remote_addr,
    }
    country = str(props.get("country", "")).strip()
    if country:
        details["country"] = country

    if event_name == LANDING_ALERT_VISIT_EVENT:
        kind = "visit"
        details["page"] = str(props.get("page_url", "")).strip()
        details["utm_source"] = str(props.get("utm_source", "")).strip()
    elif event_name.endswith(LANDING_ALERT_ERROR_SUFFIX):
        kind = "error"
        details["error_type"] = str(props.get("error_type", "")).strip()
        details["error_message"] = str(props.get("error_message", "")).strip()
    else:
        return

    _send_telegram_message_async(_format_landing_alert(kind, details))


def _notify_waitlist_saved(email: str, source: str, submitted_at: str, remote_addr: str) -> None:
    alert = _format_landing_alert(
        "lead",
        {
            "email": email,
            "source": source,
            "submitted_at": submitted_at,
            "ip": remote_addr,
        },
    )
    _send_telegram_message_async(alert)


def _issue_owner_session(identity: str) -> str:
    exp = int(time.time()) + ANALYTICS_SESSION_TTL_SEC
    payload = {"identity": identity, "exp": exp}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    sig = hmac.new(ANALYTICS_SESSION_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _parse_cookie(cookie_header: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for pair in cookie_header.split(";"):
        pair = pair.strip()
        if not pair or "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def _verify_owner_session(cookie_header: str) -> tuple[bool, str]:
    cookies = _parse_cookie(cookie_header)
    token = cookies.get(ANALYTICS_SESSION_COOKIE, "")
    if not token or "." not in token:
        return False, "missing_session"

    body, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(ANALYTICS_SESSION_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False, "invalid_session_sig"

    try:
        payload_raw = base64.urlsafe_b64decode(body.encode("ascii")).decode("utf-8")
        payload = json.loads(payload_raw)
    except Exception:
        return False, "invalid_session_payload"

    identity = str(payload.get("identity", "")).strip()
    exp = int(payload.get("exp", 0))
    if not identity or exp <= int(time.time()):
        return False, "expired_session"

    owner_ok = identity == OWNER_USER_ID or identity.lower() == OWNER_EMAIL
    if not owner_ok:
        return False, "not_owner"

    return True, identity


def _client_ip(handler: SimpleHTTPRequestHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return handler.client_address[0] if handler.client_address else "unknown"


def _ip_allowed(ip: str) -> bool:
    if not ANALYTICS_IP_ALLOWLIST_ENABLED:
        return True
    return ip in ANALYTICS_IP_ALLOWLIST


def _is_locked(ip: str) -> bool:
    now = time.time()
    until = _LOCKED_UNTIL.get(ip, 0)
    return until > now


def _record_auth_failure(ip: str) -> None:
    now = time.time()
    history = [ts for ts in _FAILED_AUTH.get(ip, []) if now - ts <= ANALYTICS_AUTH_WINDOW_SEC]
    history.append(now)
    _FAILED_AUTH[ip] = history

    if len(history) >= ANALYTICS_AUTH_MAX_ATTEMPTS:
        _LOCKED_UNTIL[ip] = now + ANALYTICS_AUTH_LOCKOUT_SEC
        _FAILED_AUTH[ip] = []


def _record_auth_success(ip: str) -> None:
    _FAILED_AUTH.pop(ip, None)
    _LOCKED_UNTIL.pop(ip, None)


def _extract_basic_credentials(auth_header: str) -> tuple[str, str] | None:
    if not auth_header or not auth_header.startswith("Basic "):
        return None

    encoded = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        return None

    if ":" not in decoded:
        return None

    username, password = decoded.split(":", 1)
    return username, password


def _validate_basic_auth(auth_header: str) -> tuple[bool, str]:
    credentials = _extract_basic_credentials(auth_header)
    if not credentials:
        return False, "missing_or_invalid_basic"

    username, password = credentials
    if username != ANALYTICS_BASIC_USER:
        return False, "auth_failed"

    if not ANALYTICS_BASIC_PASSWORD_HASH:
        return False, "auth_config_missing"

    incoming = _sha256_hex(password)
    if not hmac.compare_digest(incoming, ANALYTICS_BASIC_PASSWORD_HASH):
        return False, "auth_failed"

    return True, username


class LandingHandler(SimpleHTTPRequestHandler):
    server_version = "LandingServer/2.0"

    def list_directory(self, path: str):
        self._send_error_json(HTTPStatus.FORBIDDEN, "Directory listing disabled")
        return None

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        super().end_headers()

    def _send_security_headers_for_analytics(self) -> None:
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self';",
        )

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

    def _send_html(self, code: int, html: str, analytics_csp: bool = False, extra_headers: dict[str, str] | None = None) -> None:
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if analytics_csp:
            self._send_security_headers_for_analytics()
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, code: int, message: str) -> None:
        self._send_json(code, {"ok": False, "error": message})

    def _read_json_payload(self) -> tuple[dict | None, str | None]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None, "invalid_content_length"

        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None, "invalid_json"

        if not isinstance(payload, dict):
            return None, "json_body_must_be_object"

        return payload, None

    def _build_analytics_page(self, events: list[dict]) -> str:
        rows: list[str] = []
        for idx, event in enumerate(reversed(events), start=1):
            # PII minimization in UI: strip raw email from rendered props
            props = dict(event.get("props", {}))
            if "email" in props:
                props["email"] = "[redacted]"
            props_json = json.dumps(props, ensure_ascii=False, indent=2)
            rows.append(
                "<tr>"
                f"<td>{idx}</td>"
                f"<td>{event.get('received_at', '')}</td>"
                f"<td>{event.get('event_name', '')}</td>"
                f"<td>{event.get('mixpanel_forwarded', '')}</td>"
                f"<td>{event.get('mixpanel_error', '')}</td>"
                f"<td><details><summary>props</summary><pre>{props_json}</pre></details></td>"
                "</tr>"
            )

        table_rows = "\n".join(rows) if rows else "<tr><td colspan='6'>No events yet</td></tr>"
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Private Analytics</title>
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
    button {{ margin-left:12px;padding:6px 10px;border-radius:8px;border:1px solid #405097;background:#1e295c;color:#e4ebff;cursor:pointer; }}
  </style>
</head>
<body>
  <h1>Private Landing Analytics</h1>
  <div class=\"meta\">
    Events: {len(events)} | API: <code>/api/v1/analytics/events?pretty=1</code>
    <button id=\"clear-events-btn\" type=\"button\">Clear events</button>
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>received_at</th>
        <th>event_name</th>
        <th>forward</th>
        <th>forward_error</th>
        <th>props</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
  <script>
    const clearBtn = document.getElementById('clear-events-btn');
    clearBtn?.addEventListener('click', async () => {{
      const ok = window.confirm('Clear analytics events?');
      if (!ok) return;
      clearBtn.disabled = true;
      const res = await fetch('/api/v1/analytics/clear', {{ method: 'POST', credentials: 'same-origin' }});
      if (res.ok) {{ window.location.reload(); return; }}
      alert('Failed to clear events');
      clearBtn.disabled = false;
    }});
  </script>
</body>
</html>"""

    def _require_analytics_page_auth(self, route: str) -> tuple[bool, str, dict[str, str]]:
        ip = _client_ip(self)

        if not _ip_allowed(ip):
            _log_access(route, ip, "denied", "ip_blocked")
            return False, "ip_blocked", {}

        if _is_locked(ip):
            _log_access(route, ip, "denied", "lockout")
            return False, "auth_failed", {}

        ok, detail = _validate_basic_auth(self.headers.get("Authorization", ""))
        if not ok:
            _record_auth_failure(ip)
            _log_access(route, ip, "denied", detail)
            headers = {"WWW-Authenticate": 'Basic realm="Private Analytics"'}
            return False, "auth_failed", headers

        _record_auth_success(ip)
        identity = detail
        session = _issue_owner_session(identity)
        _log_access(route, ip, "allowed", "ok")
        return True, "ok", {
            "Set-Cookie": f"{ANALYTICS_SESSION_COOKIE}={session}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age={ANALYTICS_SESSION_TTL_SEC}"
        }

    def _require_analytics_api_auth(self, route: str) -> tuple[bool, str]:
        ip = _client_ip(self)

        if not _ip_allowed(ip):
            _log_access(route, ip, "denied", "ip_blocked")
            return False, "ip_blocked"

        ok, reason = _verify_owner_session(self.headers.get("Cookie", ""))
        if not ok:
            _log_access(route, ip, "denied", reason)
            return False, reason

        _log_access(route, ip, "allowed", "ok")
        return True, "ok"

    def _handle_waitlist(self) -> None:
        payload, error = self._read_json_payload()
        if error:
            self._send_error_json(400, error)
            return

        assert payload is not None
        email = str(payload.get("email", "")).strip().lower()
        source = str(payload.get("source", "landing"))
        submitted_at = str(payload.get("submitted_at", "")).strip()

        if not EMAIL_PATTERN.match(email):
            self._send_error_json(400, "invalid_email")
            return

        if not submitted_at:
            submitted_at = _now_iso()

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
        _notify_waitlist_saved(
            email=email,
            source=source,
            submitted_at=submitted_at,
            remote_addr=_client_ip(self),
        )

        self._send_json(200, {"ok": True, "saved": True})

    def _handle_analytics_ingest(self) -> None:
        payload, error = self._read_json_payload()
        if error:
            self._send_error_json(400, error)
            return

        assert payload is not None
        event_name = str(payload.get("event_name", "")).strip()
        props = payload.get("props")

        if not event_name:
            self._send_error_json(400, "event_name_required")
            return
        if not isinstance(props, dict):
            self._send_error_json(400, "props_must_be_object")
            return

        _forward_to_mixpanel_async(event_name, props)
        entry = {
            "received_at": _now_iso(),
            "event_name": event_name,
            "props": props,
            "user_agent": self.headers.get("User-Agent", ""),
            "remote_addr": _client_ip(self),
            "mixpanel_forwarded": "queued",
            "mixpanel_error": "",
        }
        _append_analytics_debug(entry)
        _notify_landing_event(event_name=event_name, props=props, remote_addr=entry["remote_addr"])
        self._send_json(
            200,
            {
                "ok": True,
                "saved": True,
                "mixpanel_forwarded": "queued",
                "mixpanel_error": "",
            },
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        # Private analytics page
        if route == "/analytics":
            ok, reason, headers = self._require_analytics_page_auth(route)
            if not ok:
                status = HTTPStatus.FORBIDDEN if reason == "ip_blocked" else HTTPStatus.UNAUTHORIZED
                self._send_html(status, "<h1>Access denied</h1>", analytics_csp=True, extra_headers=headers)
                return

            events = _read_analytics_debug(limit=300)
            self._send_html(200, self._build_analytics_page(events), analytics_csp=True, extra_headers=headers)
            return

        # New private analytics API
        if route.startswith("/api/v1/analytics/"):
            ok, reason = self._require_analytics_api_auth(route)
            if not ok:
                status = HTTPStatus.FORBIDDEN
                self._send_error_json(status, reason)
                return

            if route == "/api/v1/analytics/events":
                query = parse_qs(parsed.query)
                try:
                    limit = int((query.get("limit") or ["120"])[0])
                except ValueError:
                    limit = 120
                limit = max(1, min(limit, 1000))
                events = _read_analytics_debug(limit=limit)
                sanitized = [_sanitize_event_for_output(item) for item in events]
                payload = {"ok": True, "count": len(sanitized), "events": sanitized}
                if (query.get("pretty") or ["0"])[0] in {"1", "true", "yes"}:
                    self._send_json_pretty(200, payload)
                else:
                    self._send_json(200, payload)
                return

            if route == "/api/v1/analytics/summary":
                events = _read_analytics_debug(limit=1000)
                event_names: dict[str, int] = {}
                for item in events:
                    name = str(item.get("event_name", "unknown"))
                    event_names[name] = event_names.get(name, 0) + 1
                self._send_json(200, {"ok": True, "count": len(events), "event_names": event_names})
                return

            self._send_error_json(404, "not_found")
            return

        # Legacy analytics endpoints are now blocked from direct public access.
        if route in {"/api/analytics-debug", "/api/analytics-debug/view"}:
            self._send_error_json(403, "legacy_analytics_endpoint_blocked")
            return

        super().do_GET()

    def do_POST(self) -> None:
        route = self.path

        if route == "/api/waitlist":
            self._handle_waitlist()
            return

        # public ingest endpoint used by frontend
        if route == "/api/analytics-debug":
            self._handle_analytics_ingest()
            return

        if route.startswith("/api/v1/analytics/"):
            ok, reason = self._require_analytics_api_auth(route)
            if not ok:
                self._send_error_json(403, reason)
                return

            if route == "/api/v1/analytics/clear":
                _clear_analytics_debug()
                self._send_json(200, {"ok": True, "cleared": True})
                return

            self._send_error_json(404, "not_found")
            return

        # Legacy clear endpoint blocked.
        if route == "/api/analytics-debug/clear":
            self._send_error_json(403, "legacy_analytics_endpoint_blocked")
            return

        self._send_error_json(404, "not_found")


def create_server(host: str = "127.0.0.1", port: int = 8081) -> ThreadingHTTPServer:
    os.chdir(BASE_DIR)
    return ThreadingHTTPServer((host, port), LandingHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8081"))
    server = create_server("127.0.0.1", port)
    print(f"Landing server running on http://127.0.0.1:{port}")
    print(f"Waitlist file: {WAITLIST_FILE}")
    print(f"Analytics debug file: {ANALYTICS_DEBUG_FILE}")
    print(f"Analytics access log file: {ANALYTICS_ACCESS_LOG_FILE}")
    server.serve_forever()
