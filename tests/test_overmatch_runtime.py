import asyncio
import json
from pathlib import Path
import types

import infrastructure
import mission_supervisor
import repo_intel
import roxy_core
import tool_retry
from repo_intel import RepoIndexer, query_symbol


def test_retry_controller_rotates_strategies_without_repeating_default():
    controller = tool_retry.ToolRetryController()

    first = controller.get_next_strategy("bash", "ls /nonexistent", {}, "No such file", 1)
    second = controller.get_next_strategy("bash", "ls /nonexistent", {}, "No such file", 1)

    assert first is not None
    assert first["strategy_name"] == "install_deps"
    assert second is not None
    assert second["strategy_name"] != first["strategy_name"]


def test_retry_controller_writes_fix_recipe_with_reusable_command(monkeypatch):
    captured = []

    def fake_remember_typed_record(**kwargs):
        captured.append(kwargs)
        return 1

    monkeypatch.setattr(infrastructure, "remember_typed_record", fake_remember_typed_record)

    controller = tool_retry.ToolRetryController()
    controller.record_success(
        "bash",
        "npm test",
        {},
        "command not found",
        "not_found",
        "pnpm test",
    )

    assert captured
    record = captured[0]
    assert record["record_type"] == "fix_recipe"
    assert record["metadata"]["command"] == "pnpm test"
    assert record["metadata"]["successful_command"] == "pnpm test"


def test_repo_intel_query_symbol_returns_real_file_path(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "demo.py").write_text("def load_mpc_core():\n    return 'ok'\n")

    RepoIndexer(repo_root).build(force=True)
    matches = query_symbol("load_mpc_core", repo_root=repo_root)

    assert matches
    assert matches[0]["file"] == "demo.py"
    assert matches[0]["line"] == 1


def test_build_repo_context_for_prompt_includes_file_and_symbol(monkeypatch, tmp_path):
    dummy_index = types.SimpleNamespace(
        root=str(tmp_path),
        symbol_index={"load_mpc_core": []},
    )

    monkeypatch.setattr(roxy_core, "REPO_INTEL_AVAILABLE", True)
    monkeypatch.setattr(roxy_core, "get_repo_index", lambda *args, **kwargs: dummy_index)
    monkeypatch.setattr(
        roxy_core,
        "get_file_context",
        lambda path, repo_root=None: {
            "path": "src/demo.py",
            "language": "python",
            "symbols": [{"name": "load_mpc_core", "kind": "function", "line": 7}],
            "tests": ["tests/test_demo.py"],
        } if path == "src/demo.py" else {},
    )
    monkeypatch.setattr(
        roxy_core,
        "query_symbol",
        lambda symbol, repo_root=None: [{
            "symbol": "load_mpc_core",
            "kind": "function",
            "file": "src/demo.py",
            "line": 7,
        }] if symbol == "load_mpc_core" else [],
    )

    context, meta = roxy_core._build_repo_context_for_prompt(
        "Fix src/demo.py around load_mpc_core and verify the tests."
    )

    assert "src/demo.py" in context
    assert "load_mpc_core" in context
    assert meta["repo_context_items"] >= 1


def test_mission_ledger_persists_files_in_scope_and_writes_evidence(tmp_path, monkeypatch):
    ledger_path = tmp_path / "mission_ledger.json"
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    monkeypatch.setattr(mission_supervisor, "MISSION_LEDGER", ledger_path)
    monkeypatch.setattr(mission_supervisor, "EVIDENCE_DIR", evidence_dir)

    ledger = mission_supervisor.MissionLedger()
    envelope = mission_supervisor.MissionEnvelope(
        mission_id="mission-test-1",
        story_id="TEST-001",
        story_title="Test Story",
        goal="Ship it",
        files_in_scope=["src/demo.py"],
        verification_plan=["pytest tests/test_demo.py"],
    )

    mission = ledger.create_mission(envelope)
    ledger.complete(mission.mission_id, {"result": "ok"})

    reloaded = mission_supervisor.MissionLedger()
    saved = reloaded.missions[mission.mission_id]

    assert saved.files_in_scope == ["src/demo.py"]
    artifact_path = Path(saved.evidence_bundle["artifact_path"])
    assert artifact_path.exists()


def test_mission_executor_extracts_explicit_verification_commands():
    executor = mission_supervisor.MissionExecutor()
    mission = mission_supervisor.Mission(
        mission_id="m1",
        story_id="S1",
        story_title="Story",
        status=mission_supervisor.MissionStatus.RUNNING,
        goal="goal",
        created_at=0.0,
        verification_plan=[
            "Verify: the acceptance criteria",
            "cmd: python -c \"print('ok')\"",
            "bun run test -- tests/unit/example.test.ts",
        ],
    )

    commands = executor._extract_explicit_verification_commands(mission)

    assert len(commands) == 2
    assert commands[0]["command"].startswith("python -c")
    assert commands[1]["command"].startswith("bun run test")


def test_mission_executor_derives_auto_verification_commands(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "tests").mkdir(parents=True)
    (repo_root / "package.json").write_text(json.dumps({
        "scripts": {
            "test": "bun test",
            "typecheck": "tsc --noEmit",
        }
    }))

    monkeypatch.setenv("ROXY_REPO_ROOT", str(repo_root))
    monkeypatch.setattr(
        repo_intel,
        "get_file_context",
        lambda path, repo_root=None: {
            "path": "src/foo.ts",
            "language": "typescript",
            "symbols": [{"name": "foo", "kind": "function", "line": 1}],
            "tests": ["tests/foo.test.ts"],
        },
    )

    executor = mission_supervisor.MissionExecutor()
    mission = mission_supervisor.Mission(
        mission_id="m2",
        story_id="S2",
        story_title="Story",
        status=mission_supervisor.MissionStatus.RUNNING,
        goal="goal",
        created_at=0.0,
        files_in_scope=["src/foo.ts"],
    )

    commands = executor._derive_auto_verification_commands(mission, ["src/foo.ts"])

    command_texts = [item["command"] for item in commands]
    assert any(cmd == "bun run typecheck" for cmd in command_texts)
    assert any(cmd.startswith("bun run test -- tests/foo.test.ts") for cmd in command_texts)


def test_mission_executor_execute_touches_lease(monkeypatch):
    import requests

    class FakeResponse:
        status_code = 200

        def iter_lines(self):
            payloads = [
                {"event": "tool_execution_started", "tool_name": "bash", "call_id": "abc"},
                {"event": "complete", "data": {"response": "done"}},
            ]
            for payload in payloads:
                yield b"data: " + json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse())

    touches = []
    executor = mission_supervisor.MissionExecutor()
    mission = mission_supervisor.Mission(
        mission_id="m3",
        story_id="S3",
        story_title="Story",
        status=mission_supervisor.MissionStatus.RUNNING,
        goal="goal",
        created_at=0.0,
    )

    result = asyncio.run(executor.execute(mission, lease_touch=touches.append))

    assert result["success"] is True
    assert touches


def test_mission_executor_execute_verification_stops_on_failure():
    executor = mission_supervisor.MissionExecutor()
    mission = mission_supervisor.Mission(
        mission_id="m4",
        story_id="S4",
        story_title="Story",
        status=mission_supervisor.MissionStatus.VERIFYING,
        goal="goal",
        created_at=0.0,
        verification_plan=[
            "cmd: python -c \"import sys; sys.exit(1)\"",
            "cmd: python -c \"print('should-not-run')\"",
        ],
    )

    results = asyncio.run(executor.execute_verification(mission, []))

    assert len(results) == 1
    assert results[0]["success"] is False
