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
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("roxy.eval")

# Configuration
ROXY_BASE_URL = os.getenv("ROXY_BASE_URL", "http://127.0.0.1:8766")
ROXY_TOKEN_FILE = os.getenv("ROXY_TOKEN_FILE", "/home/mark/.roxy/secret.token")
PASS_THRESHOLD = 0.85  # 85% pass rate required

# Load canonical identity
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from canonical_identity import CANONICAL_NAME, CANONICAL_ROLE, USER_ALIASES
except ImportError:
    # Fallback defaults
    CANONICAL_NAME = "Mark"
    CANONICAL_ROLE = "CEO of MindSong Studios"
    USER_ALIASES = ["mark", "Mark", "CEO"]


class ROXYEvaluator:
    """ROXY evaluation harness."""
    
    def __init__(self):
        self.results: List[Dict] = []
        self._load_token()
    
    def _load_token(self):
        """Load ROXY auth token."""
        try:
            with open(ROXY_TOKEN_FILE) as f:
                self.token = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            self.token = ""
    
    def _query(self, command: str, session: str = "eval") -> Dict:
        """Execute ROXY query and return response."""
        import requests
        try:
            resp = requests.post(
                f"{ROXY_BASE_URL}/run",
                headers={
                    "X-ROXY-Token": self.token,
                    "X-ROXY-Session": session,
                    "Content-Type": "application/json"
                },
                json={"command": command, "stream": False},
                timeout=60
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {"status": "error", "message": str(e)}
    
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
        
        # Check expected facts are mentioned
        facts_found = sum(1 for fact in expected_facts if fact.lower() in response_text.lower())
        fact_score = facts_found / len(expected_facts) if expected_facts else 0
        
        passed = memory_injected and memory_items > 0 and fact_score >= 0.5
        
        return {
            "test": test_name,
            "category": "memory",
            "passed": passed,
            "score": fact_score,
            "memory_items": memory_items,
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
    
    def run_evaluation_suite(self) -> Dict:
        """Run full evaluation suite."""
        logger.info("Starting ROXY evaluation suite...")
        
        tests = [
            # Memory tests - use canonical identity config
            # Identity test: check for name OR role (more flexible)
            ("memory_identity", "Who am I?", [CANONICAL_NAME.lower(), CANONICAL_ROLE.split()[0].lower()]),
            ("memory_production", "What is my production state?", ["mindsong", "skybeam", "render"]),
            ("memory_preferences", "What are my preferences?", ["mindsong", "electronic", "music"]),
            
            # Confidence tests
            ("confidence_known", "What is my name?", []),
            ("confidence_unknown", "What did I have for breakfast yesterday?", []),
            
            # Quality tests
            ("quality_technical", "Explain how memory retrieval works.", 100),
            ("quality_production", "What is the SkyBeam render status?", 50),
        ]
        
        for test_name, query, extra in tests:
            logger.info(f"Running test: {test_name}")
            
            if test_name.startswith("memory_"):
                result = self._evaluate_memory_recall(test_name, query, extra)
            elif test_name.startswith("confidence_"):
                result = self._evaluate_confidence_calibration(test_name, query)
            elif test_name.startswith("quality_"):
                result = self._evaluate_response_quality(test_name, query, extra)
            else:
                continue
            
            self.results.append(result)
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
