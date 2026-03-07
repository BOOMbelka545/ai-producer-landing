import base64
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

SERVER_PATH = Path('/Users/leo/Desktop/Production/landing/server.py')


def load_server_module(env_overrides: dict[str, str], temp_dir: Path):
    for key, value in env_overrides.items():
        os.environ[key] = value

    spec = importlib.util.spec_from_file_location(f"landing_server_{time.time_ns()}", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.DATA_DIR = temp_dir
    module.WAITLIST_FILE = temp_dir / 'waitlist.json'
    module.ANALYTICS_DEBUG_FILE = temp_dir / 'analytics-debug.jsonl'
    module.ANALYTICS_ACCESS_LOG_FILE = temp_dir / 'analytics-access.jsonl'
    return module


class SecurityServerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir_obj = tempfile.TemporaryDirectory(prefix='landing-sec-tests-')
        self.temp_dir = Path(self.temp_dir_obj.name)

        env = {
            'ANALYTICS_BASIC_USER': 'owner',
            'ANALYTICS_BASIC_PASSWORD': 'secret-pass',
            'ANALYTICS_BASIC_PASSWORD_HASH': '',
            'OWNER_USER_ID': 'owner',
            'OWNER_EMAIL': 'owner@broox.group',
            'ANALYTICS_SESSION_SECRET': 'test-secret-123',
            'ANALYTICS_IP_ALLOWLIST_ENABLED': 'false',
            'ANALYTICS_IP_ALLOWLIST': '',
        }
        self.module = load_server_module(env, self.temp_dir)

        self.server = self.module.create_server('127.0.0.1', 0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir_obj.cleanup()

    def url(self, path: str) -> str:
        return f'http://127.0.0.1:{self.port}{path}'

    def basic_header(self, username: str, password: str) -> str:
        token = base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')
        return f'Basic {token}'

    def request(self, path: str, method='GET', headers=None, body=None, opener=None):
        req = urllib.request.Request(self.url(path), method=method)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        if body is not None:
            req.data = body
        opener = opener or urllib.request.build_opener()
        return opener.open(req, timeout=5)

    def test_public_root_is_open(self):
        with self.request('/') as resp:
            self.assertEqual(resp.status, 200)

    def test_analytics_page_requires_basic_auth(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/analytics')
        self.assertEqual(ctx.exception.code, 401)

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/analytics', headers={'Authorization': self.basic_header('owner', 'wrong')})
        self.assertEqual(ctx.exception.code, 401)

        with self.request('/analytics', headers={'Authorization': self.basic_header('owner', 'secret-pass')}) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn('set-cookie', {k.lower(): v for k, v in resp.headers.items()})

    def test_analytics_api_owner_only(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/api/v1/analytics/events')
        self.assertEqual(ctx.exception.code, 403)

        non_owner_cookie = self.module._issue_owner_session('not-owner')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/api/v1/analytics/events', headers={'Cookie': f'{self.module.ANALYTICS_SESSION_COOKIE}={non_owner_cookie}'})
        self.assertEqual(ctx.exception.code, 403)

        owner_cookie = self.module._issue_owner_session('owner')
        with self.request('/api/v1/analytics/events', headers={'Cookie': f'{self.module.ANALYTICS_SESSION_COOKIE}={owner_cookie}'}) as resp:
            self.assertEqual(resp.status, 200)

    def test_allowlist_enforced_when_enabled(self):
        self.module.ANALYTICS_IP_ALLOWLIST_ENABLED = True
        self.module.ANALYTICS_IP_ALLOWLIST = {'10.10.10.10'}

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/analytics', headers={'Authorization': self.basic_header('owner', 'secret-pass')})
        self.assertEqual(ctx.exception.code, 403)

        self.module.ANALYTICS_IP_ALLOWLIST = {'127.0.0.1'}
        with self.request('/analytics', headers={'Authorization': self.basic_header('owner', 'secret-pass')}) as resp:
            self.assertEqual(resp.status, 200)

    def test_negative_bypass_and_legacy_endpoints_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/api/v1/analytics/events?owner=true', headers={'X-Owner': 'true'})
        self.assertEqual(ctx.exception.code, 403)

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.request('/api/analytics-debug/view')
        self.assertEqual(ctx.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
