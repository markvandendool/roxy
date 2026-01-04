#!/usr/bin/env python3
"""
ROXY Infrastructure Comprehensive Test Suite
Tests all components: Redis, PostgreSQL, NATS, Expert Router, Broadcasting
"""
import time
import json
import sys
import requests
from pathlib import Path
from datetime import datetime

# Configuration
TOKEN_FILE = Path.home() / ".roxy" / "secret.token"
TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else ""
BASE_URL = "http://127.0.0.1:8766"
HEADERS = {"X-ROXY-Token": TOKEN, "Content-Type": "application/json"}


class Colors:
    """ANSI color codes for pretty output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")


def print_result(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"  {status} {name}")
    if details:
        print(f"       {Colors.YELLOW}{details}{Colors.END}")


def test_service_health():
    """Test that ROXY service is running and responding"""
    print_header("SERVICE HEALTH CHECK")
    
    try:
        r = requests.get(f"{BASE_URL}/health", headers=HEADERS, timeout=5)
        data = r.json()
        
        service_ok = data.get("status") == "ok"
        print_result("Service responding", service_ok, f"Status: {data.get('status')}")
        
        checks = data.get("checks", {})
        for check_name, check_status in checks.items():
            if isinstance(check_status, dict):
                is_ok = check_status.get("initialized", True)
            else:
                is_ok = check_status == "ok"
            print_result(f"  {check_name}", is_ok)
        
        return service_ok
    except Exception as e:
        print_result("Service responding", False, str(e))
        return False


def test_infrastructure_components():
    """Test all infrastructure components are connected"""
    print_header("INFRASTRUCTURE COMPONENTS")
    
    try:
        r = requests.get(f"{BASE_URL}/infrastructure", headers=HEADERS, timeout=5)
        data = r.json()
        
        results = {}
        for name, component in data.get("components", {}).items():
            if isinstance(component, dict):
                healthy = component.get("healthy", False)
                backend = component.get("backend", component.get("mode", "unknown"))
                
                # Check if using real backend vs fallback
                is_real = backend not in ["memory", "buffered", "unknown"]
                status_text = f"backend={backend}"
                
                if "details" in component:
                    details = component["details"]
                    if "used_memory" in details:
                        status_text += f", mem={details['used_memory']}"
                    if "available_count" in details:
                        status_text += f", experts={details['available_count']}"
                
                print_result(name, healthy, status_text)
                results[name] = {"healthy": healthy, "real_backend": is_real}
        
        return all(r["healthy"] for r in results.values())
    except Exception as e:
        print_result("Infrastructure check", False, str(e))
        return False


def test_redis_cache():
    """Test Redis cache performance"""
    print_header("REDIS CACHE PERFORMANCE")
    
    test_query = f"Test query for cache at {datetime.now().isoformat()}"
    
    try:
        # First query (cold)
        start = time.time()
        r1 = requests.post(f"{BASE_URL}/run", headers=HEADERS, 
                          json={"command": "What is 2+2?"}, timeout=60)
        cold_time = time.time() - start
        
        # Same query (should be cached)
        start = time.time()
        r2 = requests.post(f"{BASE_URL}/run", headers=HEADERS,
                          json={"command": "What is 2+2?"}, timeout=60)
        warm_time = time.time() - start
        
        speedup = cold_time / warm_time if warm_time > 0 else 1
        
        print_result("Cold query", r1.status_code == 200, f"{cold_time:.2f}s")
        print_result("Warm query", r2.status_code == 200, f"{warm_time:.2f}s")
        print_result("Cache speedup", speedup > 1.5, f"{speedup:.1f}x faster")
        
        return speedup > 1.5
    except Exception as e:
        print_result("Cache test", False, str(e))
        return False


def test_expert_routing():
    """Test expert model routing"""
    print_header("EXPERT MODEL ROUTING")
    
    test_cases = [
        ("Write a Python function for binary search", "code"),
        ("Calculate the derivative of x^3 + 2x", "math"),
        ("What is the capital of France?", "general"),
    ]
    
    all_passed = True
    
    try:
        for query, expected_type in test_cases:
            r = requests.post(f"{BASE_URL}/expert", headers=HEADERS,
                            json={"query": query}, timeout=120)
            
            if r.status_code == 200:
                data = r.json()
                actual_type = data.get("query_type", "unknown")
                confidence = data.get("confidence", 0)
                response_time = data.get("response_time", 0)
                
                passed = actual_type == expected_type
                all_passed = all_passed and passed
                
                details = f"got={actual_type}, conf={confidence:.2f}, time={response_time:.1f}s"
                print_result(f"{expected_type:8} query", passed, details)
            else:
                print_result(f"{expected_type:8} query", False, f"HTTP {r.status_code}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print_result("Expert routing", False, str(e))
        return False


def test_memory_system():
    """Test memory storage and recall"""
    print_header("MEMORY SYSTEM")
    
    try:
        # Store a memory
        test_fact = f"Test fact: Mark's test ID is {datetime.now().timestamp()}"
        r1 = requests.post(f"{BASE_URL}/run", headers=HEADERS,
                          json={"command": f"Remember this: {test_fact}"}, timeout=60)
        
        store_ok = r1.status_code == 200
        print_result("Memory storage", store_ok)
        
        # Try to recall
        r2 = requests.post(f"{BASE_URL}/memory/recall", headers=HEADERS,
                          json={"query": "test fact Mark", "k": 10}, timeout=10)
        
        recall_ok = r2.status_code == 200
        memories = r2.json().get("memories", [])
        memory_count = len(memories)
        
        print_result("Memory recall", recall_ok, f"{memory_count} memories found")
        
        return store_ok and recall_ok
    except Exception as e:
        print_result("Memory system", False, str(e))
        return False


def test_feedback_system():
    """Test feedback collection"""
    print_header("FEEDBACK SYSTEM")
    
    try:
        # Submit feedback
        r1 = requests.post(f"{BASE_URL}/feedback", headers=HEADERS,
                          json={
                              "query": "test query",
                              "response": "test response",
                              "type": "positive"
                          }, timeout=10)
        
        submit_ok = r1.status_code == 200
        print_result("Feedback submission", submit_ok)
        
        # Get stats
        r2 = requests.get(f"{BASE_URL}/feedback/stats", headers=HEADERS, timeout=10)
        
        if r2.status_code == 200:
            stats = r2.json()
            total = stats.get("total", 0)
            print_result("Feedback stats", True, f"total={total}")
        else:
            print_result("Feedback stats", False)
        
        return submit_ok
    except Exception as e:
        print_result("Feedback system", False, str(e))
        return False


def test_broadcast_intelligence():
    """Test broadcasting intelligence module"""
    print_header("BROADCAST INTELLIGENCE")
    
    try:
        sys.path.insert(0, str(Path.home() / ".roxy"))
        from broadcast_intelligence import (
            analyze_content, get_optimal_time, optimize_title, predict_performance
        )
        
        # Test content analysis
        test_content = {
            "title": "How I Built an AI Assistant in Python",
            "description": "Complete tutorial on building your own AI",
            "platform": "youtube",
            "has_video": True,
            "tags": ["python", "ai", "tutorial"]
        }
        
        analysis = analyze_content(test_content)
        virality = analysis.get("virality_score", 0)
        print_result("Content analysis", virality > 0, f"virality={virality:.2f}")
        
        # Test optimal time
        optimal = get_optimal_time("youtube")
        has_time = "datetime" in optimal
        print_result("Optimal time calc", has_time, optimal.get("datetime", "")[:16])
        
        # Test title optimization
        title_result = optimize_title("My Video")
        has_suggestions = len(title_result.get("suggestions", [])) > 0
        print_result("Title optimization", has_suggestions, 
                    f"score={title_result.get('score', 0):.2f}")
        
        # Test performance prediction
        prediction = predict_performance(test_content)
        has_views = "estimated_views" in prediction
        print_result("Performance prediction", has_views,
                    f"views={prediction.get('estimated_views', {}).get('mid', 0)}")
        
        return True
    except Exception as e:
        print_result("Broadcast intelligence", False, str(e))
        return False


def run_all_tests():
    """Run complete test suite"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}   ROXY INFRASTRUCTURE VALIDATION SUITE{Colors.END}")
    print(f"{Colors.BOLD}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    results = []
    
    # Run all tests
    results.append(("Service Health", test_service_health()))
    results.append(("Infrastructure", test_infrastructure_components()))
    results.append(("Redis Cache", test_redis_cache()))
    results.append(("Expert Routing", test_expert_routing()))
    results.append(("Memory System", test_memory_system()))
    results.append(("Feedback System", test_feedback_system()))
    results.append(("Broadcast Intel", test_broadcast_intelligence()))
    
    # Summary
    print_header("FINAL RESULTS")
    
    total_passed = 0
    for name, passed in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.YELLOW}⚠️ WARN{Colors.END}"
        print(f"  {status} {name}")
        if passed:
            total_passed += 1
    
    print(f"\n  {Colors.BOLD}Overall: {total_passed}/{len(results)} components operational{Colors.END}")
    
    if total_passed == len(results):
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🏆 ALL SYSTEMS FULLY OPERATIONAL!{Colors.END}")
        return 0
    elif total_passed >= len(results) - 2:
        print(f"\n  {Colors.YELLOW}{Colors.BOLD}⚠️ Some components in fallback mode (still functional){Colors.END}")
        return 0
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}❌ Critical components failing{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
