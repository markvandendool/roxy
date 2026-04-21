#!/usr/bin/env python3
"""
ROXY CI Evaluation Harness
Continuous evaluation for memory, reasoning, hallucination, and task completion.

Run in CI to gate merges on regression.
"""
import os
import sys
import time
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roxy.eval")

# Configuration
ROXY_BASE_URL = os.getenv("ROXY_BASE_URL", "http://127.0.0.1:8766")
ROXY_TOKEN_FILE = os.getenv("ROXY_TOKEN_FILE", "/home/mark/.roxy/secret.token")
PASS_THRESHOLD = float(os.getenv("ROXY_EVAL_PASS_THRESHOLD", "0.95"))
SKIP_MCP_GATE = os.getenv("ROXY_EVAL_SKIP_MCP_GATE", "0").lower() in ("1", "true", "yes")
CRITICAL_MCP_SERVERS = [
    item.strip()
    for item in os.getenv(
        "ROXY_EVAL_CRITICAL_MCP_SERVERS",
        "roxy-content,roxy-desktop,github,filesystem",
    ).split(",")
    if item.strip()
]

# Load canonical identity
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from canonical_identity import CANONICAL_USER_ID, CANONICAL_NAME, CANONICAL_ROLE, USER_ALIASES
except ImportError:
    # Fallback defaults
    CANONICAL_USER_ID = "mark-roxy-canonical"
    CANONICAL_NAME = "Mark"
    CANONICAL_ROLE = "CEO of MindSong Studios"
    USER_ALIASES = ["mark", "Mark", "CEO"]


class ROXYEvaluator:
    """ROXY evaluation harness."""
    
    def __init__(self):
        self.results: List[Dict] = []
        self._last_query_payload: Dict = {}
        self._load_token()
    
    def _load_token(self):
        """Load ROXY auth token."""
        try:
            with open(ROXY_TOKEN_FILE) as f:
                self.token = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            self.token = ""
    
    def _query(self, command: str, session: str = "eval", user_id: Optional[str] = None) -> Dict:
        """Execute ROXY query and return response."""
        import requests
        effective_user_id = user_id or CANONICAL_USER_ID
        try:
            resp = requests.post(
                f"{ROXY_BASE_URL}/run",
                headers={
                    "X-ROXY-Token": self.token,
                    "X-ROXY-Session": session,
                    "X-ROXY-User-Id": str(effective_user_id),
                    "Content-Type": "application/json"
                },
                json={"command": command, "stream": False},
                timeout=60
            )
            payload = resp.json()
            self._last_query_payload = payload if isinstance(payload, dict) else {}
            return payload
        except Exception as e:
            logger.error(f"Query failed: {e}")
            payload = {"status": "error", "message": str(e)}
            self._last_query_payload = payload
            return payload

    def _record_eval_trace(self, test_name: str, query: str, verdict: Dict) -> None:
        try:
            from trace_spine import get_trace_spine

            trace_id = (
                (self._last_query_payload.get("metadata") or {}).get("trace_id")
                or f"eval-{test_name}-{int(time.time() * 1000)}"
            )
            get_trace_spine().record_eval_trace(trace_id, query, self._last_query_payload, verdict)
        except Exception as exc:
            logger.debug(f"Eval trace emission failed (non-critical): {exc}")

    def _evaluate_identity_assertion(self, test_name: str, query: str) -> Dict:
        """Enforce canonical identity assertion: user name + role."""
        result = self._query(query, session=f"eval-memory-{test_name}", user_id=CANONICAL_USER_ID)
        if result.get("status") != "success":
            return {"test": test_name, "category": "memory", "passed": False, "error": "Query failed"}

        response_text = result.get("result", "")
        lower = response_text.lower()
        memory_meta = result.get("metadata", {}).get("memory", {})
        memory_injected = memory_meta.get("context_injected", False)
        memory_items = int(memory_meta.get("memory_items", 0))
        profile_items = int(memory_meta.get("profile_items", 0))

        aliases = {str(CANONICAL_NAME).strip().lower()}
        aliases.update(str(alias).strip().lower() for alias in USER_ALIASES or [])
        name_match = any(alias and alias in lower for alias in aliases)

        role_tokens = [
            token.lower()
            for token in re.findall(r"[a-zA-Z0-9]+", str(CANONICAL_ROLE))
            if len(token) > 2
        ]
        role_match = any(token in lower for token in role_tokens)

        passed = memory_injected and (memory_items + profile_items) > 0 and name_match and role_match
        return {
            "test": test_name,
            "category": "memory",
            "passed": passed,
            "memory_items": memory_items,
            "profile_items": profile_items,
            "memory_injected": memory_injected,
            "name_match": name_match,
            "role_match": role_match,
            "canonical_user_id": CANONICAL_USER_ID,
            "response_preview": response_text[:240],
        }
    
    def _evaluate_memory_recall(self, test_name: str, query: str, expected_facts: List[str]) -> Dict:
        """Test memory recall capability."""
        result = self._query(query, session=f"eval-memory-{test_name}")
        
        if result.get("status") != "success":
            return {"test": test_name, "category": "memory", "passed": False, "error": "Query failed"}
        
        response_text = result.get("result", "")
        memory_meta = result.get("metadata", {}).get("memory", {})
        
        # Check memory was injected
        memory_injected = memory_meta.get("context_injected", False)
        memory_items = memory_meta.get("memory_items", 0)
        profile_items = memory_meta.get("profile_items", 0)
        memory_context_items = int(memory_items) + int(profile_items)
        
        # Check expected facts are mentioned
        facts_found = sum(1 for fact in expected_facts if fact.lower() in response_text.lower())
        fact_score = facts_found / len(expected_facts) if expected_facts else 0
        
        passed = memory_injected and memory_context_items > 0 and fact_score >= 0.5
        
        return {
            "test": test_name,
            "category": "memory",
            "passed": passed,
            "score": fact_score,
            "memory_items": memory_items,
            "profile_items": profile_items,
            "response_preview": response_text[:200]
        }
    
    def _evaluate_confidence_calibration(self, test_name: str, query: str) -> Dict:
        """Test confidence calibration."""
        result = self._query(query, session=f"eval-confidence-{test_name}")
        
        if result.get("status") != "success":
            return {"test": test_name, "category": "confidence", "passed": False, "error": "Query failed"}
        
        reflection_meta = result.get("metadata", {}).get("reflection", {})
        confidence = reflection_meta.get("confidence", 0)
        flags = reflection_meta.get("flags", [])
        
        # High confidence should have no flags
        # Low confidence should have appropriate flags
        if confidence >= 0.9:
            passed = len([f for f in flags if "CLAIM" in f]) == 0
        else:
            passed = True  # Low confidence responses may have flags
        
        return {
            "test": test_name,
            "category": "confidence",
            "passed": passed,
            "confidence": confidence,
            "flags": flags
        }
    
    def _evaluate_response_quality(self, test_name: str, query: str, min_length: int = 20) -> Dict:
        """Test response quality metrics."""
        result = self._query(query, session=f"eval-quality-{test_name}")
        
        if result.get("status") != "success":
            return {"test": test_name, "category": "quality", "passed": False, "error": "Query failed"}
        
        response_text = result.get("result", "")
        response_time = result.get("response_time", 0)
        
        # Check response is substantive
        has_content = len(response_text.strip()) >= min_length
        has_source = "source" in response_text.lower() or "📌" in response_text
        
        passed = has_content and has_source
        
        return {
            "test": test_name,
            "category": "quality",
            "passed": passed,
            "response_length": len(response_text),
            "response_time": response_time
        }

    def _evaluate_critical_mcp_availability(self) -> Dict:
        """Fail qualification if any critical MCP server is unreachable or empty."""
        if SKIP_MCP_GATE:
            return {
                "test": "mcp_gate",
                "category": "runtime",
                "passed": True,
                "skipped": True,
                "details": {"reason": "ROXY_EVAL_SKIP_MCP_GATE=1"},
            }
        try:
            from mcp_client import MCPClient
            import asyncio

            async def _run_check():
                client = MCPClient()
                await client.initialize()
                details = {}
                passed = True
                try:
                    for server_id in CRITICAL_MCP_SERVERS:
                        health = await client.health_check(server_id)
                        tools = await client.list_tools(server_id)
                        details[server_id] = {
                            "connected": bool(health.get("connected")),
                            "tool_count": len(tools),
                        }
                        if not health.get("connected") or len(tools) == 0:
                            passed = False
                finally:
                    await client.disconnect_all()
                return passed, details

            passed, details = asyncio.run(_run_check())
            return {
                "test": "mcp_gate",
                "category": "runtime",
                "passed": passed,
                "details": details,
            }
        except Exception as e:
            return {
                "test": "mcp_gate",
                "category": "runtime",
                "passed": False,
                "error": str(e),
            }
    
    def run_evaluation_suite(self) -> Dict:
        """Run full evaluation suite."""
        logger.info("Starting ROXY evaluation suite...")
        self.results.append(self._evaluate_critical_mcp_availability())
        
        tests = [
            # Memory tests - canonical identity requires both name and role grounding
            ("memory_identity", "Who am I?", []),
            ("memory_production", "What is my SkyBeam render queue status?", ["skybeam", "render"]),
            ("memory_preferences", "What are my preferences?", ["electronic", "music"]),
            
            # Confidence tests
            ("confidence_known", "What is my name?", []),
            ("confidence_unknown", "What did I have for breakfast yesterday?", []),
            
            # Quality tests
            ("quality_technical", "Explain how memory retrieval works.", 100),
            ("quality_production", "What is the SkyBeam render status?", 50),
        ]
        
        for test_name, query, extra in tests:
            logger.info(f"Running test: {test_name}")
            
            if test_name == "memory_identity":
                result = self._evaluate_identity_assertion(test_name, query)
            elif test_name.startswith("memory_"):
                result = self._evaluate_memory_recall(test_name, query, extra)
            elif test_name.startswith("confidence_"):
                result = self._evaluate_confidence_calibration(test_name, query)
            elif test_name.startswith("quality_"):
                result = self._evaluate_response_quality(test_name, query, extra)
            else:
                continue
            
            self.results.append(result)
            self._record_eval_trace(test_name, query, result)
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            logger.info(f"  {status}: {test_name}")
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict:
        """Generate evaluation report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        pass_rate = passed / total if total > 0 else 0
        
        by_category = {}
        for r in self.results:
            cat = r.get("category", "unknown")
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if r["passed"]:
                by_category[cat]["passed"] += 1
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
            "meets_threshold": pass_rate >= PASS_THRESHOLD,
            "by_category": by_category,
            "results": self.results
        }
        
        return report


def main():
    """Main entry point."""
    evaluator = ROXYEvaluator()
    report = evaluator.run_evaluation_suite()
    
    print("\n" + "=" * 70)
    print("ROXY EVALUATION REPORT")
    print("=" * 70)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Pass Rate: {report['pass_rate']*100:.1f}%")
    print(f"Meets Threshold ({PASS_THRESHOLD*100:.0f}%): {'✅ YES' if report['meets_threshold'] else '❌ NO'}")
    
    print("\nBy Category:")
    for cat, stats in report.get("by_category", {}).items():
        pct = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cat}: {pct:.0f}% ({stats['passed']}/{stats['total']})")
    
    print("\nDetailed Results:")
    for r in report.get("results", []):
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} [{r['category']}] {r['test']}")
    
    print("=" * 70)
    
    # Exit with error code if threshold not met
    sys.exit(0 if report["meets_threshold"] else 1)


if __name__ == "__main__":
    main()
