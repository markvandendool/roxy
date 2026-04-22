#!/usr/bin/env python3
"""
CitadelAction routing helpers for ROXY.

This is intentionally additive:
- clients post one shared Citadel envelope to roxy-core
- roxy-core fans out to the existing local or remote operator lanes
- backends remain the current source of execution semantics
"""

from __future__ import annotations

import json
import base64
import shlex
import subprocess
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LOCAL_PROXY_BASE = "http://127.0.0.1:9136"
MAC_PODIUM_BASE = "http://127.0.0.1:3848"
MAC_GATEWAY_BASE = "http://127.0.0.1:9136"

SECRET_TOKEN_PATH = Path.home() / ".roxy" / "secret.token"

MACHINE_SSH_TARGETS = {
    "mac-studio": "macstudio",
    "citadel-worker-1-imac": "friday",
}

REMOTE_HTTP_SCRIPT = r"""
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

cfg = json.load(sys.stdin)
url = cfg["url"]
payload = cfg.get("payload") or {}
headers = cfg.get("headers") or {}
method = cfg.get("method") or "POST"
timeout = float(cfg.get("timeout") or 15.0)

data = json.dumps(payload).encode("utf-8")
request = Request(url, data=data, method=method)
for key, value in headers.items():
    if value is None:
        continue
    request.add_header(str(key), str(value))

try:
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"message": raw or f"HTTP {response.status}"}
        print(json.dumps({"status_code": int(getattr(response, "status", 200)), "payload": parsed}))
except HTTPError as exc:
    raw = exc.read().decode("utf-8")
    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {"message": raw or str(exc)}
    print(json.dumps({"status_code": int(getattr(exc, "code", 500)), "payload": parsed}))
except URLError as exc:
    print(json.dumps({"status_code": 503, "payload": {"status": "error", "message": str(exc)}}))
except Exception as exc:
    print(json.dumps({"status_code": 500, "payload": {"status": "error", "message": str(exc)}}))
"""


def _read_roxy_token() -> Optional[str]:
    try:
        token = SECRET_TOKEN_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    return token or None


def _coerce_message(payload: Any, status_code: int) -> str:
    if isinstance(payload, dict):
        for key in ("message", "error", "status", "runId"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        result = payload.get("result")
        if result is not None:
            nested = _coerce_message(result, status_code)
            if nested:
                return nested
    elif isinstance(payload, list):
        for item in payload:
            nested = _coerce_message(item, status_code)
            if nested:
                return nested
    elif isinstance(payload, str) and payload.strip():
        return payload.strip()
    return "OK" if status_code < 400 else f"HTTP {status_code}"


def _json_request(
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 15.0,
) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update({str(k): str(v) for k, v in headers.items() if v is not None})
    request = Request(url, data=data, method="POST", headers=merged_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"message": raw or f"HTTP {response.status}"}
            return int(getattr(response, "status", 200)), parsed if isinstance(parsed, dict) else {"result": parsed}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"message": raw or str(exc)}
        return int(getattr(exc, "code", 500)), parsed if isinstance(parsed, dict) else {"result": parsed}
    except URLError as exc:
        return 503, {"status": "error", "message": str(exc)}
    except Exception as exc:
        return 500, {"status": "error", "message": str(exc)}


def _ssh_json_request(
    ssh_target: str,
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 20.0,
) -> Tuple[int, Dict[str, Any]]:
    request = {
        "url": url,
        "payload": payload,
        "headers": {"Content-Type": "application/json", **(headers or {})},
        "timeout": timeout,
    }
    loader = "import base64,sys; exec(base64.b64decode(sys.argv[1]).decode('utf-8'))"
    encoded_script = base64.b64encode(REMOTE_HTTP_SCRIPT.encode("utf-8")).decode("ascii")
    remote_command = f"python3 -c {shlex.quote(loader)} {shlex.quote(encoded_script)}"
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            ssh_target,
            remote_command,
        ],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        timeout=timeout + 5.0,
        check=False,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip() or f"ssh failed with exit {completed.returncode}"
        return 502, {"status": "error", "message": message}
    try:
        decoded = json.loads((completed.stdout or "").strip() or "{}")
    except Exception as exc:
        return 502, {"status": "error", "message": f"invalid ssh bridge response: {exc}"}
    status_code = int(decoded.get("status_code") or 500)
    payload_obj = decoded.get("payload")
    if not isinstance(payload_obj, dict):
        payload_obj = {"result": payload_obj}
    return status_code, payload_obj


def _discover_remote_gateway_token(ssh_target: str, *, port: int = 9136, timeout: float = 10.0) -> Optional[str]:
    script = (
        f'PID=$(lsof -tiTCP:{port} -sTCP:LISTEN | head -n1 || true); '
        'if [ -n "$PID" ]; then ps eww -p "$PID"; fi'
    )
    remote_command = f"sh -lc {shlex.quote(script)}"
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            ssh_target,
            remote_command,
        ],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        return None

    combined = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    for key in ("ROXY_GATEWAY_TOKEN", "PODIUM_AUTH_TOKEN"):
        match = re.search(rf"{key}=([^\s]+)", combined)
        if match and match.group(1).strip():
            return match.group(1).strip()
    return None


def _discover_remote_http_base(
    ssh_target: str,
    *,
    ports: tuple[int, ...],
    timeout: float = 8.0,
) -> str:
    probes = "; ".join(
        f'PID=$(lsof -tiTCP:{port} -sTCP:LISTEN | head -n1 || true); if [ -n "$PID" ]; then echo {port}; exit 0; fi'
        for port in ports
    )
    remote_command = f"sh -lc {shlex.quote(probes)}"
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            ssh_target,
            remote_command,
        ],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode == 0:
        detected = (completed.stdout or "").strip().splitlines()
        if detected:
            port_text = detected[-1].strip()
            if port_text.isdigit():
                return f"http://127.0.0.1:{int(port_text)}"
    return f"http://127.0.0.1:{ports[0]}"


def _attach_citadel_meta(
    action: Dict[str, Any],
    status_code: int,
    payload: Dict[str, Any],
    *,
    routed_via: str,
    target_endpoint: str,
) -> Dict[str, Any]:
    body = dict(payload)
    body["citadelAction"] = {
        "action_id": action.get("action_id"),
        "action_type": action.get("action_type"),
        "target_machine": action.get("target_machine"),
        "requested_from_surface": action.get("requested_from_surface"),
        "routed_via": routed_via,
        "target_endpoint": target_endpoint,
        "status_code": status_code,
        "ok": status_code < 400,
    }
    if "message" not in body:
        body["message"] = _coerce_message(payload, status_code)
    return body


def _route_local_proxy(action: Dict[str, Any], path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    status_code, response_payload = _json_request(f"{LOCAL_PROXY_BASE}{path}", payload)
    return {
        "http_status": status_code,
        "body": _attach_citadel_meta(
            action,
            status_code,
            response_payload,
            routed_via="local_proxy",
            target_endpoint=f"{LOCAL_PROXY_BASE}{path}",
        ),
    }


def _route_local_process(
    action: Dict[str, Any],
    argv: list[str],
    *,
    cwd: Optional[str] = None,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        response_payload: Dict[str, Any] = {
            "status": "error",
            "message": "timed out",
            "argv": argv,
        }
        status_code = 504
    except Exception as exc:
        response_payload = {
            "status": "error",
            "message": str(exc),
            "argv": argv,
        }
        status_code = 500
    else:
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        status_code = 200 if completed.returncode == 0 else 500
        response_payload = {
            "status": "ok" if completed.returncode == 0 else "error",
            "message": stdout or stderr or f"exit {completed.returncode}",
            "response": stdout,
            "stderr": stderr,
            "exit_code": completed.returncode,
            "argv": argv,
        }

    return {
        "http_status": status_code,
        "body": _attach_citadel_meta(
            action,
            status_code,
            response_payload,
            routed_via="local_process",
            target_endpoint=" ".join(argv),
        ),
    }


def _route_ssh_json(
    action: Dict[str, Any],
    ssh_target: str,
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    status_code, response_payload = _ssh_json_request(ssh_target, url, payload, headers=headers)
    return {
        "http_status": status_code,
        "body": _attach_citadel_meta(
            action,
            status_code,
            response_payload,
            routed_via=f"ssh:{ssh_target}",
            target_endpoint=url,
        ),
    }


def _unsupported(action: Dict[str, Any], message: str, *, status_code: int = 501) -> Dict[str, Any]:
    return {
        "http_status": status_code,
        "body": {
            "status": "error",
            "message": message,
            "citadelAction": {
                "action_id": action.get("action_id"),
                "action_type": action.get("action_type"),
                "target_machine": action.get("target_machine"),
                "requested_from_surface": action.get("requested_from_surface"),
                "status_code": status_code,
                "ok": False,
            },
        },
    }


def _route_command_run(action: Dict[str, Any]) -> Dict[str, Any]:
    target_machine = str(action.get("target_machine") or "").strip()
    target_scope = action.get("target_scope") or {}
    payload = dict(action.get("payload") or {})
    dispatch_path = str(target_scope.get("dispatch_path") or payload.get("dispatchPath") or "").strip().lower()

    if target_machine == "roxy-macpro":
        if dispatch_path == "gateway_command":
            gateway_payload = {
                "text": payload.get("text") or "",
                **({"confirm": True} if payload.get("confirm") is True else {}),
                **({"confirmToken": payload.get("confirmToken")} if payload.get("confirmToken") else {}),
            }
            return _route_local_proxy(action, "/api/roxy/command", gateway_payload)

        if dispatch_path in {"run_launch", ""}:
            return _route_local_proxy(action, "/api/runs", payload)

        return _unsupported(action, f"Unsupported command.run dispatch_path for roxy-macpro: {dispatch_path}", status_code=400)

    ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
    if not ssh_target:
        return _unsupported(action, f"Unsupported target_machine for command.run: {target_machine}", status_code=400)

    if dispatch_path == "gateway_command":
        gateway_payload = {
            "text": payload.get("text") or "",
            **({"confirm": True} if payload.get("confirm") is True else {}),
            **({"confirmToken": payload.get("confirmToken")} if payload.get("confirmToken") else {}),
        }
        headers: Dict[str, str] = {}
        gateway_token = _discover_remote_gateway_token(ssh_target)
        if gateway_token:
            headers["Authorization"] = f"Bearer {gateway_token}"
        return _route_ssh_json(
            action,
            ssh_target,
            f"{MAC_GATEWAY_BASE}/api/roxy/command",
            gateway_payload,
            headers=headers or None,
        )

    if dispatch_path in {"run_launch", ""}:
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _route_ssh_json(
            action,
            ssh_target,
            f"{podium_base}/api/operator/run/launch",
            payload,
            headers={"X-Citadel-Hop": "1"},
        )

    return _unsupported(action, f"Unsupported command.run dispatch_path for {target_machine}: {dispatch_path}", status_code=400)


def route_citadel_action(action: Dict[str, Any]) -> Dict[str, Any]:
    action_type = str(action.get("action_type") or "").strip()
    target_machine = str(action.get("target_machine") or "").strip()
    payload = dict(action.get("payload") or {})

    if action_type == "command.run":
        return _route_command_run(action)

    if action_type == "email.send":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _unsupported(action, f"email.send requires an SSH-routable target_machine, got: {target_machine}", status_code=400)
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _route_ssh_json(
            action,
            ssh_target,
            f"{podium_base}/api/operator/email/send",
            payload,
            headers={"X-Citadel-Hop": "1"},
        )

    if action_type == "recording.start":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _unsupported(action, f"recording.start requires an SSH-routable target_machine, got: {target_machine}", status_code=400)
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _route_ssh_json(
            action,
            ssh_target,
            f"{podium_base}/api/operator/recording/start",
            payload,
            headers={"X-Citadel-Hop": "1"},
        )

    if action_type == "recording.stop":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _unsupported(action, f"recording.stop requires an SSH-routable target_machine, got: {target_machine}", status_code=400)
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _route_ssh_json(
            action,
            ssh_target,
            f"{podium_base}/api/operator/recording/stop",
            payload,
            headers={"X-Citadel-Hop": "1"},
        )

    if action_type == "mobile.alert.ack":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _unsupported(action, f"mobile.alert.ack requires an SSH-routable target_machine, got: {target_machine}", status_code=400)
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _route_ssh_json(
            action,
            ssh_target,
            f"{podium_base}/api/operator/alerts/ack",
            payload,
            headers={"X-Citadel-Hop": "1"},
        )

    if action_type == "repo.status":
        repo_path = payload.get("repo_path") or ""
        argv = ["git"]
        if repo_path:
            argv.extend(["-C", str(repo_path)])
        argv.extend(["status", "--short", "--branch"])
        return _route_local_process(action, argv)

    if action_type == "repo.push":
        repo_path = payload.get("repo_path") or ""
        argv = ["git"]
        if repo_path:
            argv.extend(["-C", str(repo_path)])
        argv.append("push")
        return _route_local_process(action, argv, timeout=60.0)

    return _unsupported(action, f"CitadelAction routing is not implemented yet for {action_type}")
