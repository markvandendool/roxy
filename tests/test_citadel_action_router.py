import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))

import citadel_action_router


def test_command_run_gateway_command_routes_to_local_proxy(monkeypatch):
    captured = {}

    def fake_json_request(url, payload, headers=None, timeout=15.0):
        captured["url"] = url
        captured["payload"] = payload
        return 200, {"status": "pending_confirm", "message": "Confirmation required", "needsConfirm": True, "confirmToken": "tok-123"}

    monkeypatch.setattr(citadel_action_router, "_json_request", fake_json_request)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-1",
            "action_type": "command.run",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "target_scope": {"dispatch_path": "gateway_command"},
            "payload": {"text": "enqueue story AIL-001", "confirm": True, "confirmToken": "tok-123"},
        }
    )

    assert captured["url"] == "http://127.0.0.1:9136/api/roxy/command"
    assert captured["payload"]["text"] == "enqueue story AIL-001"
    assert result["http_status"] == 200
    assert result["body"]["needsConfirm"] is True
    assert result["body"]["citadelAction"]["routed_via"] == "local_proxy"


def test_command_run_gateway_command_routes_to_mac_gateway_with_auth(monkeypatch):
    captured = {}

    def fake_discover_remote_gateway_token(ssh_target, port=9136, timeout=10.0):
        captured["token_lookup_target"] = ssh_target
        return "tok-mac-123"

    def fake_ssh_json_request(ssh_target, url, payload, headers=None, timeout=20.0):
        captured["ssh_target"] = ssh_target
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return 200, {"status": "success", "message": "READY"}

    monkeypatch.setattr(citadel_action_router, "_discover_remote_gateway_token", fake_discover_remote_gateway_token)
    monkeypatch.setattr(citadel_action_router, "_ssh_json_request", fake_ssh_json_request)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-1b",
            "action_type": "command.run",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "target_scope": {"dispatch_path": "gateway_command"},
            "payload": {"text": "Reply only with READY."},
        }
    )

    assert captured["token_lookup_target"] == "macstudio"
    assert captured["url"] == "http://127.0.0.1:9136/api/roxy/command"
    assert captured["headers"] == {"Authorization": "Bearer tok-mac-123"}
    assert result["http_status"] == 200
    assert result["body"]["message"] == "READY"


def test_command_run_run_launch_routes_to_mac_podium_via_ssh(monkeypatch):
    captured = {}

    def fake_discover_remote_podium_headers(ssh_target):
        captured["header_lookup_target"] = ssh_target
        return {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-mac-123"}

    def fake_ssh_json_request(ssh_target, url, payload, headers=None, timeout=20.0):
        captured["ssh_target"] = ssh_target
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return 200, {"status": "pending_confirm", "message": "Confirmation required to enqueue story.", "runId": "run-123", "needsConfirm": True, "confirmToken": "confirm-xyz"}

    monkeypatch.setattr(citadel_action_router, "_ssh_json_request", fake_ssh_json_request)
    monkeypatch.setattr(citadel_action_router, "_discover_remote_http_base", lambda ssh_target, ports=(3848, 3847), timeout=8.0: "http://127.0.0.1:3848")
    monkeypatch.setattr(citadel_action_router, "_discover_remote_podium_headers", fake_discover_remote_podium_headers)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-2",
            "action_type": "command.run",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "target_scope": {"dispatch_path": "run_launch"},
            "payload": {
                "text": "prepare apply PLAN-001",
                "host": "roxy",
                "executionTarget": "codex",
                "confirm": False,
            },
        }
    )

    assert captured["ssh_target"] == "macstudio"
    assert captured["url"] == "http://127.0.0.1:3848/api/operator/run/launch"
    assert captured["payload"]["text"] == "prepare apply PLAN-001"
    assert captured["payload"]["host"] == "roxy"
    assert captured["header_lookup_target"] == "macstudio"
    assert captured["headers"] == {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-mac-123"}
    assert result["body"]["runId"] == "run-123"
    assert result["body"]["citadelAction"]["routed_via"] == "ssh:macstudio"


def test_email_send_routes_to_mac_podium_via_ssh(monkeypatch):
    captured = {}

    def fake_discover_remote_podium_headers(ssh_target):
        captured["header_lookup_target"] = ssh_target
        return {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-mail-123"}

    def fake_ssh_json_request(ssh_target, url, payload, headers=None, timeout=20.0):
        captured["ssh_target"] = ssh_target
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return 200, {"success": True, "message": "Sent"}

    monkeypatch.setattr(citadel_action_router, "_ssh_json_request", fake_ssh_json_request)
    monkeypatch.setattr(citadel_action_router, "_discover_remote_http_base", lambda ssh_target, ports=(3848, 3847), timeout=8.0: "http://127.0.0.1:3848")
    monkeypatch.setattr(citadel_action_router, "_discover_remote_podium_headers", fake_discover_remote_podium_headers)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-3",
            "action_type": "email.send",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {
                "account": "gmail",
                "to": ["test@example.com"],
                "subject": "Test",
                "body": "Hello",
            },
        }
    )

    assert captured["url"] == "http://127.0.0.1:3848/api/operator/email/send"
    assert captured["payload"]["account"] == "gmail"
    assert captured["header_lookup_target"] == "macstudio"
    assert captured["headers"] == {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-mail-123"}
    assert result["http_status"] == 200
    assert result["body"]["citadelAction"]["target_machine"] == "mac-studio"


def test_recording_start_routes_to_mac_podium_with_auth(monkeypatch):
    captured = {}

    def fake_discover_remote_podium_headers(ssh_target):
        captured["header_lookup_target"] = ssh_target
        return {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-rec-123"}

    def fake_ssh_json_request(ssh_target, url, payload, headers=None, timeout=20.0):
        captured["ssh_target"] = ssh_target
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return 200, {"status": "success", "message": "Started OBS recording"}

    monkeypatch.setattr(citadel_action_router, "_ssh_json_request", fake_ssh_json_request)
    monkeypatch.setattr(citadel_action_router, "_discover_remote_http_base", lambda ssh_target, ports=(3848, 3847), timeout=8.0: "http://127.0.0.1:3848")
    monkeypatch.setattr(citadel_action_router, "_discover_remote_podium_headers", fake_discover_remote_podium_headers)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-3b",
            "action_type": "recording.start",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"profile": "theater-8k"},
        }
    )

    assert captured["ssh_target"] == "macstudio"
    assert captured["url"] == "http://127.0.0.1:3848/api/operator/recording/start"
    assert captured["payload"]["profile"] == "theater-8k"
    assert captured["header_lookup_target"] == "macstudio"
    assert captured["headers"] == {"X-Citadel-Hop": "1", "Authorization": "Bearer tok-rec-123"}
    assert result["http_status"] == 200
    assert result["body"]["message"] == "Started OBS recording"


def test_repo_status_routes_to_local_process(monkeypatch):
    captured = {}

    def fake_local_process(action, argv, cwd=None, timeout=20.0):
        captured["argv"] = argv
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return {
            "http_status": 200,
            "body": {
                "status": "ok",
                "message": "## main",
                "response": "## main\n M roxy_core.py",
                "citadelAction": {"routed_via": "local_process"},
            },
        }

    monkeypatch.setattr(citadel_action_router, "_route_local_process", fake_local_process)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-4",
            "action_type": "repo.status",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"repo_path": "/home/mark/.roxy"},
        }
    )

    assert captured["argv"] == ["git", "-C", "/home/mark/.roxy", "status", "--short", "--branch"]
    assert result["http_status"] == 200
    assert result["body"]["citadelAction"]["routed_via"] == "local_process"
