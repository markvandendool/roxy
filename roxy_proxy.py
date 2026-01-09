#!/usr/bin/env python3
"""ROXY proxy v2 - forwards requests to local ROXY core, injects X-ROXY-Token, and maps API paths."""
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import sys

HOME = os.path.expanduser('~')
TOKEN_PATH = os.path.join(HOME, '.roxy', 'secret.token')
if not os.path.exists(TOKEN_PATH):
    print('Missing token:', TOKEN_PATH, file=sys.stderr)
    sys.exit(1)
TOKEN = open(TOKEN_PATH).read().strip()

PORT = 9136
TARGET_BASE = 'http://127.0.0.1:8766'

# Map incoming proxy paths to ROXY core paths
PATH_MAP = {
    '/api/status': '/health',
    '/api/roxy/status': '/health',
    '/api/roxy/run': '/run',
    '/api/run': '/run'
}

class Handler(http.server.BaseHTTPRequestHandler):
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
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()

    def do_GET(self):
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
