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
from capabilities import CapabilitiesProvider
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

    def test_answer_git_query_records_truth_sources_and_gitnexus(self, monkeypatch, tmp_path):
        """git_query metadata should carry raw-git primary truth plus GitNexus status when available."""
        repo_path = tmp_path / "mindsong-juke-hub"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        monkeypatch.setattr(
            roxy_commands,
            "_run_git_status_snapshot",
            lambda _repo: (
                "## main...origin/main",
                [(" M", "src/components/theater8k/hooks/useDualCanvasThreeScene.ts")],
            ),
        )
        monkeypatch.setattr(roxy_commands, "_mount_type_for", lambda _repo: "ext4")

        fake_gitnexus = types.ModuleType("gitnexus_client")
        fake_gitnexus.resolve_repo_name = lambda _repo: "mindsong-juke-hub"
        fake_gitnexus.get_repo_status = lambda _repo: {
            "available": True,
            "repo_name": "mindsong-juke-hub",
            "indexed": True,
            "indexed_at": "2026-04-21T00:00:00Z",
            "fresh": True,
            "stats": {"files": 10, "nodes": 20, "processes": 2},
            "error": None,
            "truth_source": "gitnexus",
        }
        monkeypatch.setitem(sys.modules, "gitnexus_client", fake_gitnexus)

        roxy_commands._reset_last_command_metadata()
        roxy_commands.answer_git_query(f"In {repo_path}, what branch am I on and what changed?")

        assert roxy_commands.LAST_COMMAND_METADATA["truth_sources"]["primary"] == "raw_git"
        assert "gitnexus" in roxy_commands.LAST_COMMAND_METADATA["truth_sources"]["sources"]
        assert roxy_commands.LAST_COMMAND_METADATA["gitnexus"]["indexed"] is True

    def test_answer_git_query_marks_stale_gitnexus_as_degraded(self, monkeypatch, tmp_path):
        """Stale GitNexus indexes must downgrade truth confidence instead of reading as fresh."""
        repo_path = tmp_path / "mindsong-juke-hub"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        monkeypatch.setattr(
            roxy_commands,
            "_run_git_status_snapshot",
            lambda _repo: (
                "## main...origin/main",
                [(" M", "src/components/theater8k/hooks/useDualCanvasThreeScene.ts")],
            ),
        )
        monkeypatch.setattr(roxy_commands, "_mount_type_for", lambda _repo: "ext4")

        fake_gitnexus = types.ModuleType("gitnexus_client")
        fake_gitnexus.resolve_repo_name = lambda _repo: "mindsong-juke-hub"
        fake_gitnexus.get_repo_status = lambda _repo: {
            "available": True,
            "repo_name": "mindsong-juke-hub",
            "indexed": True,
            "indexed_at": "2026-04-21T00:00:00Z",
            "fresh": False,
            "indexed_commit": "abc123",
            "current_commit": "def456",
            "staleness_reason": "head_mismatch",
            "stats": {"files": 10, "nodes": 20, "processes": 2},
            "error": None,
            "truth_source": "gitnexus",
        }
        monkeypatch.setitem(sys.modules, "gitnexus_client", fake_gitnexus)

        roxy_commands._reset_last_command_metadata()
        roxy_commands.answer_git_query(f"In {repo_path}, what branch am I on and what changed?")

        truth_sources = roxy_commands.LAST_COMMAND_METADATA["truth_sources"]
        assert truth_sources["primary"] == "raw_git"
        assert truth_sources["degraded"] is True
        assert truth_sources["degraded_reason"] == "gitnexus_stale"
        assert roxy_commands.LAST_COMMAND_METADATA["gitnexus"]["fresh"] is False


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

    def test_reply_with_exactly_routes_to_chat(self):
        """Exact literal prompts using 'with exactly' must bypass RAG."""
        result = parse_command("Reply with exactly READY.")
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

    def test_benchmark_store_without_colon_routes_to_memory_store(self):
        """MBENCH-STORE prefix should route deterministically even without the legacy colon form."""
        result = parse_command(
            "MBENCH-STORE Remember this codename exactly: AZURE-EMBER-918. Reply only with STORED-MBENCH."
        )
        assert result[0] == "memory_store"

    def test_benchmark_recall_prefix_routes_to_memory_recall(self):
        """MBENCH-RECALL prefix should not fall through to chat."""
        result = parse_command(
            "MBENCH-RECALL What codename did I ask you to remember? Reply with only the codename."
        )
        assert result[0] == "memory_recall"

    def test_answer_personal_memory_query_returns_latest_benchmark_codename(self, monkeypatch, tmp_path):
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
        monkeypatch.setattr(
            roxy_commands,
            "BENCHMARK_FAST_MEMORY_PATH",
            tmp_path / "benchmark_fast_memory.json",
        )

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

    def test_extract_literal_reply_fastpath_matches_with_exactly(self):
        """'Reply with exactly' should also use the deterministic literal fastpath."""
        assert roxy_commands._extract_literal_only_reply_fastpath("Reply with exactly READY.") == "READY"

    def test_benchmark_fast_memory_roundtrip(self, monkeypatch, tmp_path):
        """Benchmark codename store/recall should use the direct fast-memory path."""
        fast_path = tmp_path / "benchmark_fast_memory.json"
        monkeypatch.setattr(roxy_commands, "BENCHMARK_FAST_MEMORY_PATH", fast_path)
        monkeypatch.setenv("ROXY_USER_ID", "mark-test")
        roxy_commands._reset_last_command_metadata()

        stored, _model = roxy_commands.execute_command(
            "memory_store",
            [
                "MBENCH-STORE: My benchmark codename is AZURE-EMBER-999. Remember it for later. Reply only with STORED-MBENCH.",
                "MBENCH-STORE: My benchmark codename is AZURE-EMBER-999. Remember it for later. Reply only with STORED-MBENCH.",
            ],
        )
        recalled = roxy_commands.answer_memory_recall_query(
            "What is my benchmark codename from earlier? Reply only with the codename."
        )

        assert stored == "STORED-MBENCH"
        assert recalled == "AZURE-EMBER-999"
        assert roxy_commands.LAST_COMMAND_METADATA["memory_receipt"]["backend"] == "benchmark_fast_memory"

    def test_benchmark_fast_memory_roundtrip_for_remember_this_codename_shape(self, monkeypatch, tmp_path):
        """The newer operator phrasing should hit the same fast-memory backend."""
        fast_path = tmp_path / "benchmark_fast_memory.json"
        monkeypatch.setattr(roxy_commands, "BENCHMARK_FAST_MEMORY_PATH", fast_path)
        monkeypatch.setenv("ROXY_USER_ID", "mark-test")
        roxy_commands._reset_last_command_metadata()

        stored, _model = roxy_commands.execute_command(
            "memory_store",
            [
                "REVIEW-CODENAME-4422",
                "MBENCH-STORE Remember this codename exactly: REVIEW-CODENAME-4422. Reply only with STORED-MBENCH.",
            ],
        )
        recalled = roxy_commands.answer_memory_recall_query(
            "MBENCH-RECALL What codename did I ask you to remember? Reply with only the codename."
        )

        assert stored == "STORED-MBENCH"
        assert recalled == "REVIEW-CODENAME-4422"
        assert roxy_commands.LAST_COMMAND_METADATA["memory_receipt"]["backend"] == "benchmark_fast_memory"

    def test_git_dirty_paths_prompt_routes_to_git_query(self):
        """Structured dirty-path prompts should bypass RAG and use deterministic git_query."""
        result = parse_command(
            "In /home/mark/.roxy, list every dirty path as a JSON array of relative paths only, sorted ascending, with no extra text."
        )
        assert result[0] == "git_query"

    def test_answer_git_query_serializes_branch_dirty_contract(self, monkeypatch, tmp_path):
        """Strict branch/dirty contracts should render exact machine-readable output."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        monkeypatch.setattr(
            roxy_commands,
            "_run_git_status_snapshot",
            lambda _repo: (
                "## main...origin/main",
                [
                    (" M", "apps/roxy-command-center/main.py"),
                    ("??", "briefings/live-bench.md"),
                ],
            ),
        )
        monkeypatch.setattr(roxy_commands, "_mount_type_for", lambda _repo: "ext4")

        result = roxy_commands.answer_git_query(
            f"In {repo_path}, what branch am I on and how many dirty paths are there? Reply exactly in the form BRANCH=<branch>; DIRTY=<n>."
        )
        assert result == "BRANCH=main; DIRTY=2"

    def test_answer_git_query_serializes_dirty_paths_json(self, monkeypatch, tmp_path):
        """Strict dirty-path prompts should render a raw JSON array without prose."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        monkeypatch.setattr(
            roxy_commands,
            "_run_git_status_snapshot",
            lambda _repo: (
                "## main...origin/main",
                [
                    (" M", "briefings/a.md"),
                    ("??", "briefings/b.json"),
                ],
            ),
        )
        monkeypatch.setattr(roxy_commands, "_mount_type_for", lambda _repo: "ext4")

        result = roxy_commands.answer_git_query(
            f"In {repo_path}, list every dirty path as a JSON array of relative paths only, sorted ascending, with no extra text."
        )
        assert result == '["briefings/a.md", "briefings/b.json"]'


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

    def test_natural_language_write_file_routes_to_tool_direct(self, tmp_path):
        """Natural-language create/write requests should route to deterministic host writes."""
        target = tmp_path / "note.txt"
        result = parse_command(f"Create file {target} with content HELLO-ROXY")
        assert result[0] == "tool_direct"
        assert result[1][0] == "write_file"
        assert result[1][1]["path"] == str(target)
        assert result[1][1]["content"] == "HELLO-ROXY"

    def test_natural_language_write_file_strips_trailing_reply_instruction(self, tmp_path):
        """Write-file parser should not leak exact-output instructions into file content."""
        target = tmp_path / "note.txt"
        result = parse_command(
            f"Create file {target} with content HELLO-ROXY. Reply only with CREATED."
        )
        assert result[0] == "tool_direct"
        assert result[1][1]["content"] == "HELLO-ROXY"

    def test_natural_language_write_file_with_exactly_and_nothing_else(self, tmp_path):
        """Common operator phrasing should still route to deterministic host writes."""
        target = tmp_path / "note.txt"
        result = parse_command(
            f"Create the file {target} with exactly HELLO-ROXY and nothing else."
        )
        assert result[0] == "tool_direct"
        assert result[1][0] == "write_file"
        assert result[1][1]["path"] == str(target)
        assert result[1][1]["content"] == "HELLO-ROXY"

    def test_capability_probe_routes_to_capabilities(self):
        """Direct capability checks should use the deterministic capabilities lane."""
        result = parse_command("Can you create a file in /home/mark/.roxy right now? Reply only with YES or NO.")
        assert result[0] == "capabilities"

    def test_execute_tool_direct_write_file_creates_host_file(self, tmp_path):
        """write_file tool should create real host files deterministically."""
        target = tmp_path / "created.txt"
        result = roxy_commands.execute_tool_direct(
            "write_file",
            {"path": str(target), "content": "hello world", "create_dirs": True},
        )
        assert "WROTE:" in result
        assert target.read_text() == "hello world"


class TestCapabilitiesProvider:
    """Capability answers must stay deterministic and evidence-backed."""

    def test_three_line_capability_answer_honors_exact_prompt(self, monkeypatch):
        provider = CapabilitiesProvider()
        monkeypatch.setattr(
            provider,
            "get_available_tools",
            lambda: ["file_writing", "memory_recall", "mcp:browser", "mcp:sandbox"],
        )
        monkeypatch.setattr(
            provider,
            "check_email_available",
            lambda: {"enabled": True, "mode": "multi_account_mcp", "account_count": 4, "account_names": ["icloud", "gmail", "novaxe-gmail", "novaxe"]},
        )
        monkeypatch.setattr(
            provider,
            "get_gitnexus_info",
            lambda repo_name="roxy": {"indexed": False},
        )
        monkeypatch.setattr(
            provider,
            "get_model_info",
            lambda: {"current_model": "qwen3:14b"},
        )

        answer = provider.answer_query("What are your capabilities right now? Reply in exactly 3 lines.")

        lines = answer.splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("Files/Git:")
        assert "GitNexus for roxy is not indexed." in lines[1]
        assert lines[2] == "Model: qwen3:14b. Email: live via 4 configured accounts."

    def test_check_email_available_uses_multi_account_registry(self, tmp_path):
        provider = CapabilitiesProvider()
        provider.roxy_dir = tmp_path / ".roxy"
        (provider.roxy_dir / "mcp-servers" / "email").mkdir(parents=True)
        (provider.roxy_dir / "mcp-servers" / "email" / "accounts.json").write_text(
            """
            {
              "accounts": [
                {"name": "icloud", "email": "mark@me.com"},
                {"name": "gmail", "email": "mark@gmail.com"}
              ]
            }
            """.strip()
        )

        status = provider.check_email_available()

        assert status["enabled"] is True
        assert status["mode"] == "multi_account_mcp"
        assert status["account_count"] == 2
        assert status["account_names"] == ["icloud", "gmail"]


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
