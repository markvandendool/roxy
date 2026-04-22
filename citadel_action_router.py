#!/usr/bin/env python3
"""
CitadelAction routing helpers for ROXY.

This is intentionally additive:
- clients post one shared Citadel envelope to roxy-core
- roxy-core fans out to the existing local or remote operator lanes
- backends remain the current source of execution semantics
"""

from __future__ import annotations

import base64
import json
import re
import shlex
import subprocess
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from citadel_event_log import (
    append_event,
    append_worker_dispatch,
    claim_device,
    load_authority_state,
    release_device,
)


LOCAL_PROXY_BASE = "http://127.0.0.1:9136"
MAC_GATEWAY_BASE = "http://127.0.0.1:9136"

MACHINE_SSH_TARGETS = {
    "mac-studio": "macstudio",
    "citadel-worker-1-imac": "friday",
}

MAC_LUNO_ROOT = "/Users/markvandendool/mindsong-juke-hub/luno-orchestrator"

ROXY_SERVICE_UNITS = {
    "gitnexus": "gitnexus.service",
    "gitnexus-analyze": "gitnexus-analyze-mindsong.service",
    "gitnexus-analyze-mindsong": "gitnexus-analyze-mindsong.service",
}

MAC_SERVICE_COMMANDS = {
    "operator-stack": ["bun", "run", "scripts/operator-supervisor.ts", "restart"],
    "operator-bar": ["sh", "-lc", "launchctl kickstart -k gui/$(id -u)/com.mindsong.operator-bar"],
    "operator-mirror": ["sh", "-lc", "launchctl kickstart -k gui/$(id -u)/com.mindsong.operator-mirror"],
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


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


def _run_local_command(
    argv: list[str],
    *,
    cwd: Optional[str] = None,
    timeout: float = 20.0,
) -> Tuple[int, Dict[str, Any]]:
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
        return 504, {"status": "error", "message": "timed out", "argv": argv}
    except Exception as exc:
        return 500, {"status": "error", "message": str(exc), "argv": argv}

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    status_code = 200 if completed.returncode == 0 else 500
    return status_code, {
        "status": "ok" if completed.returncode == 0 else "error",
        "message": stdout or stderr or f"exit {completed.returncode}",
        "response": stdout,
        "stderr": stderr,
        "exit_code": completed.returncode,
        "argv": argv,
    }


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
    return _discover_remote_service_token(ssh_target, ports=(port,), timeout=timeout)


def _discover_remote_service_token(
    ssh_target: str,
    *,
    ports: tuple[int, ...] = (9136, 3848, 3847),
    timeout: float = 10.0,
) -> Optional[str]:
    port_checks = " ".join(str(int(port)) for port in ports)
    script = (
        f'for PORT in {port_checks}; do '
        'PID=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN | head -n1 || true); '
        'if [ -n "$PID" ]; then ps eww -p "$PID"; exit 0; fi; '
        'done'
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


def _discover_remote_podium_headers(ssh_target: str) -> Dict[str, str]:
    headers: Dict[str, str] = {"X-Citadel-Hop": "1"}
    podium_token = _discover_remote_service_token(ssh_target, ports=(3848, 3847, 9136))
    if podium_token:
        headers["Authorization"] = f"Bearer {podium_token}"
    return headers


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
    status_code, response_payload = _run_local_command(argv, cwd=cwd, timeout=timeout)
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


def _route_ssh_process(
    action: Dict[str, Any],
    ssh_target: str,
    argv: list[str],
    *,
    cwd: Optional[str] = None,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    command = shlex.join(argv)
    if cwd:
        command = f"cd {shlex.quote(cwd)} && {command}"
    status_code, response_payload = _run_local_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            ssh_target,
            "sh",
            "-lc",
            command,
        ],
        timeout=timeout,
    )
    return {
        "http_status": status_code,
        "body": _attach_citadel_meta(
            action,
            status_code,
            response_payload,
            routed_via=f"ssh:{ssh_target}",
            target_endpoint=command,
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


def _inline_result(
    action: Dict[str, Any],
    *,
    status_code: int,
    payload: Dict[str, Any],
    routed_via: str,
    target_endpoint: str,
) -> Dict[str, Any]:
    return {
        "http_status": status_code,
        "body": _attach_citadel_meta(
            action,
            status_code,
            payload,
            routed_via=routed_via,
            target_endpoint=target_endpoint,
        ),
    }


def _schedule_deferred_roxy_core_restart() -> Tuple[int, Dict[str, Any]]:
    try:
        subprocess.Popen(
            [
                "bash",
                "-lc",
                "sleep 1; systemctl --user restart roxy-core.service >/dev/null 2>&1",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return 500, {"status": "error", "message": str(exc)}
    return 202, {"status": "accepted", "message": "Deferred restart scheduled for roxy-core.service"}


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
            headers=_discover_remote_podium_headers(ssh_target),
        )

    return _unsupported(action, f"Unsupported command.run dispatch_path for {target_machine}: {dispatch_path}", status_code=400)


def _route_gitnexus_action(action: Dict[str, Any], *, resume: bool) -> Dict[str, Any]:
    payload = dict(action.get("payload") or {})
    repo_name = str(payload.get("repo_name") or payload.get("repo") or "mindsong-juke-hub").strip() or "mindsong-juke-hub"
    if repo_name != "mindsong-juke-hub":
        return _unsupported(action, f"GitNexus action currently supports only mindsong-juke-hub, got: {repo_name}", status_code=400)

    import gitnexus_client

    current_status = gitnexus_client.get_repo_status(repo_name)
    bootstrap_state = str(current_status.get("bootstrap_state") or "").strip().lower()
    if resume and bootstrap_state in {"starting", "submitted", "indexing", "reloading"}:
        return _inline_result(
            action,
            status_code=200,
            payload={
                "status": "ok",
                "message": "GitNexus analyze is already active.",
                "repo_name": repo_name,
                "gitnexus": current_status,
            },
            routed_via="local_kernel",
            target_endpoint="gitnexus.status",
        )

    verb = "start" if resume else "restart"
    status_code, response_payload = _run_local_command(
        ["systemctl", "--user", verb, "--no-block", "gitnexus-analyze-mindsong.service"],
        timeout=20.0,
    )
    refreshed_status = gitnexus_client.get_repo_status(repo_name)
    if status_code >= 400:
        response_payload["gitnexus"] = refreshed_status
        return _inline_result(
            action,
            status_code=status_code,
            payload=response_payload,
            routed_via="local_kernel",
            target_endpoint=f"systemctl --user {verb} --no-block gitnexus-analyze-mindsong.service",
        )
    return _inline_result(
        action,
        status_code=202,
        payload={
            "status": "accepted",
            "message": "GitNexus analyze requested." if not resume else "GitNexus analyze resume requested.",
            "repo_name": repo_name,
            "gitnexus": refreshed_status,
        },
        routed_via="local_kernel",
        target_endpoint=f"systemctl --user {verb} --no-block gitnexus-analyze-mindsong.service",
    )


def _route_device_claim(action: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(action.get("payload") or {})
    device_id = str(payload.get("device_id") or payload.get("deviceId") or "").strip()
    if not device_id:
        return _unsupported(action, "device.claim requires payload.device_id", status_code=400)

    owner = str(payload.get("owner") or action.get("requested_by") or "").strip()
    if not owner:
        return _unsupported(action, "device.claim requires an owner or requested_by", status_code=400)

    claims = (load_authority_state().get("claims") or {})
    existing = claims.get(device_id) if isinstance(claims, dict) else None
    force = payload.get("force") is True
    if isinstance(existing, dict) and str(existing.get("owner") or "").strip() not in {"", owner} and not force:
        return _inline_result(
            action,
            status_code=409,
            payload={
                "status": "error",
                "message": f"Device {device_id} is already claimed by {existing.get('owner')}.",
                "claim": existing,
            },
            routed_via="local_kernel",
            target_endpoint="authority_state.claims",
        )

    claim = claim_device(
        device_id,
        owner=owner,
        target_machine=str(action.get("target_machine") or "").strip() or None,
        requested_from_surface=str(action.get("requested_from_surface") or "").strip() or None,
        note=str(payload.get("note") or "").strip() or None,
    )
    return _inline_result(
        action,
        status_code=200,
        payload={
            "status": "ok",
            "message": f"Claimed device {device_id} for {owner}.",
            "claim": claim,
        },
        routed_via="local_kernel",
        target_endpoint="authority_state.claims",
    )


def _route_device_release(action: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(action.get("payload") or {})
    device_id = str(payload.get("device_id") or payload.get("deviceId") or "").strip()
    if not device_id:
        return _unsupported(action, "device.release requires payload.device_id", status_code=400)

    claims = (load_authority_state().get("claims") or {})
    existing = claims.get(device_id) if isinstance(claims, dict) else None
    if not isinstance(existing, dict):
        return _inline_result(
            action,
            status_code=404,
            payload={"status": "error", "message": f"Device {device_id} is not currently claimed."},
            routed_via="local_kernel",
            target_endpoint="authority_state.claims",
        )

    requester = str(action.get("requested_by") or "").strip()
    owner = str(existing.get("owner") or "").strip()
    force = payload.get("force") is True
    if owner and requester and owner != requester and not force:
        return _inline_result(
            action,
            status_code=409,
            payload={
                "status": "error",
                "message": f"Device {device_id} is owned by {owner}; use force to release it.",
                "claim": existing,
            },
            routed_via="local_kernel",
            target_endpoint="authority_state.claims",
        )

    released = release_device(device_id)
    return _inline_result(
        action,
        status_code=200,
        payload={
            "status": "ok",
            "message": f"Released device {device_id}.",
            "claim": released,
        },
        routed_via="local_kernel",
        target_endpoint="authority_state.claims",
    )


def _route_service_restart(action: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(action.get("payload") or {})
    target_machine = str(action.get("target_machine") or "").strip()
    service_id = str(payload.get("service_id") or payload.get("service") or "").strip().lower()
    if not service_id:
        return _unsupported(action, "service.restart requires payload.service_id", status_code=400)

    if target_machine == "roxy-macpro":
        if service_id == "roxy-core":
            status_code, response_payload = _schedule_deferred_roxy_core_restart()
            return _inline_result(
                action,
                status_code=status_code,
                payload=response_payload,
                routed_via="local_kernel",
                target_endpoint="systemctl --user restart roxy-core.service",
            )

        unit_name = ROXY_SERVICE_UNITS.get(service_id)
        if not unit_name:
            return _unsupported(action, f"Unsupported ROXY service.restart target: {service_id}", status_code=400)
        return _route_local_process(action, ["systemctl", "--user", "restart", unit_name], timeout=30.0)

    ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
    remote_command = MAC_SERVICE_COMMANDS.get(service_id)
    if ssh_target and remote_command:
        return _route_ssh_process(
            action,
            ssh_target,
            remote_command,
            cwd=MAC_LUNO_ROOT if service_id == "operator-stack" else None,
            timeout=90.0,
        )

    return _unsupported(action, f"Unsupported service.restart target: {service_id} on {target_machine}", status_code=400)


def _route_worker_dispatch(action: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(action.get("payload") or {})
    mission = str(payload.get("mission") or payload.get("text") or payload.get("task") or "").strip()
    if not mission:
        return _unsupported(action, "worker.dispatch requires payload.mission or payload.text", status_code=400)

    dispatch = append_worker_dispatch(
        {
            "dispatch_id": f"dispatch-{uuid.uuid4().hex[:12]}",
            "created_at": _now_iso(),
            "target_machine": action.get("target_machine"),
            "worker_id": payload.get("worker_id") or action.get("target_machine"),
            "mission": mission,
            "focus": payload.get("focus"),
            "repo_id": payload.get("repo_id"),
            "file_path": payload.get("file_path"),
            "requested_by": action.get("requested_by"),
            "requested_from_surface": action.get("requested_from_surface"),
            "status": "queued",
        }
    )
    return _inline_result(
        action,
        status_code=202,
        payload={
            "status": "queued",
            "message": f"Worker dispatch queued for {dispatch.get('worker_id')}.",
            "dispatch": dispatch,
        },
        routed_via="local_kernel",
        target_endpoint="worker_dispatches.jsonl",
    )


def _finalize_action(action: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    body = response.get("body") if isinstance(response, dict) else {}
    if not isinstance(body, dict):
        return response
    citadel_meta = body.get("citadelAction") if isinstance(body.get("citadelAction"), dict) else {}
    append_event(
        "citadel.action",
        status="ok" if int(response.get("http_status") or 500) < 400 else "error",
        source="roxy-core.citadel_action",
        machine_id=str(action.get("target_machine") or "").strip() or None,
        action=action,
        payload={
            "message": body.get("message"),
            "routed_via": citadel_meta.get("routed_via"),
            "target_endpoint": citadel_meta.get("target_endpoint"),
            "status_code": response.get("http_status"),
        },
        tags=["citadel", str(action.get("action_type") or "").strip()],
    )
    return response


def route_citadel_action(action: Dict[str, Any]) -> Dict[str, Any]:
    action_type = str(action.get("action_type") or "").strip()
    target_machine = str(action.get("target_machine") or "").strip()
    payload = dict(action.get("payload") or {})

    if action_type == "command.run":
        return _finalize_action(action, _route_command_run(action))

    if action_type == "email.send":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _finalize_action(
                action,
                _unsupported(action, f"email.send requires an SSH-routable target_machine, got: {target_machine}", status_code=400),
            )
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _finalize_action(
            action,
            _route_ssh_json(
                action,
                ssh_target,
                f"{podium_base}/api/operator/email/send",
                payload,
                headers=_discover_remote_podium_headers(ssh_target),
            ),
        )

    if action_type == "recording.start":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _finalize_action(
                action,
                _unsupported(action, f"recording.start requires an SSH-routable target_machine, got: {target_machine}", status_code=400),
            )
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _finalize_action(
            action,
            _route_ssh_json(
                action,
                ssh_target,
                f"{podium_base}/api/operator/recording/start",
                payload,
                headers=_discover_remote_podium_headers(ssh_target),
            ),
        )

    if action_type == "recording.stop":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _finalize_action(
                action,
                _unsupported(action, f"recording.stop requires an SSH-routable target_machine, got: {target_machine}", status_code=400),
            )
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _finalize_action(
            action,
            _route_ssh_json(
                action,
                ssh_target,
                f"{podium_base}/api/operator/recording/stop",
                payload,
                headers=_discover_remote_podium_headers(ssh_target),
            ),
        )

    if action_type == "mobile.alert.ack":
        ssh_target = MACHINE_SSH_TARGETS.get(target_machine)
        if not ssh_target:
            return _finalize_action(
                action,
                _unsupported(action, f"mobile.alert.ack requires an SSH-routable target_machine, got: {target_machine}", status_code=400),
            )
        podium_base = _discover_remote_http_base(ssh_target, ports=(3848, 3847))
        return _finalize_action(
            action,
            _route_ssh_json(
                action,
                ssh_target,
                f"{podium_base}/api/operator/alerts/ack",
                payload,
                headers=_discover_remote_podium_headers(ssh_target),
            ),
        )

    if action_type == "repo.status":
        repo_path = payload.get("repo_path") or ""
        argv = ["git"]
        if repo_path:
            argv.extend(["-C", str(repo_path)])
        argv.extend(["status", "--short", "--branch"])
        return _finalize_action(action, _route_local_process(action, argv))

    if action_type == "repo.push":
        repo_path = payload.get("repo_path") or ""
        argv = ["git"]
        if repo_path:
            argv.extend(["-C", str(repo_path)])
        argv.append("push")
        return _finalize_action(action, _route_local_process(action, argv, timeout=60.0))

    if action_type == "gitnexus.analyze":
        return _finalize_action(action, _route_gitnexus_action(action, resume=False))

    if action_type == "gitnexus.resume":
        return _finalize_action(action, _route_gitnexus_action(action, resume=True))

    if action_type == "device.claim":
        return _finalize_action(action, _route_device_claim(action))

    if action_type == "device.release":
        return _finalize_action(action, _route_device_release(action))

    if action_type == "service.restart":
        return _finalize_action(action, _route_service_restart(action))

    if action_type == "worker.dispatch":
        return _finalize_action(action, _route_worker_dispatch(action))

    return _finalize_action(
        action,
        _unsupported(action, f"CitadelAction routing is not implemented yet for {action_type}"),
    )
