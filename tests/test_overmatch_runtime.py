import asyncio
import json
from pathlib import Path
import time
import types

import infrastructure
import mission_supervisor
import repo_intel
import roxy_commands
import roxy_core
import story_selector
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


def test_runtime_state_snapshot_uses_cached_repo_index_without_rebuild(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("ROXY_REPO_ROOT", str(repo_root))
    monkeypatch.setattr(roxy_core, "REPO_INTEL_AVAILABLE", True)
    monkeypatch.setattr(roxy_core, "get_repo_index", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not rebuild")))
    dummy_index = types.SimpleNamespace(
        root=str(repo_root),
        file_count=12,
        symbol_index={"alpha": []},
        language_stats={"python": 3},
        built_at=time.time(),
        is_stale=lambda: False,
    )
    monkeypatch.setattr(roxy_core, "get_cached_repo_index", lambda repo_root=None: dummy_index)

    snapshot = roxy_core._get_runtime_state_snapshot()

    assert snapshot["repo_intel"]["available"] is True
    assert snapshot["repo_intel"]["file_count"] == 12


def test_runtime_state_snapshot_reports_missing_repo_intel_cache(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("ROXY_REPO_ROOT", str(repo_root))
    monkeypatch.setattr(roxy_core, "REPO_INTEL_AVAILABLE", True)
    monkeypatch.setattr(roxy_core, "get_cached_repo_index", lambda repo_root=None: None)

    snapshot = roxy_core._get_runtime_state_snapshot()

    assert snapshot["repo_intel"]["available"] is False
    assert snapshot["repo_intel"]["reason"] == "cache_missing"


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


def test_personal_memory_query_returns_profile_summary_from_verified_memory(monkeypatch):
    monkeypatch.setenv(
        "ROXY_MEMORY_CONTEXT",
        "- name: Mark\n"
        "- role: CEO of MindSong Studios\n"
        "- production_state: SkyBeam render queue with 5 videos pending\n"
        "- general_preference: electronic music\n"
        "- production_tool: SkyBeam\n",
    )

    response = roxy_commands._answer_personal_memory_query(
        "Summarize my profile from memory with no assumptions."
    )

    assert response is not None
    assert "Mark" in response
    assert "CEO of MindSong Studios" in response
    assert "SkyBeam" in response


def test_query_rag_sanitizes_backend_index_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError(
            "Error executing plan: Error sending backfill request to compactor: "
            "Error constructing hnsw segment reader"
        )

    monkeypatch.setattr(roxy_commands, "_query_rag_impl", fail)

    result = roxy_commands.query_rag("where is the theater release note?")

    assert isinstance(result, dict)
    assert result["rag_status"] == "index_unavailable"
    assert result["model_used"] == "none"
    assert "hnsw" not in result["response"].lower()
    assert "compactor" not in result["response"].lower()
    assert "temporarily unavailable" in result["response"].lower()



def test_query_fallback_collections_combines_healthy_sources():
    class FakeCollection:
        def __init__(self, name, docs, distance):
            self.name = name
            self.docs = docs
            self.distance = distance

        def query(self, **kwargs):
            return {
                "documents": [self.docs],
                "metadatas": [[{"source": f"/{self.name}.md"} for _ in self.docs]],
                "distances": [[self.distance for _ in self.docs]],
            }

    class FakeClient:
        def get_collection(self, name):
            if name == "roxy_onboarding":
                return FakeCollection(name, ["onboarding doc"], 0.4)
            if name == "roxy_api":
                return FakeCollection(name, ["api doc"], 0.8)
            raise RuntimeError("missing")

    results, used = roxy_commands._query_fallback_collections(FakeClient(), [0.1, 0.2], n_results=2)

    assert used == ["roxy_onboarding", "roxy_api"]
    assert results["documents"][0][0] == "onboarding doc"
    assert results["metadatas"][0][0]["collection"] == "roxy_onboarding"



def test_resolve_raw_query_mode_falls_back_to_technical():
    mode, config = roxy_core._resolve_raw_query_mode("not-a-real-mode")

    assert mode == "technical"
    assert config["temperature"] == roxy_core.ROXY_MODES["technical"]["temperature"]


def test_personal_memory_query_detection_prefers_memory_answering():
    assert roxy_commands._is_personal_memory_query("Who am I?") is True
    assert roxy_commands._is_personal_memory_query("What are my preferences?") is True
    assert roxy_commands._is_personal_memory_query("What does the mindsong documentation say about onboarding?") is False


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

    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/event-stream"}

        def iter_lines(self):
            payloads = [
                {"event": "tool_execution_started", "tool_name": "bash", "call_id": "abc"},
                {"event": "complete", "data": {"response": "done"}},
            ]
            for payload in payloads:
                yield b"data: " + json.dumps(payload).encode("utf-8")

    def fake_request(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_request)

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
    assert captured["url"].endswith("/stream")
    assert captured["params"]["command"].startswith("/deep ")
    assert result["trace_path"].endswith("m3.jsonl")


def test_mission_executor_execute_verification_stops_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("ROXY_REPO_ROOT", str(tmp_path))
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


def test_mission_ledger_load_clears_stale_active_pointer_and_persists(tmp_path, monkeypatch):
    ledger_path = tmp_path / "mission_ledger.json"
    evidence_dir = tmp_path / "evidence"
    trace_dir = tmp_path / "trace"
    evidence_dir.mkdir()
    trace_dir.mkdir()

    monkeypatch.setattr(mission_supervisor, "MISSION_LEDGER", ledger_path)
    monkeypatch.setattr(mission_supervisor, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(mission_supervisor, "TRACE_DIR", trace_dir)

    ledger_path.write_text(json.dumps({
        "missions": {},
        "active_mission_id": "mission-stale-1",
        "saved_at": time.time(),
    }))

    ledger = mission_supervisor.MissionLedger()
    persisted = json.loads(ledger_path.read_text())

    assert ledger.get_active() is None
    assert ledger.get_stats()["active"] is None
    assert persisted["active_mission_id"] is None


def test_mission_ledger_story_blocklist_covers_terminal_and_active_states(tmp_path, monkeypatch):
    ledger_path = tmp_path / "mission_ledger.json"
    evidence_dir = tmp_path / "evidence"
    trace_dir = tmp_path / "trace"
    evidence_dir.mkdir()
    trace_dir.mkdir()

    monkeypatch.setattr(mission_supervisor, "MISSION_LEDGER", ledger_path)
    monkeypatch.setattr(mission_supervisor, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(mission_supervisor, "TRACE_DIR", trace_dir)

    now = 10_000.0
    ledger = mission_supervisor.MissionLedger()
    ledger.missions = {
        "complete-1": mission_supervisor.Mission(
            mission_id="complete-1",
            story_id="DONE-1",
            story_title="Done Story",
            status=mission_supervisor.MissionStatus.COMPLETE,
            goal="done",
            created_at=1.0,
            completed_at=now - 50.0,
        ),
        "active-1": mission_supervisor.Mission(
            mission_id="active-1",
            story_id="RUN-1",
            story_title="Running Story",
            status=mission_supervisor.MissionStatus.RUNNING,
            goal="running",
            created_at=1.0,
        ),
        "cooldown-1": mission_supervisor.Mission(
            mission_id="cooldown-1",
            story_id="COOL-1",
            story_title="Cooling Story",
            status=mission_supervisor.MissionStatus.EXPIRED,
            goal="cooldown",
            created_at=1.0,
            completed_at=now - 30.0,
            attempts=1,
        ),
        "max-1": mission_supervisor.Mission(
            mission_id="max-1",
            story_id="MAX-1",
            story_title="Maxed Story",
            status=mission_supervisor.MissionStatus.FAILED,
            goal="failed",
            created_at=1.0,
            completed_at=now - mission_supervisor.STORY_COOLDOWN_SEC - 50.0,
            attempts=mission_supervisor.MAX_STORY_ATTEMPTS,
        ),
    }

    blocklist = ledger.get_story_blocklist(now=now)

    assert blocklist["DONE-1"] == "complete"
    assert blocklist["RUN-1"] == "active"
    assert blocklist["COOL-1"] == "cooldown"
    assert blocklist["MAX-1"] == "max_attempts"


def test_mission_executor_writes_trace_artifact(tmp_path, monkeypatch):
    import requests

    trace_dir = tmp_path / "trace"
    trace_dir.mkdir()
    monkeypatch.setattr(mission_supervisor, "TRACE_DIR", trace_dir)

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/event-stream"}

        def iter_lines(self):
            payloads = [
                {"event": "tool_call_detected", "tool_name": "read", "call_id": "abc", "arguments": {"path": "src/demo.py"}},
                {"event": "complete", "data": {"response": "done"}},
            ]
            for payload in payloads:
                yield b"data: " + json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: FakeResponse())

    executor = mission_supervisor.MissionExecutor()
    mission = mission_supervisor.Mission(
        mission_id="trace-mission-1",
        story_id="TRACE-1",
        story_title="Trace Story",
        status=mission_supervisor.MissionStatus.RUNNING,
        goal="goal",
        created_at=0.0,
    )

    result = asyncio.run(executor.execute(mission))
    trace_path = Path(result["trace_path"])

    assert trace_path.exists()
    trace_text = trace_path.read_text()
    assert "execute_started" in trace_text
    assert "stream_event" in trace_text
    assert "execute_finished" in trace_text


def test_run_mission_task_resumes_acquired_mission_without_reselecting_story(tmp_path, monkeypatch):
    ledger_path = tmp_path / "mission_ledger.json"
    evidence_dir = tmp_path / "evidence"
    trace_dir = tmp_path / "trace"
    evidence_dir.mkdir()
    trace_dir.mkdir()

    monkeypatch.setattr(mission_supervisor, "MISSION_LEDGER", ledger_path)
    monkeypatch.setattr(mission_supervisor, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(mission_supervisor, "TRACE_DIR", trace_dir)

    ledger = mission_supervisor.MissionLedger()
    envelope = mission_supervisor.MissionEnvelope(
        mission_id="mission-acquired-1",
        story_id="STORY-ACQ",
        story_title="Resume Me",
        goal="Finish the active story",
        files_in_scope=["src/demo.py"],
        verification_plan=["cmd: python -c \"print('ok')\""],
    )
    mission = ledger.create_mission(envelope)
    mission.status = mission_supervisor.MissionStatus.ACQUIRED
    mission.attempts = 1
    ledger._save()

    class FakeSelector:
        def __init__(self):
            self.get_next_story_calls = 0
            self.completed = []

        def get_next_story(self, active_executions=None):
            self.get_next_story_calls += 1
            return None

        def mark_complete(self, story_id):
            self.completed.append(story_id)
            return True

    class FakeExecutor:
        async def execute(self, mission, lease_touch=None):
            if lease_touch:
                lease_touch(120.0)
            return {
                "success": True,
                "tool_calls": [],
                "files_modified": ["src/demo.py"],
                "output": "done",
                "trace_path": str(trace_dir / f"{mission.mission_id}.jsonl"),
            }

        async def execute_verification(self, mission, files_modified):
            return [{"label": "smoke", "command": "python -c \"print('ok')\"", "success": True}]

    selector = FakeSelector()
    monkeypatch.setattr(mission_supervisor, "get_ledger", lambda: ledger)
    monkeypatch.setattr(mission_supervisor, "get_executor", lambda: FakeExecutor())
    monkeypatch.setattr(story_selector, "StorySelector", lambda: selector)

    result = asyncio.run(mission_supervisor.run_mission_task())

    assert "completed successfully" in result
    assert selector.get_next_story_calls == 0
    assert selector.completed == ["STORY-ACQ"]
    assert ledger.missions["mission-acquired-1"].status == mission_supervisor.MissionStatus.COMPLETE


def test_run_mission_task_expires_active_and_dispatches_next_story_same_cycle(tmp_path, monkeypatch):
    ledger_path = tmp_path / "mission_ledger.json"
    evidence_dir = tmp_path / "evidence"
    trace_dir = tmp_path / "trace"
    evidence_dir.mkdir()
    trace_dir.mkdir()

    monkeypatch.setattr(mission_supervisor, "MISSION_LEDGER", ledger_path)
    monkeypatch.setattr(mission_supervisor, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(mission_supervisor, "TRACE_DIR", trace_dir)

    ledger = mission_supervisor.MissionLedger()
    expired_envelope = mission_supervisor.MissionEnvelope(
        mission_id="mission-old-1",
        story_id="STORY-OLD",
        story_title="Old Story",
        goal="stale mission",
    )
    expired_mission = ledger.create_mission(expired_envelope)
    expired_mission.status = mission_supervisor.MissionStatus.RUNNING
    expired_mission.started_at = 100.0
    expired_mission.lease_expires_at = time.time() - 5.0
    ledger._save()

    next_story = story_selector.Story(
        id="STORY-NEW",
        title="Fresh Story",
        description="Do the next thing",
        status="todo",
        files_in_scope=["src/fresh.py"],
    )

    class FakeSelector:
        def __init__(self):
            self.active_executions = []
            self.completed = []

        def get_next_story(self, active_executions=None):
            self.active_executions = list(active_executions or [])
            return next_story

        def build_envelope(self, story):
            return mission_supervisor.MissionEnvelope(
                mission_id="mission-new-1",
                story_id=story.id,
                story_title=story.title,
                goal=story.title,
                files_in_scope=story.files_in_scope,
                verification_plan=["cmd: python -c \"print('ok')\""],
            )

        def mark_complete(self, story_id):
            self.completed.append(story_id)
            return True

    class FakeExecutor:
        async def execute(self, mission, lease_touch=None):
            if lease_touch:
                lease_touch(120.0)
            return {
                "success": True,
                "tool_calls": [],
                "files_modified": mission.files_in_scope,
                "output": "done",
                "trace_path": str(trace_dir / f"{mission.mission_id}.jsonl"),
            }

        async def execute_verification(self, mission, files_modified):
            return [{"label": "smoke", "command": "python -c \"print('ok')\"", "success": True}]

    selector = FakeSelector()
    monkeypatch.setattr(mission_supervisor, "get_ledger", lambda: ledger)
    monkeypatch.setattr(mission_supervisor, "get_executor", lambda: FakeExecutor())
    monkeypatch.setattr(story_selector, "StorySelector", lambda: selector)

    result = asyncio.run(mission_supervisor.run_mission_task())

    assert "completed successfully" in result
    assert "STORY-OLD" in selector.active_executions
    assert selector.completed == ["STORY-NEW"]
    assert ledger.missions["mission-old-1"].status == mission_supervisor.MissionStatus.EXPIRED
    assert ledger.missions["mission-new-1"].status == mission_supervisor.MissionStatus.COMPLETE
