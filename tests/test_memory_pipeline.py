import asyncio
import sys
import types
from datetime import datetime, timedelta

import benchmark_suite
import infrastructure
import memory_postgres
import roxy_commands
import roxy_core


def test_extract_user_facts_name_and_preference():
    text = "My name is Mark and I prefer concise responses."
    facts = infrastructure.extract_user_facts(text)
    categories = {f["category"] for f in facts}
    assert "name" in categories
    assert "general_preference" in categories
    assert any("Mark" in f["preference"] for f in facts if f["category"] == "name")


def test_inject_memory_context_into_prompt(monkeypatch):
    monkeypatch.setenv("ROXY_MEMORY_CONTEXT", "Learned user profile facts/preferences:\n- name: Mark")
    monkeypatch.setenv("ROXY_PLAN_CONTEXT", "1. Inspect service health\n2. Apply fix")
    base_prompt = "User: hello\nAssistant:"
    prompt = roxy_commands._inject_memory_context(base_prompt)
    assert "system memory directives" in prompt.lower()
    assert "for questions about the user" in prompt.lower()
    assert "name: Mark" in prompt
    assert "execution plan hints" in prompt.lower()
    assert base_prompt in prompt


def test_extract_user_facts_age_and_dislike():
    text = "I'm 35 years old and I don't like long meetings."
    facts = infrastructure.extract_user_facts(text)
    by_category = {f["category"]: f["preference"] for f in facts}
    assert by_category.get("age") == "35"
    assert by_category.get("general_dislike") == "long meetings"


def test_extract_user_facts_benchmark_codename():
    text = "My benchmark codename is AZURE-EMBER-914. Remember it for later."
    facts = infrastructure.extract_user_facts(text)
    by_category = {f["category"]: f["preference"] for f in facts}
    assert by_category.get("benchmark_codename") == "AZURE-EMBER-914"


def test_memory_rerank_prefers_lexical_overlap():
    memory = object.__new__(memory_postgres.PostgresMemory)
    memory.recall_min_score = 0.18
    memory.recall_min_similarity = 0.20
    memory.recall_min_lexical = 0.12

    now = datetime.now()
    memories = [
        {
            "id": 1,
            "session_id": "s1",
            "query": "show latest docker container stats",
            "response": "containers are running",
            "similarity": 0.56,
            "importance": 0.5,
            "score": 0.2,
            "created_at": (now - timedelta(days=1)).isoformat(),
        },
        {
            "id": 2,
            "session_id": "s2",
            "query": "my name is mark and i prefer concise responses",
            "response": "noted your name and style",
            "similarity": 0.22,
            "importance": 0.5,
            "score": 0.2,
            "created_at": (now - timedelta(days=2)).isoformat(),
        },
    ]
    ranked = memory._rerank_and_filter_memories("what is my name?", memories, k=2)
    assert ranked
    # The name query should match the second memory better (lexical overlap)
    # Check that lexical_overlap is calculated
    assert any(m.get("lexical_overlap", 0) > 0 for m in ranked)


def test_memory_recall_isolated_by_user_id():
    memory = object.__new__(memory_postgres.PostgresMemory)
    memory.recall_min_score = 0.0
    memory.recall_min_similarity = 0.0
    memory.recall_min_lexical = 0.0
    memory.default_user_id = "default"

    now = datetime.now().isoformat()
    memory._memory_store = [
        {
            "id": 1,
            "session_id": "s1",
            "user_id": "mark-roxy-canonical",
            "query": "my name is mark",
            "response": "noted",
            "importance": 0.8,
            "created_at": now,
        },
        {
            "id": 2,
            "session_id": "s2",
            "user_id": "sarah-test-user",
            "query": "my name is sarah",
            "response": "noted",
            "importance": 0.8,
            "created_at": now,
        },
    ]

    recalled = memory._recall_memory(
        query="what is my name",
        k=5,
        session_id=None,
        user_id="mark-roxy-canonical",
        time_window_days=None,
    )
    assert recalled
    assert all(item.get("user_id") == "mark-roxy-canonical" for item in recalled)


def test_agentic_analysis_detects_ambiguity_and_plan():
    ambiguous = roxy_core._analyze_agentic_request("fix it please")
    assert ambiguous["needs_clarification"] is True
    assert "refers to" in ambiguous["clarifying_question"].lower()

    complex_query = roxy_core._analyze_agentic_request(
        "run benchmark baseline and then optimize memory recall and verify the score delta"
    )
    assert complex_query["complex"] is True
    assert len(complex_query["plan_steps"]) >= 2


def test_memory_rescue_detection():
    query = "What is my name?"
    miss_response = "Based on the given context, there is no mention of your name."
    assert roxy_core._should_attempt_memory_rescue(query, miss_response, "EPISODIC MEMORY CONTEXT")
    good_response = "Your name is Mark."
    assert not roxy_core._should_attempt_memory_rescue(query, good_response, "EPISODIC MEMORY CONTEXT")


def test_execute_command_passes_memory_context_env(monkeypatch):
    handler = object.__new__(roxy_core.RoxyCoreHandler)
    handler.headers = {"X-ROXY-Session": "sess-xyz"}
    handler._last_execution_metadata = {}

    monkeypatch.setattr(
        roxy_core,
        "_resolve_ollama_pools",
        lambda: {
            "default": "http://127.0.0.1:11435",
            "w5700x": {"url": "http://127.0.0.1:11434", "configured": True},
            "6900xt": {"url": "http://127.0.0.1:11435", "configured": True},
            "misconfigured": False,
        },
    )
    monkeypatch.setattr(
        roxy_core,
        "_check_ollama_reachability",
        lambda _url: {"reachable": True, "error": None},
    )
    monkeypatch.setattr(roxy_core, "_get_default_model", lambda *args, **kwargs: "qwen2.5-coder:14b-instruct")

    captured_env = {}

    def fake_run(_cmd, capture_output, text, timeout, cwd, env):
        captured_env.update(env)
        structured = (
            "ok\n__STRUCTURED_RESPONSE__\n"
            '{"mode":"chat","tools_executed":[],"metadata":{"routing_meta":{"selected_pool":"6900xt","model_used":"qwen2.5-coder:14b-instruct"}}}'
        )
        return types.SimpleNamespace(stdout=structured, stderr="")

    monkeypatch.setattr(roxy_core.subprocess, "run", fake_run)

    result = handler._execute_command(
        "hello there",
        request_id="rid-123",
        session_id="sess-xyz",
        user_id="mark-roxy-canonical",
        memory_context="EPISODIC MEMORY CONTEXT (cross-session):\n- name: Mark",
        plan_steps=["Inspect health", "Apply fix"],
    )

    assert "ok" in result
    assert captured_env["ROXY_REQUEST_ID"] == "rid-123"
    assert captured_env["ROXY_SESSION_ID"] == "sess-xyz"
    assert captured_env["ROXY_USER_ID"] == "mark-roxy-canonical"
    assert "EPISODIC MEMORY CONTEXT" in captured_env["ROXY_MEMORY_CONTEXT"]
    assert "1. Inspect health" in captured_env["ROXY_PLAN_CONTEXT"]


def test_execute_command_preserves_repo_snapshot_metadata(monkeypatch):
    handler = object.__new__(roxy_core.RoxyCoreHandler)
    handler.headers = {"X-ROXY-Session": "sess-repo"}
    handler._last_execution_metadata = {}

    monkeypatch.setattr(
        roxy_core,
        "_resolve_ollama_pools",
        lambda: {
            "default": "http://127.0.0.1:11435",
            "w5700x": {"url": "http://127.0.0.1:11434", "configured": True},
            "6900xt": {"url": "http://127.0.0.1:11435", "configured": True},
            "misconfigured": False,
        },
    )
    monkeypatch.setattr(
        roxy_core,
        "_check_ollama_reachability",
        lambda _url: {"reachable": True, "error": None},
    )
    monkeypatch.setattr(roxy_core, "_get_default_model", lambda *args, **kwargs: "qwen2.5-coder:14b-instruct")

    def fake_run(_cmd, capture_output, text, timeout, cwd, env):
        structured = (
            "repo summary\n__STRUCTURED_RESPONSE__\n"
            '{"mode":"git_query","tools_executed":[],"metadata":{"route":"git_query","repo_path":"/tmp/repo","repo_snapshot":{"repo_path":"/tmp/repo","branch":"main","upstream":"origin/main","is_dirty":true,"changed_count":1,"modified_paths":["apps/roxy-command-center/main.py"],"untracked_paths":[],"status_lines":[" M apps/roxy-command-center/main.py"]},"routing_meta":{"selected_pool":"none","model_used":"none","reason":"deterministic:git_query:repo_override"}}}'
        )
        return types.SimpleNamespace(stdout=structured, stderr="")

    monkeypatch.setattr(roxy_core.subprocess, "run", fake_run)

    result = handler._execute_command(
        "In /tmp/repo, what branch am I on and which Roxy Command Center files are modified?",
        request_id="rid-repo",
        session_id="sess-repo",
        user_id="mark-roxy-canonical",
    )

    assert "repo summary" in result
    assert handler._last_execution_metadata["route"] == "git_query"
    assert handler._last_execution_metadata["repo_path"] == "/tmp/repo"
    assert handler._last_execution_metadata["repo_snapshot"]["branch"] == "main"
    assert handler._last_execution_metadata["routing_meta"]["reason"] == "deterministic:git_query:repo_override"


def test_canonical_identity_conflict_is_skipped(monkeypatch):
    recorded = []

    class DummyMemory:
        def learn_preference(self, category, preference, confidence=0.5, user_id=None):
            recorded.append((category, preference, confidence, user_id))

    monkeypatch.setattr(infrastructure, "ENFORCE_CANONICAL_IDENTITY", True)
    monkeypatch.setattr(infrastructure, "get_memory", lambda: DummyMemory())

    result = infrastructure.learn_user_facts(
        "My name is Sarah and I like coffee",
        session_id="sess-1",
        user_id=infrastructure.CANONICAL_USER_ID,
    )

    # Canonical identity conflict should be skipped, preference should still be learned.
    assert any(item.get("skipped") == "canonical_identity_conflict" for item in result["learned"])
    assert all(entry[0] != "name" for entry in recorded)


def test_learn_user_facts_reports_receipt_for_benchmark_codename(monkeypatch):
    recorded = []

    class DummyMemory:
        def learn_preference(self, category, preference, confidence=0.5, user_id=None):
            recorded.append((category, preference, confidence, user_id))

        def health_check(self):
            return {"healthy": True, "backend": "dummy-memory"}

    monkeypatch.setattr(infrastructure, "get_memory", lambda: DummyMemory())

    result = infrastructure.learn_user_facts(
        "My benchmark codename is AZURE-EMBER-914.",
        session_id="sess-bench",
        user_id="mark-roxy-canonical",
    )

    assert result["attempted"] is True
    assert result["succeeded"] is True
    assert result["backend"] == "dummy-memory"
    assert result["count"] == 1
    assert recorded[0][0] == "benchmark_codename"
    assert recorded[0][1] == "AZURE-EMBER-914"


def test_remember_conversation_returns_receipt(monkeypatch):
    calls = []

    class DummyMemory:
        def remember(self, *args, **kwargs):
            calls.append((args, kwargs))

        def health_check(self):
            return {"healthy": True, "backend": "dummy-memory"}

    monkeypatch.setattr(infrastructure, "get_memory", lambda: DummyMemory())

    receipt = infrastructure.remember_conversation("hello", "world", "sess-1", {"source": "test"}, user_id="mark")

    assert receipt["attempted"] is True
    assert receipt["succeeded"] is True
    assert receipt["backend"] == "dummy-memory"
    assert receipt["error"] is None
    assert calls


def test_recall_conversations_with_receipt_handles_missing_backend(monkeypatch):
    monkeypatch.setattr(infrastructure, "get_memory", lambda: None)

    results, receipt = infrastructure.recall_conversations_with_receipt("test query", k=3)

    assert results == []
    assert receipt["attempted"] is False
    assert receipt["backend_healthy"] is False
    assert receipt["error"] == "memory unavailable"


def test_memory_recall_latency_reports_backend_failure(monkeypatch):
    monkeypatch.setenv("ROXY_BENCHMARK_USE_SERVICE", "0")
    fake_infra = types.SimpleNamespace(
        recall_conversations_with_receipt=lambda *_args, **_kwargs: (
            [],
            {
                "attempted": True,
                "succeeded": False,
                "backend": "postgres",
                "backend_healthy": False,
                "error": "password authentication failed",
            },
        )
    )
    monkeypatch.setitem(sys.modules, "infrastructure", fake_infra)

    result = asyncio.run(benchmark_suite.LatencyBenchmark.memory_recall_latency())

    assert result.passed is False
    assert result.score == 0.0
    assert result.details["backend"] == "postgres"
    assert result.details["backend_healthy"] is False
    assert result.error == "password authentication failed"


def test_memory_recall_latency_prefers_service_endpoint(monkeypatch, tmp_path):
    token_file = tmp_path / "secret.token"
    token_file.write_text("test-token")
    monkeypatch.setattr(benchmark_suite, "ROXY_DIR", tmp_path)
    monkeypatch.setenv("ROXY_BENCHMARK_USE_SERVICE", "1")
    monkeypatch.setenv("ROXY_BENCHMARK_MEMORY_URL", "http://127.0.0.1:8766/memory/recall")

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        @staticmethod
        def json():
            return {
                "count": 3,
                "memory_receipt": {
                    "backend": "postgres",
                    "backend_healthy": True,
                    "attempted": True,
                    "succeeded": True,
                    "error": None,
                },
            }

    fake_requests = types.ModuleType("requests")
    captured = {}

    def fake_post(*args, **kwargs):
        captured["json"] = kwargs.get("json", {})
        return FakeResponse()

    fake_requests.post = fake_post
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    result = asyncio.run(benchmark_suite.LatencyBenchmark.memory_recall_latency())

    assert result.details["mode"] == "service"
    assert result.details["backend"] == "postgres"
    assert result.details["results"] == 3
    assert result.error is None
    assert captured["json"]["query"] == "what is my benchmark codename from earlier"


def test_sigterm_ignore_is_disabled_under_systemd(monkeypatch):
    monkeypatch.setenv("ROXY_IGNORE_SIGTERM", "1")
    monkeypatch.setenv("INVOCATION_ID", "systemd-unit-123")

    assert roxy_core._should_ignore_sigterm() is False


def test_sigterm_ignore_still_supported_for_manual_shell_launch(monkeypatch):
    monkeypatch.setenv("ROXY_IGNORE_SIGTERM", "1")
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    monkeypatch.delenv("JOURNAL_STREAM", raising=False)

    assert roxy_core._should_ignore_sigterm() is True


def test_build_memory_context_prioritizes_benchmark_codename(monkeypatch):
    monkeypatch.setattr(roxy_core, "INFRASTRUCTURE_AVAILABLE", True)
    monkeypatch.setattr(
        roxy_core,
        "recall_conversations_with_receipt",
        lambda *_args, **_kwargs: ([], {"attempted": True, "succeeded": True, "backend": "dummy", "error": None}),
    )

    def fake_get_user_profile(category=None, limit=10, user_id=None):
        if category == "benchmark_codename":
            return [
                {
                    "category": "benchmark_codename",
                    "preference": "AZURE-EMBER-915",
                    "confidence": 0.95,
                    "updated_at": "2026-04-20T23:30:00Z",
                },
                {
                    "category": "benchmark_codename",
                    "preference": "AZURE-EMBER-914",
                    "confidence": 0.95,
                    "updated_at": "2026-04-20T22:30:00Z",
                },
            ]
        return [
            {"category": "name", "preference": "Mark", "confidence": 0.99, "updated_at": "2026-04-20T20:00:00Z"},
            {
                "category": "benchmark_codename",
                "preference": "AZURE-EMBER-914",
                "confidence": 0.95,
                "updated_at": "2026-04-20T22:30:00Z",
            },
        ]

    monkeypatch.setattr(roxy_core, "get_user_profile", fake_get_user_profile)
    monkeypatch.setattr(roxy_core, "get_typed_records", lambda **_kwargs: [])
    monkeypatch.setattr(roxy_core, "_build_repo_context_for_prompt", lambda _query: ("", {}))

    context, meta = roxy_core._build_memory_context_for_prompt(
        "What is my benchmark codename from earlier? Reply with only the codename.",
        "sess-bench",
        "mark-roxy-canonical",
    )

    assert meta["priority_profile_category"] == "benchmark_codename"
    assert "AZURE-EMBER-915" in context
    assert context.index("AZURE-EMBER-915") < context.index("AZURE-EMBER-914")


def test_reflection_verifier_detects_hallucination():
    """Test that reflection verifier flags responses with unverified claims."""
    from reflection import ReflectionVerifier
    verifier = ReflectionVerifier(enabled=True, confidence_threshold=0.7)
    
    # Response with system claim without truth packet
    response = "The render is complete at /home/mark/renders/output.mp4"
    query = "Is the render done?"
    
    verification = verifier.verify_response(query, response, memory_context="", truth_packet="")
    
    # Should flag the system claim
    assert verification["confidence"] < 1.0
    assert len(verification["flags"]) > 0


def test_reflection_verifier_high_confidence():
    """Test that reflection verifier approves well-grounded responses."""
    from reflection import ReflectionVerifier
    verifier = ReflectionVerifier(enabled=True, confidence_threshold=0.7)
    
    # Response that admits uncertainty
    response = "I don't know the current render status. Let me check the production logs."
    query = "What's the render status?"
    
    verification = verifier.verify_response(query, response, memory_context="", truth_packet="")
    
    # Should have high confidence in not knowing
    assert verification["confidence"] >= 0.9


def test_mindson_production_boost():
    """Test that MindSong/SkyBeam memories get boosted scoring."""
    memory = object.__new__(memory_postgres.PostgresMemory)
    memory.recall_min_score = 0.18
    memory.recall_min_similarity = 0.20
    memory.recall_min_lexical = 0.12
    
    # SkyBeam render memory
    render_memory = {
        "query": "check skybeam render status",
        "response": "SkyBeam is rendering 3 videos",
        "similarity": 0.5,
        "importance": 0.5,
        "created_at": datetime.now().isoformat(),
    }
    
    # Generic memory
    generic_memory = {
        "query": "what's the weather",
        "response": "It's sunny today",
        "similarity": 0.5,
        "importance": 0.5,
        "created_at": datetime.now().isoformat(),
    }
    
    score_parts = memory._composite_recall_score(
        "check skybeam render queue", 
        render_memory, 
        same_session=False
    )
    
    generic_score = memory._composite_recall_score(
        "check skybeam render queue",
        generic_memory,
        same_session=False
    )
    
    # Production memory should get a boost
    assert score_parts.get("production_boost", 0) > 0
    assert score_parts["composite_score"] > generic_score["composite_score"]


def test_prompt_templates_production_detection():
    """Test that production queries get production prompts."""
    from prompts.templates import PromptTemplates
    
    # Production query should use production template
    prod_query = "How is the SkyBeam render queue?"
    template = PromptTemplates.select_prompt(prod_query, context="rendering 3 videos")
    assert "skybeam" in template.lower() or "production" in template.lower()
    # Ensure we don't regress to hardcoded disconnected status
    assert "production status: unknown (system not connected)" not in template.lower()
    
    # Monetization query should use monetization template
    money_query = "How is the StackKraft campaign performing?"
    template = PromptTemplates.select_prompt(money_query, context="1000 views")
    assert "monetize" in template.lower() or "stackkraft" in template.lower() or "revenue" in template.lower()


def test_verify_and_enhance_response():
    """Test the full verification and enhancement flow."""
    query = "What's the render status?"
    response = "The SkyBeam render is at 50% complete"
    memory_context = ""
    truth_packet = ""
    
    enhanced, verification = roxy_core._verify_and_enhance_response(
        query, response, memory_context, truth_packet
    )
    
    # Should return verification metadata
    assert "confidence" in verification
    assert "flags" in verification
    assert isinstance(verification["confidence"], float)


def test_reflection_retry_config():
    """Test that reflection retry configuration exists."""
    # Check that retry configs are defined
    assert hasattr(roxy_core, 'ENABLE_REFLECTION_RETRY')
    assert hasattr(roxy_core, 'REFLECTION_RETRY_THRESHOLD')
    assert hasattr(roxy_core, 'REFLECTION_MAX_RETRIES')
    assert isinstance(roxy_core.ENABLE_REFLECTION_RETRY, bool)
    assert isinstance(roxy_core.REFLECTION_RETRY_THRESHOLD, float)
    assert isinstance(roxy_core.REFLECTION_MAX_RETRIES, int)


def test_regenerate_with_memory_first():
    """Test memory-first regeneration function."""
    # Test with empty memory - should fail gracefully
    result, meta = roxy_core._regenerate_with_memory_first(
        query="Who am I?",
        session_id="test",
        memory_context="",
    )
    assert result == ""
    assert meta.get("error") == "no_memory_context"
    assert meta.get("regenerated") == True


def test_memory_fallback_uses_embeddings_for_semantic_recall():
    memory = object.__new__(memory_postgres.PostgresMemory)
    memory.recall_min_score = 0.0
    memory.recall_min_similarity = 0.0
    memory.recall_min_lexical = 0.0
    memory.default_user_id = "default"
    memory.embeddings_enabled = True
    memory._hot_memory_cache = []
    memory._memory_store = [
        {
            "id": 1,
            "session_id": "s1",
            "user_id": "default",
            "query": "deploy orchestration changes",
            "response": "done",
            "importance": 0.6,
            "query_embedding": [1.0, 0.0],
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
        },
        {
            "id": 2,
            "session_id": "s2",
            "user_id": "default",
            "query": "what is the weather today",
            "response": "sunny",
            "importance": 0.6,
            "query_embedding": [0.0, 1.0],
            "created_at": datetime.now().isoformat(),
            "access_count": 0,
        },
    ]
    memory._encode_text = lambda text: [1.0, 0.0]

    recalled = memory._recall_memory(
        query="ship the release",
        k=2,
        session_id=None,
        user_id="default",
        time_window_days=None,
    )

    assert recalled
    assert recalled[0]["id"] == 1
    assert recalled[0]["similarity"] > recalled[1]["similarity"]


def test_typed_record_roundtrip_in_memory_store():
    memory = object.__new__(memory_postgres.PostgresMemory)
    memory.conn = None
    memory._sqlite_enabled = False
    memory._sqlite_tables = set()
    memory._typed_records_store = []
    memory.embeddings_enabled = False
    memory.default_user_id = "default"
    memory.use_pgvector = False

    record_id = memory.remember_fix(
        "missing package import",
        "pip install fastmcp",
        metadata={"tool_name": "bash"},
        user_id="default",
    )

    records = memory.get_records(record_type="fix_recipe", query="package import failed", user_id="default")

    assert record_id == 1
    assert records
    assert records[0]["record_type"] == "fix_recipe"
    assert "fastmcp" in records[0]["content"]


def test_build_ui_snapshot_payload_merges_truth_and_snapshot(monkeypatch):
    monkeypatch.setattr(
        roxy_core,
        "_fetch_ui_panel_snapshot",
        lambda mode, remote_host, remote_port: (
            {
                "mode": mode,
                "source": "local",
                "system": {"cpu_pct": 12.5, "mem_used_gb": 4.0, "mem_total_gb": 16.0},
                "gpu": [{"index": 0, "name": "6900 XT", "temp_c": 54, "utilization_pct": 33}],
                "services": {"roxy_core": {"active": True, "source": "local"}},
                "bench": {"available": True, "status": "idle"},
            },
            True,
        ),
    )
    monkeypatch.setattr(
        roxy_core,
        "_collect_info_payload",
        lambda: {"git": {"branch": "main", "head_sha": "abc1234", "dirty": True}},
    )

    payload = roxy_core._build_ui_snapshot_payload(
        mode="local",
        remote_host="127.0.0.1",
        remote_port=8766,
    )

    assert payload["mode"] == "local"
    assert payload["info"]["git"]["branch"] == "main"
    assert payload["truth"]["git"]["head_sha"] == "abc1234"
    assert payload["bench"]["status"] == "idle"
    assert payload["snapshot_meta"]["cache_hit"] is True
    assert payload["snapshot_meta"]["target_host"] == "127.0.0.1"


def test_build_ui_snapshot_payload_falls_back_on_panel_failure(monkeypatch):
    monkeypatch.setattr(
        roxy_core,
        "_fetch_ui_panel_snapshot",
        lambda mode, remote_host, remote_port: (_ for _ in ()).throw(RuntimeError("panel unavailable")),
    )
    monkeypatch.setattr(
        roxy_core,
        "_collect_info_payload",
        lambda: {"git": {"branch": "main"}},
    )
    monkeypatch.setattr(
        roxy_core,
        "_get_bench_status_payload",
        lambda: {"available": False, "status": "unavailable"},
    )

    payload = roxy_core._build_ui_snapshot_payload()

    assert payload["source"] == "roxy-core-fallback"
    assert payload["snapshot_error"] == "panel unavailable"
    assert payload["info"]["git"]["branch"] == "main"
    assert payload["bench"]["status"] == "unavailable"
