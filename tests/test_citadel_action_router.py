import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path.home() / ".roxy"))

import citadel_action_router
import gitnexus_client


@pytest.fixture(autouse=True)
def suppress_event_log(monkeypatch):
    monkeypatch.setattr(citadel_action_router, "append_event", lambda *args, **kwargs: {"event_id": "evt-test"})


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


def test_gitnexus_analyze_restarts_local_service(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        gitnexus_client,
        "get_repo_status",
        lambda _repo: {"bootstrap_state": "idle", "fresh": False, "repo_name": "mindsong-juke-hub"},
    )

    def fake_run_local_command(argv, cwd=None, timeout=20.0):
        captured["argv"] = argv
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return 200, {"status": "ok", "message": "started"}

    monkeypatch.setattr(citadel_action_router, "_run_local_command", fake_run_local_command)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-5",
            "action_type": "gitnexus.analyze",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"repo_name": "mindsong-juke-hub"},
        }
    )

    assert captured["argv"] == ["systemctl", "--user", "restart", "--no-block", "gitnexus-analyze-mindsong.service"]
    assert result["http_status"] == 202
    assert result["body"]["gitnexus"]["repo_name"] == "mindsong-juke-hub"


def test_gitnexus_resume_returns_active_when_indexing(monkeypatch):
    monkeypatch.setattr(
        gitnexus_client,
        "get_repo_status",
        lambda _repo: {"bootstrap_state": "indexing", "repo_name": "mindsong-juke-hub"},
    )

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-6",
            "action_type": "gitnexus.resume",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"repo_name": "mindsong-juke-hub"},
        }
    )

    assert result["http_status"] == 200
    assert result["body"]["message"] == "GitNexus analyze is already active."


def test_device_claim_conflicts_without_force(monkeypatch):
    monkeypatch.setattr(
        citadel_action_router,
        "load_authority_state",
        lambda: {"claims": {"hid-primary": {"device_id": "hid-primary", "owner": "someone-else"}}},
    )

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-7",
            "action_type": "device.claim",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"device_id": "hid-primary"},
        }
    )

    assert result["http_status"] == 409
    assert "already claimed" in result["body"]["message"]


def test_device_release_releases_owned_device(monkeypatch):
    monkeypatch.setattr(
        citadel_action_router,
        "load_authority_state",
        lambda: {"claims": {"hid-primary": {"device_id": "hid-primary", "owner": "codex"}}},
    )
    monkeypatch.setattr(
        citadel_action_router,
        "release_device",
        lambda device_id: {"device_id": device_id, "owner": "codex"},
    )

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-8",
            "action_type": "device.release",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"device_id": "hid-primary"},
        }
    )

    assert result["http_status"] == 200
    assert result["body"]["claim"]["device_id"] == "hid-primary"


def test_worker_dispatch_queues_record(monkeypatch):
    monkeypatch.setattr(
        citadel_action_router,
        "append_worker_dispatch",
        lambda dispatch: dict(dispatch),
    )

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-9",
            "action_type": "worker.dispatch",
            "target_machine": "citadel-worker-1-imac",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"mission": "Reindex the repo graph", "focus": "gitnexus"},
        }
    )

    assert result["http_status"] == 202
    assert result["body"]["dispatch"]["mission"] == "Reindex the repo graph"
    assert result["body"]["status"] == "queued"


def test_service_restart_routes_mac_operator_stack_over_ssh(monkeypatch):
    captured = {}

    def fake_ssh_process(action, ssh_target, argv, cwd=None, timeout=60.0):
        captured["ssh_target"] = ssh_target
        captured["argv"] = argv
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return {
            "http_status": 200,
            "body": {
                "status": "ok",
                "message": "operator stack restarted",
                "citadelAction": {"routed_via": f"ssh:{ssh_target}"},
            },
        }

    monkeypatch.setattr(citadel_action_router, "_route_ssh_process", fake_ssh_process)

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-10",
            "action_type": "service.restart",
            "target_machine": "mac-studio",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"service_id": "operator-stack"},
        }
    )

    assert captured["ssh_target"] == "macstudio"
    assert captured["argv"] == ["bun", "run", "scripts/operator-supervisor.ts", "restart"]
    assert captured["cwd"].endswith("/mindsong-juke-hub/luno-orchestrator")
    assert result["http_status"] == 200


def test_service_restart_schedules_roxy_core_restart(monkeypatch):
    monkeypatch.setattr(
        citadel_action_router,
        "_schedule_deferred_roxy_core_restart",
        lambda: (202, {"status": "accepted", "message": "Deferred restart scheduled for roxy-core.service"}),
    )

    result = citadel_action_router.route_citadel_action(
        {
            "action_id": "act-11",
            "action_type": "service.restart",
            "target_machine": "roxy-macpro",
            "requested_by": "codex",
            "requested_from_surface": "operator-bar",
            "payload": {"service_id": "roxy-core"},
        }
    )

    assert result["http_status"] == 202
    assert "Deferred restart scheduled" in result["body"]["message"]
