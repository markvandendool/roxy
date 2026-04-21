"""
Unit tests for roxy_commands.py command parsing
Tests command routing and pattern matching
"""
import pytest
import sys
import types
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))
import roxy_commands
from roxy_commands import parse_command, _extract_repo_override


class TestGitCommandParsing:
    """Test Git command parsing"""
    
    def test_git_status(self):
        """Test git status parsing"""
        result = parse_command("git status")
        assert result[0] == "git"
        assert "status" in result[1]
    
    def test_git_commit(self):
        """Test git commit parsing"""
        result = parse_command("git commit -m 'test'")
        assert result[0] == "git"
    
    def test_git_push(self):
        """Test git push parsing"""
        result = parse_command("git push")
        assert result[0] == "git"
        assert "push" in result[1]
    
    def test_git_pull(self):
        """Test git pull parsing"""
        result = parse_command("git pull")
        assert result[0] == "git"

    def test_git_repo_question_routes_to_git_query(self):
        """Natural-language repo questions should use deterministic git-query handling."""
        result = parse_command(
            "In /home/mark/.roxy, what branch am I on and which Roxy Command Center files are modified?"
        )
        assert result[0] == "git_query"

    def test_extract_repo_override_from_explicit_path(self):
        """Explicit repo paths in prompts should be honored."""
        repo_path = Path.home() / ".roxy"
        if not (repo_path / ".git").exists():
            pytest.skip("~/.roxy git repo not present in this environment")
        assert _extract_repo_override(f"Check {repo_path} status") == str(repo_path)

    def test_answer_git_query_honors_explicit_repo_path(self, monkeypatch, tmp_path):
        """git_query answers must anchor to the repo path in the prompt."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        monkeypatch.setattr(
            roxy_commands,
            "_run_git_status_snapshot",
            lambda _repo: (
                "## feature/test...origin/feature/test",
                [(" M", "apps/roxy-command-center/main.py")],
            ),
        )
        monkeypatch.setattr(roxy_commands, "_mount_type_for", lambda _repo: "ext4")

        roxy_commands._reset_last_command_metadata()
        result = roxy_commands.answer_git_query(
            f"In {repo_path}, what branch am I on and which Roxy Command Center files are modified?"
        )

        assert str(repo_path) in result
        assert roxy_commands.LAST_COMMAND_METADATA["repo_path"] == str(repo_path)
        assert roxy_commands.LAST_COMMAND_METADATA["repo_snapshot"]["branch"] == "feature/test"
        assert roxy_commands.LAST_COMMAND_METADATA["repo_snapshot"]["modified_paths"] == [
            "apps/roxy-command-center/main.py"
        ]


class TestOBSCommandParsing:
    """Test OBS command parsing"""
    
    def test_obs_stream(self):
        """Test OBS stream command"""
        result = parse_command("start streaming")
        assert result[0] == "obs"
    
    def test_obs_record(self):
        """Test OBS record command"""
        result = parse_command("start recording")
        assert result[0] == "obs"
    
    def test_obs_scene_switch(self):
        """Test OBS scene switch"""
        result = parse_command("switch to gaming scene")
        assert result[0] == "obs"


class TestRAGQueryDetection:
    """Test RAG query detection"""
    
    def test_question_mark_query(self):
        """Test query with question mark"""
        result = parse_command("what is the weather?")
        assert result[0] == "rag"
    
    def test_what_query(self):
        """Test 'what' query"""
        result = parse_command("what can you do")
        assert result[0] in ["rag", "capabilities"]
    
    def test_how_query(self):
        """Test 'how' query"""
        result = parse_command("how do I install python?")
        assert result[0] == "rag"
    
    def test_explain_query(self):
        """Test 'explain' query"""
        result = parse_command("explain docker compose")
        assert result[0] == "rag"

    def test_strict_output_prompt_routes_to_chat(self):
        """Exact-format prompts should bypass RAG and use direct chat."""
        result = parse_command("Reply only with READY.")
        assert result[0] == "chat"

    def test_literal_strict_prompt_stays_chat(self):
        """Literal exact-answer prompts must preserve deterministic fastpath eligibility."""
        result = parse_command("Return only with READY")
        assert result[0] == "chat"

    def test_benchmark_codename_prompt_routes_to_memory_recall(self):
        """Benchmark codename recall should use the explicit deterministic memory-recall path."""
        result = parse_command("What is my benchmark codename from earlier? Reply with only the codename.")
        assert result[0] == "memory_recall"

    def test_benchmark_store_prompt_routes_to_memory_store(self):
        """Benchmark codename store prompts should use deterministic memory_store routing."""
        result = parse_command(
            "MBENCH-STORE: My benchmark codename is AZURE-EMBER-918. Remember it for later. Reply only with STORED-MBENCH."
        )
        assert result[0] == "memory_store"

    def test_answer_personal_memory_query_returns_latest_benchmark_codename(self, monkeypatch):
        """Personal memory fastpath should answer benchmark codenames from learned profile data."""
        fake_infra = types.ModuleType("infrastructure")
        fake_infra.get_user_profile = lambda **_kwargs: [
            {
                "category": "benchmark_codename",
                "preference": "AZURE-EMBER-916",
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
        monkeypatch.setitem(sys.modules, "infrastructure", fake_infra)
        monkeypatch.setenv("ROXY_USER_ID", "mark-roxy-canonical")

        assert (
            roxy_commands._answer_personal_memory_query(
                "What is my benchmark codename from earlier? Reply with only the codename."
            )
            == "AZURE-EMBER-916"
        )

    def test_answer_memory_recall_query_sets_explicit_memory_metadata(self, monkeypatch):
        """Benchmark codename recall should expose deterministic memory-recall metadata."""
        monkeypatch.setattr(
            roxy_commands,
            "_resolve_benchmark_codename",
            lambda: (
                "AZURE-EMBER-920",
                {
                    "attempted": True,
                    "succeeded": True,
                    "backend": "postgres",
                    "backend_healthy": True,
                    "source": "profile",
                    "facts_recalled": 1,
                    "recalled_facts": [{"category": "benchmark_codename", "preference": "AZURE-EMBER-920"}],
                    "error": None,
                },
            ),
        )

        roxy_commands._reset_last_command_metadata()
        result = roxy_commands.answer_memory_recall_query(
            "What is my benchmark codename from earlier? Reply with only the codename."
        )

        assert result == "AZURE-EMBER-920"
        assert roxy_commands.LAST_COMMAND_METADATA["route"] == "memory_recall"
        assert roxy_commands.LAST_COMMAND_METADATA["memory_receipt"]["backend"] == "postgres"
        assert roxy_commands.LAST_COMMAND_METADATA["routing_meta"]["reason"] == (
            "deterministic:memory_recall:benchmark_codename"
        )

    def test_command_response_json_sanitizes_datetime_metadata(self):
        """Structured response JSON must survive datetime-bearing metadata."""
        response = roxy_commands.CommandResponse(
            text="ok",
            mode="memory_recall",
            metadata={"memory_receipt": {"updated_at": datetime(2026, 4, 21, 5, 0, 0)}},
        )

        payload = response.to_json()
        assert "2026-04-21T05:00:00" in payload

    def test_chat_direct_prioritizes_literal_reply_over_memory_fastpath(self, monkeypatch):
        """Strict literal replies must win even if the prompt also matches personal-memory patterns."""
        monkeypatch.setattr(roxy_commands, "_inject_memory_context", lambda prompt: prompt)
        monkeypatch.setattr(
            roxy_commands,
            "_extract_literal_only_reply_fastpath",
            lambda _query: "STORED-MBENCH",
        )
        monkeypatch.setattr(
            roxy_commands,
            "_answer_personal_memory_query",
            lambda _query: "AZURE-EMBER-916",
        )

        assert (
            roxy_commands.chat_direct(
                "MBENCH-STORE: My benchmark codename is AZURE-EMBER-917. Remember it for later. Reply only with STORED-MBENCH."
            )
            == "STORED-MBENCH"
        )

    def test_extract_literal_reply_fastpath_matches_embedded_instruction(self):
        """Embedded 'reply only with' clauses should still yield the deterministic literal reply."""
        assert (
            roxy_commands._extract_literal_only_reply_fastpath(
                "MBENCH-STORE: My benchmark codename is AZURE-EMBER-918. Remember it for later. Reply only with STORED-MBENCH."
            )
            == "STORED-MBENCH"
        )


class TestSystemCommands:
    """Test system command parsing"""
    
    def test_health_command(self):
        """Test health check command"""
        result = parse_command("health")
        assert result[0] == "health"
    
    def test_system_health(self):
        """Test system health command"""
        result = parse_command("system health")
        assert result[0] == "health"
    
    def test_briefing_command(self):
        """Test briefing command"""
        result = parse_command("briefing")
        assert result[0] == "briefing"


class TestUnavailableCapabilities:
    """Test unavailable capability detection"""
    
    def test_browser_control_unavailable(self):
        """Test browser control is marked unavailable"""
        result = parse_command("open firefox")
        assert result[0] == "unavailable"
        assert "browser_control" in result[1]
    
    def test_shell_execution_unavailable(self):
        """Test shell execution is marked unavailable"""
        result = parse_command("execute bash command")
        assert result[0] == "unavailable"
    
    def test_cloud_integration_unavailable(self):
        """Test cloud integration is marked unavailable"""
        result = parse_command("aws list buckets")
        assert result[0] == "unavailable"


class TestToolDirectCalls:
    """Test direct tool calling syntax"""
    
    def test_json_tool_call(self):
        """Test JSON-style tool call"""
        result = parse_command('{"tool": "execute_command", "args": {"cmd": "ls"}}')
        assert result[0] == "tool_direct"
    
    def test_run_tool_syntax(self):
        """Test RUN_TOOL syntax"""
        result = parse_command('RUN_TOOL execute_command {"cmd": "ls"}')
        assert result[0] == "tool_direct"
        assert result[1][0] == "execute_command"


class TestGreetings:
    """Test greeting detection (for fastpath optimization)"""
    
    def test_hi_roxy(self):
        """Test 'hi roxy' greeting"""
        # Greetings may be handled at execution level, not parse level
        result = parse_command("hi roxy")
        # Should be processed somehow
        assert result is not None
    
    def test_hello(self):
        """Test 'hello' greeting"""
        result = parse_command("hello")
        assert result is not None
