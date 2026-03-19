#!/usr/bin/env python3
"""
Benchmark Suite - Performance and quality benchmarks for ROXY
Measures latency, throughput, accuracy, and tool execution.
"""
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("roxy.benchmark")

ROXY_DIR = Path.home() / ".roxy"
EVIDENCE_DIR = ROXY_DIR / "evidence" / "benchmarks"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BenchmarkResult:
    name: str
    passed: bool
    score: float
    duration: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class BenchmarkSuite:
    name: str
    description: str
    benchmarks: List[Callable] = field(default_factory=list)
    
    async def run(self) -> List[BenchmarkResult]:
        """Run all benchmarks in the suite."""
        results = []
        for benchmark in self.benchmarks:
            try:
                result = await benchmark()
                results.append(result)
            except Exception as e:
                logger.error(f"Benchmark {benchmark.__name__} failed: {e}")
                results.append(BenchmarkResult(
                    name=benchmark.__name__,
                    passed=False,
                    score=0.0,
                    duration=0.0,
                    error=str(e),
                ))
        return results


class LatencyBenchmark:
    """Measures response latency for various operations."""
    
    @staticmethod
    async def ollama_streaming_latency() -> BenchmarkResult:
        """Benchmark Ollama streaming response time."""
        start = time.time()
        try:
            import requests
            resp = requests.post(
                "http://127.0.0.1:11435/api/generate",
                json={"model": "qwen2.5-coder:14b-instruct", "prompt": "test", "stream": True},
                stream=True,
                timeout=30,
            )
            first_token_time = None
            total_tokens = 0
            for line in resp.iter_lines():
                if line:
                    data = json.loads(line)
                    if first_token_time is None and data.get("response"):
                        first_token_time = time.time() - start
                    total_tokens += len(data.get("response", ""))
            return BenchmarkResult(
                name="ollama_streaming_latency",
                passed=True,
                score=100.0 if first_token_time and first_token_time < 2.0 else 50.0,
                duration=time.time() - start,
                details={
                    "first_token_ms": int(first_token_time * 1000) if first_token_time else None,
                    "total_tokens": total_tokens,
                    "tokens_per_sec": total_tokens / (time.time() - start) if total_tokens > 0 else 0,
                },
            )
        except Exception as e:
            return BenchmarkResult(
                name="ollama_streaming_latency",
                passed=False,
                score=0.0,
                duration=time.time() - start,
                error=str(e),
            )
    
    @staticmethod
    async def memory_recall_latency() -> BenchmarkResult:
        """Benchmark memory recall query time."""
        start = time.time()
        try:
            from infrastructure import recall_conversations
            results = recall_conversations("test query", k=5)
            recall_time = time.time() - start
            return BenchmarkResult(
                name="memory_recall_latency",
                passed=recall_time < 0.5,
                score=100.0 if recall_time < 0.1 else (50.0 if recall_time < 0.5 else 0.0),
                duration=recall_time,
                details={"results": len(results)},
            )
        except Exception as e:
            return BenchmarkResult(
                name="memory_recall_latency",
                passed=False,
                score=0.0,
                duration=time.time() - start,
                error=str(e),
            )


class ThroughputBenchmark:
    """Measures throughput for various operations."""
    
    @staticmethod
    async def tool_execution_throughput() -> BenchmarkResult:
        """Benchmark tool execution throughput."""
        try:
            from tool_executor import ToolExecutor
            executor = ToolExecutor(timeout=10.0)
            
            start = time.time()
            for _ in range(10):
                await executor.execute_bash("echo test")
            duration = time.time() - start
            
            return BenchmarkResult(
                name="tool_execution_throughput",
                passed=duration < 5.0,
                score=100.0 if duration < 2.0 else (50.0 if duration < 5.0 else 0.0),
                duration=duration,
                details={"ops_per_sec": 10 / duration if duration > 0 else 0},
            )
        except Exception as e:
            return BenchmarkResult(
                name="tool_execution_throughput",
                passed=False,
                score=0.0,
                duration=0.0,
                error=str(e),
            )
    
    @staticmethod
    async def mcp_discovery_throughput() -> BenchmarkResult:
        """Benchmark MCP tool discovery time."""
        start = time.time()
        try:
            from mcp_client import MCPClient
            client = MCPClient()
            configs = client._load_configs()
            discovery_time = time.time() - start
            
            return BenchmarkResult(
                name="mcp_discovery_throughput",
                passed=discovery_time < 1.0,
                score=100.0 if discovery_time < 0.1 else (50.0 if discovery_time < 1.0 else 0.0),
                duration=discovery_time,
                details={"servers": len(configs)},
            )
        except Exception as e:
            return BenchmarkResult(
                name="mcp_discovery_throughput",
                passed=False,
                score=0.0,
                duration=time.time() - start,
                error=str(e),
            )


class QualityBenchmark:
    """Measures output quality for various operations."""
    
    @staticmethod
    async def tool_call_detection_accuracy() -> BenchmarkResult:
        """Benchmark tool call detection accuracy."""
        try:
            from tool_call_integration import ToolCallDetector
            detector = ToolCallDetector()
            
            test_cases = [
                ("<<bash>>echo hello<</bash>>", "bash"),
                ("<<read>>/tmp/test.txt<</read>>", "read"),
                ('<<tool_call>>{"name":"bash","arguments":{"command":"pwd"}}<</tool_call>>', "bash"),
                ("<<mcp_github_search>>{\"query\":\"test\"}<</mcp_github_search>>", "mcp_github_search"),
            ]
            
            correct = 0
            for text, expected in test_cases:
                calls = detector.detect(text)
                if any(c.name == expected for c in calls):
                    correct += 1
            
            accuracy = correct / len(test_cases) * 100
            
            return BenchmarkResult(
                name="tool_call_detection_accuracy",
                passed=accuracy >= 75.0,
                score=accuracy,
                duration=0.0,
                details={"correct": correct, "total": len(test_cases)},
            )
        except Exception as e:
            return BenchmarkResult(
                name="tool_call_detection_accuracy",
                passed=False,
                score=0.0,
                duration=0.0,
                error=str(e),
            )
    
    @staticmethod
    async def story_selector_quality() -> BenchmarkResult:
        """Benchmark story selector quality."""
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            
            next_story = selector.get_next_story()
            summary = selector.get_status_summary()
            
            has_next = next_story is not None
            has_stories = summary["total_stories"] > 0
            quality = (has_next and has_stories) * 50 + (summary["completion_pct"] if has_stories else 0) * 0.5
            
            return BenchmarkResult(
                name="story_selector_quality",
                passed=has_next and has_stories,
                score=quality,
                duration=0.0,
                details={
                    "next_story": next_story.id if next_story else None,
                    "total_stories": summary["total_stories"],
                    "completion_pct": summary["completion_pct"],
                },
            )
        except Exception as e:
            return BenchmarkResult(
                name="story_selector_quality",
                passed=False,
                score=0.0,
                duration=0.0,
                error=str(e),
            )


async def run_all_benchmarks() -> Dict[str, Any]:
    """Run all benchmark suites."""
    suites = [
        BenchmarkSuite(
            name="latency",
            description="Response latency benchmarks",
            benchmarks=[
                LatencyBenchmark.ollama_streaming_latency,
                LatencyBenchmark.memory_recall_latency,
            ],
        ),
        BenchmarkSuite(
            name="throughput",
            description="Throughput benchmarks",
            benchmarks=[
                ThroughputBenchmark.tool_execution_throughput,
                ThroughputBenchmark.mcp_discovery_throughput,
            ],
        ),
        BenchmarkSuite(
            name="quality",
            description="Output quality benchmarks",
            benchmarks=[
                QualityBenchmark.tool_call_detection_accuracy,
                QualityBenchmark.story_selector_quality,
            ],
        ),
    ]
    
    all_results = []
    suite_results = {}
    
    for suite in suites:
        results = await suite.run()
        all_results.extend(results)
        suite_results[suite.name] = {
            "description": suite.description,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "score": r.score,
                    "duration": r.duration,
                    "details": r.details,
                    "error": r.error,
                }
                for r in results
            ],
        }
    
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    avg_score = sum(r.score for r in all_results) / total if total > 0 else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "avg_score": avg_score,
        },
        "suites": suite_results,
    }


def save_benchmark_evidence(results: Dict[str, Any]) -> Path:
    """Save benchmark results to evidence directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_file = EVIDENCE_DIR / f"benchmark_{timestamp}.json"
    with open(evidence_file, "w") as f:
        json.dump(results, f, indent=2)
    return evidence_file


async def main():
    """Run benchmarks and save results."""
    logging.basicConfig(level=logging.INFO)
    
    print("Running ROXY Benchmark Suite...")
    print("=" * 50)
    
    results = await run_all_benchmarks()
    
    print(f"\nSummary:")
    print(f"  Total: {results['summary']['total']}")
    print(f"  Passed: {results['summary']['passed']}")
    print(f"  Failed: {results['summary']['failed']}")
    print(f"  Pass Rate: {results['summary']['pass_rate']:.1f}%")
    print(f"  Avg Score: {results['summary']['avg_score']:.1f}")
    
    print(f"\nSuites:")
    for suite_name, suite_data in results["suites"].items():
        print(f"  {suite_name}:")
        for result in suite_data["results"]:
            status = "PASS" if result["passed"] else "FAIL"
            print(f"    [{status}] {result['name']}: {result['score']:.1f}")
    
    evidence_file = save_benchmark_evidence(results)
    print(f"\nEvidence saved to: {evidence_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
