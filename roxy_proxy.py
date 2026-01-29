#!/usr/bin/env python3
"""ROXY proxy v2 - forwards requests to local ROXY core, injects X-ROXY-Token, and maps API paths."""
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import sys
import json
import time
import glob
from collections import deque
from urllib.parse import urlparse

HOME = os.path.expanduser('~')
TOKEN_PATH = os.path.join(HOME, '.roxy', 'secret.token')
if not os.path.exists(TOKEN_PATH):
    print('Missing token:', TOKEN_PATH, file=sys.stderr)
    sys.exit(1)
TOKEN = open(TOKEN_PATH).read().strip()

PORT = 9136
TARGET_BASE = 'http://127.0.0.1:8766'
LOG_DIR = os.path.join(HOME, '.roxy', 'logs')

# Map incoming proxy paths to ROXY core paths
PATH_MAP = {
    '/api/status': '/health',
    '/api/roxy/status': '/health',
    '/api/roxy/run': '/run',
    '/api/roxy/command': '/run',
    '/api/run': '/run',
    '/api/roxy/feedback': '/feedback',
    '/api/roxy/feedback/stats': '/feedback/stats',
    '/api/roxy/memory/recall': '/memory/recall',
    '/api/roxy/info': '/info',
}

DEFAULT_ACTIONS = [
    {"tool": "git_status", "status": "ready"},
    {"tool": "list_files", "status": "ready"},
    {"tool": "search_code", "status": "ready"},
]

def _tail_lines(path, max_lines=200):
    dq = deque(maxlen=max_lines)
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f:
                dq.append(line.rstrip('\n'))
    except Exception:
        return []
    return list(dq)

def _find_log_file():
    patterns = [
        os.path.join(LOG_DIR, 'roxy-core*.log'),
        os.path.join(LOG_DIR, 'roxy_core*.log'),
        os.path.join(LOG_DIR, 'roxy-core.log'),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)

def _read_recent_logs(max_lines=200):
    log_path = _find_log_file()
    if not log_path:
        return []
    lines = _tail_lines(log_path, max_lines=max_lines)
    now = time.strftime('%Y-%m-%dT%H:%M:%S')
    logs = []
    for line in lines:
        if not line.strip():
            continue
        logs.append({
            "timestamp": now,
            "event_type": "log",
            "details": line,
        })
    return logs

class Handler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _extract_token(self) -> str:
        token = (self.headers.get("X-ROXY-Token") or "").strip()
        if not token:
            auth = self.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                token = auth.split(None, 1)[1].strip()
        return token

    def _require_token(self) -> bool:
        provided = self._extract_token()
        if not provided or provided != TOKEN:
            self._send_json({"status": "error", "message": "Forbidden: Invalid or missing token"}, status=403)
            return False
        return True

    def _mapped_path(self, path):
        # split path from query
        if '?' in path:
            p,q = path.split('?',1)
            q = '?' + q
        else:
            p,q = path, ''
        mapped = PATH_MAP.get(p, p)
        return mapped + q

    def _proxy(self):
        mapped_path = self._mapped_path(self.path)
        url = TARGET_BASE + mapped_path
        method = self.command
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length) if length else None
        headers = dict(self.headers)
        headers['X-ROXY-Token'] = TOKEN
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                self.send_response(resp.getcode())
                for k,v in resp.getheaders():
                    if k.lower() == 'transfer-encoding':
                        continue
                    self.send_header(k, v)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k,v in e.headers.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization, X-ROXY-Token')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/roxy/actions':
            if not self._require_token():
                return
            timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
            actions = []
            for action in DEFAULT_ACTIONS:
                actions.append({
                    "timestamp": timestamp,
                    "tool": action["tool"],
                    "status": action.get("status"),
                    "duration": None,
                })
            self._send_json({"actions": actions, "count": len(actions)})
            return
        if path == '/api/roxy/logs':
            if not self._require_token():
                return
            logs = _read_recent_logs(max_lines=200)
            self._send_json({"logs": logs, "count": len(logs)})
            return
        self._proxy()
    def do_POST(self):
        self._proxy()
    def do_PUT(self):
        self._proxy()
    def do_DELETE(self):
        self._proxy()

if __name__ == '__main__':
    with socketserver.ThreadingTCPServer(('0.0.0.0', PORT), Handler) as httpd:
        print(f'ROXY proxy listening on 0.0.0.0:{PORT}')
        httpd.serve_forever()
