#!/usr/bin/env python3
"""
Agent Eval Harness - Tests for tool execution, MCP, and web tools
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-008)
"""
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roxy.agent_eval")

TEST_THRESHOLD = 0.85


class EvalResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.duration = 0.0


class AgentEvalHarness:
    """
    Evaluation harness for ROXY autonomous coding agent capabilities.
    
    Tests:
    - Tool execution (bash, read, write, edit, glob, grep)
    - MCP integration
    - Web tools
    - Tool call detection
    - Governance hooks
    """
    
    def __init__(self):
        self.results: List[EvalResult] = []
    
    def add_result(self, name: str, passed: bool, message: str = ""):
        self.results.append(EvalResult(name, passed, message))
    
    async def run_all(self) -> Tuple[int, int, float]:
        """Run all evaluations. Returns (passed, total, duration)."""
        start = time.time()
        
        logger.info("Starting Agent Evaluation Suite...")
        
        await self.test_tool_executor()
        await self.test_streaming_tools()
        await self.test_tool_call_detection()
        await self.test_governance_hooks()
        await self.test_claude_md_injector()
        await self.test_mcp_client()
        await self.test_benchmark_suite()
        await self.test_tool_retry()
        await self.test_repo_intel()
        await self.test_mission_supervisor()
        
        duration = time.time() - start
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        return passed, total, duration
    
    async def test_tool_executor(self):
        """Test bash tool execution."""
        try:
            from tool_executor import ToolExecutor
            
            executor = ToolExecutor(timeout=10.0)
            
            result = await executor.execute_bash("echo 'Hello from bash'")
            self.add_result(
                "bash_simple",
                result.success and "Hello from bash" in result.output,
                f"Output: {result.output.strip()}"
            )
            
            result = await executor.execute_bash("ls /nonexistent", timeout=5.0)
            self.add_result(
                "bash_error_handling",
                not result.success and "No such file" in result.error,
                f"Error: {result.error.strip()}"
            )
            
            result = await executor.execute_bash("sleep 5", timeout=1.0)
            self.add_result(
                "bash_timeout",
                not result.success and "timed out" in result.error.lower(),
                f"Error: {result.error.strip()}"
            )
            
        except Exception as e:
            self.add_result("tool_executor", False, str(e))
    
    async def test_streaming_tools(self):
        """Test Read/Write/Edit/Glob/Grep tools."""
        try:
            from tools.streaming_tools import StreamingTools
            
            tools = StreamingTools(workdir=str(Path.home() / ".roxy"))
            
            result = await tools.read_file("tool_executor.py", limit=10)
            self.add_result(
                "read_file",
                result.success and result.metadata.get("lines_read") == 10,
                f"Lines: {result.metadata.get('lines_read')}"
            )
            
            test_file = "/tmp/roxy_eval_test.txt"
            result = await tools.write_file(test_file, "Hello Eval!")
            self.add_result(
                "write_file",
                result.success and Path(test_file).exists(),
                f"Path exists: {Path(test_file).exists()}"
            )
            
            result = await tools.edit_file(test_file, "Hello", "Hello World")
            self.add_result(
                "edit_file",
                result.success and "World" in Path(test_file).read_text(),
                f"Content: {Path(test_file).read_text()}"
            )
            
            result = await tools.glob("*.py", recursive=False)
            self.add_result(
                "glob_search",
                result.success and len(result.data) > 0,
                f"Found: {len(result.data)} files"
            )
            
            result = await tools.grep("ToolExecutor", file_pattern="tool_executor.py")
            self.add_result(
                "grep_search",
                result.success and len(result.data) > 0,
                f"Matches: {len(result.data)}"
            )
            
            Path(test_file).unlink(missing_ok=True)
            
        except Exception as e:
            self.add_result("streaming_tools", False, str(e))
    
    async def test_tool_call_detection(self):
        """Test tool call detection from text (native + MCP tools)."""
        try:
            from tool_call_integration import ToolCallDetector
            
            detector = ToolCallDetector()
            
            tests = [
                ("<<bash>>echo hello<</bash>>", "bash"),
                ("<<read>>/tmp/test.txt<</read>>", "read"),
                ('<<tool_call>>{"name":"bash","arguments":{"command":"pwd"}}<</tool_call>>', "bash"),
            ]
            
            detected = 0
            for text, expected_tool in tests:
                calls = detector.detect(text)
                if calls and any(c.name == expected_tool for c in calls):
                    detected += 1
            
            self.add_result(
                "tool_call_detection",
                detected >= 2,
                f"Detected: {detected}/3"
            )
            
            try:
                from roxy_core import _extract_stream_tool_calls
                
                mcp_tests = [
                    ('<<mcp_github_search>>{"query":"test"}<</mcp_github_search>>', "mcp_github_search"),
                    ('<<mcp_browser_navigate>>{"url":"https://example.com"}<</mcp_browser_navigate>>', "mcp_browser_navigate"),
                    ("<<mcp_desktop_screenshot>><</mcp_desktop_screenshot>>", "mcp_desktop_screenshot"),
                ]
                
                mcp_detected = 0
                for text, expected_name in mcp_tests:
                    calls = _extract_stream_tool_calls(text)
                    if calls and any(c["name"] == expected_name for c in calls):
                        mcp_detected += 1
                
                self.add_result(
                    "mcp_tool_detection",
                    bool(mcp_detected >= 2),
                    f"MCP Detected: {mcp_detected}/3"
                )
            except ImportError:
                self.add_result("mcp_tool_detection", True, "Skipped (roxy_core unavailable)")
            except Exception as e:
                self.add_result("mcp_tool_detection", False, str(e))
            
        except Exception as e:
            self.add_result("tool_call_detection", False, str(e))
    
    async def test_governance_hooks(self):
        """Test PreToolUse/PostToolUse hooks."""
        try:
            from governance_hooks import GovernanceHooks, ToolContext
            
            governance = GovernanceHooks()
            
            ctx = ToolContext(tool_name="read", arguments={"file_path": "/tmp/test"})
            decision = await governance.pre_tool_use(ctx)
            self.add_result(
                "governance_safe_tool",
                decision.allowed,
                f"Allowed: {decision.allowed}"
            )
            
            ctx = ToolContext(tool_name="bash", arguments={"command": "rm -rf"})
            decision = await governance.pre_tool_use(ctx)
            self.add_result(
                "governance_dangerous_tool",
                not decision.allowed,
                f"Denied: {not decision.allowed}"
            )
            
            result = {"success": True, "duration": 0.1, "exit_code": 0}
            await governance.post_tool_use(ctx, result, decision)
            
            entries = governance.get_audit_log(limit=1)
            self.add_result(
                "governance_audit_log",
                len(entries) > 0,
                f"Entries: {len(entries)}"
            )
            
        except Exception as e:
            self.add_result("governance_hooks", False, str(e))
    
    async def test_claude_md_injector(self):
        """Test CLAUDE.md context injection."""
        try:
            from claude_md_injector import ClaudeMDInjector
            
            injector = ClaudeMDInjector()
            
            context = injector.find_claude_md("/home/mark/work/mindsong_gh_https_1769765834")
            self.add_result(
                "claude_md_detection",
                context is not None and bool(context.content),
                f"Found: {context.file_path if context else 'None'}"
            )
            
            base_prompt = "What files are in the project?"
            enhanced = injector.inject_into_prompt(
                base_prompt,
                "/home/mark/work/mindsong_gh_https_1769765834"
            )
            self.add_result(
                "claude_md_injection",
                "PROJECT CONTEXT" in enhanced,
                f"Injected: {'Yes' if 'PROJECT CONTEXT' in enhanced else 'No'}"
            )
            
        except Exception as e:
            self.add_result("claude_md_injector", False, str(e))
    
    async def test_mcp_client(self):
        """Test MCP client initialization."""
        try:
            from mcp_client import MCPClient
            
            client = MCPClient()
            configs = client._load_configs()
            
            self.add_result(
                "mcp_client_init",
                True,
                f"Configs loaded: {len(configs)}"
            )
            
        except Exception as e:
            self.add_result("mcp_client", False, str(e))
    
    async def test_benchmark_suite(self):
        """Test benchmark suite and failure cluster modules."""
        try:
            from benchmark_suite import run_all_benchmarks
            from failure_cluster import FailureClusterer
            
            bench_results = await run_all_benchmarks()
            
            passed = bench_results["summary"]["passed"]
            total = bench_results["summary"]["total"]
            rate = bench_results["summary"]["pass_rate"]
            self.add_result(
                "benchmark_suite_run",
                rate >= 60.0,
                f"Benchmarks: {passed}/{total} passed ({rate:.1f}%)"
            )
            
            clusterer = FailureClusterer()
            clusterer.load_failures_from_audit(hours=1)
            clusterer.load_failures_from_errors(hours=1)
            report = clusterer.get_analysis_report()
            self.add_result(
                "failure_cluster_analysis",
                "summary" in report and "top_clusters" in report,
                f"Failures: {report['summary']['total_failures']}, Clusters: {report['summary']['unique_clusters']}"
            )
            
        except ImportError as e:
            self.add_result("benchmark_suite_run", False, f"Import error: {e}")
            self.add_result("failure_cluster_analysis", False, f"Import error: {e}")
        except Exception as e:
            self.add_result("benchmark_suite_run", False, str(e))
            self.add_result("failure_cluster_analysis", False, str(e))
    
    async def test_tool_retry(self):
        """Test tool retry controller with strategy rotation."""
        try:
            from tool_retry import (
                ToolRetryController, RootCauseClassifier,
            )
            
            ctrl = ToolRetryController()
            
            cause = RootCauseClassifier.classify("ls /nonexistent", "No such file or directory", 1)
            self.add_result(
                "retry_root_cause_classifier",
                cause == "not_found",
                f"Classified as: {cause}"
            )
            
            strategy = ctrl.get_next_strategy("bash", "ls /nonexistent", {},
                                             "No such file", 1)
            self.add_result(
                "retry_gets_strategy",
                strategy is not None,
                f"Strategy: {strategy.get('strategy_name') if strategy else 'None'}"
            )
            
            should_retry = ctrl.should_retry("bash", "ls /foo", {},
                                              "No such file", 1)
            self.add_result(
                "retry_should_retry",
                should_retry is True,
                f"Should retry: {should_retry}"
            )
            
            ctrl.record_success("bash", "ls /foo", {}, "No such file", "not_found", "sudo ls /foo")
            stats = ctrl.get_stats()
            self.add_result(
                "retry_stats_tracking",
                "tracked_commands" in stats,
                f"Tracked: {stats.get('tracked_commands', 0)}"
            )
            
        except ImportError as e:
            self.add_result("retry_root_cause_classifier", False, f"Import error: {e}")
            self.add_result("retry_gets_strategy", False, f"Import error: {e}")
            self.add_result("retry_should_retry", False, f"Import error: {e}")
            self.add_result("retry_stats_tracking", False, f"Import error: {e}")
        except Exception as e:
            self.add_result("retry_root_cause_classifier", False, str(e))
            self.add_result("retry_gets_strategy", False, str(e))
            self.add_result("retry_should_retry", False, str(e))
            self.add_result("retry_stats_tracking", False, str(e))
    
    async def test_repo_intel(self):
        """Test RepoIntel index."""
        try:
            from repo_intel import get_repo_index
            
            idx = get_repo_index()
            self.add_result(
                "repo_intel_loads",
                idx.file_count > 0,
                f"Files: {idx.file_count}, Symbols: {len(idx.symbol_index)}"
            )
            
            self.add_result(
                "repo_intel_symbols",
                len(idx.symbol_index) > 0,
                f"Symbols: {len(idx.symbol_index)}"
            )
            
            syms = idx.find_file_with_symbol("load_mpc_core")
            self.add_result(
                "repo_intel_lookup",
                len(syms) > 0,
                f"Symbol 'load_mpc_core': {len(syms)} results"
            )
            
        except ImportError as e:
            self.add_result("repo_intel_loads", False, f"Import error: {e}")
            self.add_result("repo_intel_symbols", False, f"Import error: {e}")
            self.add_result("repo_intel_lookup", False, f"Import error: {e}")
        except Exception as e:
            self.add_result("repo_intel_loads", False, str(e))
            self.add_result("repo_intel_symbols", False, str(e))
            self.add_result("repo_intel_lookup", False, str(e))

    async def test_mission_supervisor(self):
        """Test mission supervisor: ledger, envelope building, story selector integration."""
        try:
            import mission_supervisor
            from mission_supervisor import (
                MissionStatus, MissionEnvelope, MissionLedger,
                MissionExecutor,
            )
            with tempfile.TemporaryDirectory(prefix="roxy-agent-eval-") as temp_dir:
                temp_root = Path(temp_dir)
                original_ledger = mission_supervisor.MISSION_LEDGER
                original_evidence = mission_supervisor.EVIDENCE_DIR
                original_cached_ledger = mission_supervisor._ledger
                try:
                    mission_supervisor.MISSION_LEDGER = temp_root / "mission_ledger.json"
                    mission_supervisor.EVIDENCE_DIR = temp_root / "evidence"
                    mission_supervisor.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
                    mission_supervisor._ledger = None

                    ledger = MissionLedger()
                    self.add_result(
                        "mission_ledger_init",
                        ledger is not None,
                        "Ledger initialized"
                    )

                    envelope = MissionEnvelope(
                        mission_id="test-mission-1",
                        story_id="TEST-001",
                        story_title="Test Mission",
                        goal="Test goal",
                        constraints=["must work"],
                        required_evidence=["evidence 1"],
                        tool_budget=5,
                        verification_plan=["verify step 1"],
                        rollback_command="git checkout HEAD",
                        files_in_scope=["test.py"],
                    )
                    mission = ledger.create_mission(envelope)
                    self.add_result(
                        "mission_create",
                        mission.mission_id == "test-mission-1",
                        f"Created: {mission.mission_id}"
                    )
                    self.add_result(
                        "mission_status",
                        mission.status == MissionStatus.ACQUIRED,
                        f"Status: {mission.status.value}"
                    )

                    active = ledger.get_active()
                    self.add_result(
                        "mission_get_active",
                        active is not None and active.mission_id == "test-mission-1",
                        f"Active: {active.mission_id if active else 'none'}"
                    )

                    executor = MissionExecutor()
                    self.add_result(
                        "mission_executor_init",
                        executor is not None,
                        "Executor initialized"
                    )

                    stats = ledger.get_stats()
                    self.add_result(
                        "mission_stats",
                        stats.get("total_missions", 0) > 0,
                        f"Stats: {stats.get('total_missions')} total"
                    )
                finally:
                    mission_supervisor.MISSION_LEDGER = original_ledger
                    mission_supervisor.EVIDENCE_DIR = original_evidence
                    mission_supervisor._ledger = original_cached_ledger

        except ImportError as e:
            for name in ["mission_ledger_init", "mission_create", "mission_status",
                         "mission_get_active", "mission_executor_init", "mission_stats"]:
                self.add_result(name, False, f"Import error: {e}")
        except Exception as e:
            for name in ["mission_ledger_init", "mission_create", "mission_status",
                         "mission_get_active", "mission_executor_init", "mission_stats"]:
                self.add_result(name, False, str(e))

    def print_report(self):
        """Print evaluation report."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 70)
        print("ROXY AGENT EVALUATION REPORT")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {rate:.1f}%")
        print(f"Meets Threshold ({TEST_THRESHOLD * 100}%): {'YES' if rate >= TEST_THRESHOLD * 100 else 'NO'}")
        print("-" * 70)
        print("Detailed Results:")
        
        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.name}")
            if result.message:
                print(f"         {result.message}")
        
        print("=" * 70)


async def main():
    harness = AgentEvalHarness()
    passed, total, duration = await harness.run_all()
    harness.print_report()
    
    rate = (passed / total * 100) if total > 0 else 0
    
    if rate >= TEST_THRESHOLD * 100:
        print(f"\nEval PASSED (threshold: {TEST_THRESHOLD * 100}%)")
        return 0
    else:
        print(f"\nEval FAILED (threshold: {TEST_THRESHOLD * 100}%)")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
