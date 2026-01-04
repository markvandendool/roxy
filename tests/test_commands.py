"""
Unit tests for roxy_commands.py command parsing
Tests command routing and pattern matching
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".roxy"))
from roxy_commands import parse_command


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
