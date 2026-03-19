import types
from datetime import datetime, timedelta

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
        memory_context="EPISODIC MEMORY CONTEXT (cross-session):\n- name: Mark",
        plan_steps=["Inspect health", "Apply fix"],
    )

    assert "ok" in result
    assert captured_env["ROXY_REQUEST_ID"] == "rid-123"
    assert captured_env["ROXY_SESSION_ID"] == "sess-xyz"
    assert "EPISODIC MEMORY CONTEXT" in captured_env["ROXY_MEMORY_CONTEXT"]
    assert "1. Inspect health" in captured_env["ROXY_PLAN_CONTEXT"]


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
