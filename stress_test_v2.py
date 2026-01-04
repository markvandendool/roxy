#!/usr/bin/env python3
"""
ROXY STRESS TEST v2.0 - Comprehensive Validation
================================================
Tests ALL systems including Sprint 5 features:
- Core endpoints & health
- MCP Music Tools (9 tools)
- Dual Persona System
- Speculative Decoder
- Security & Rate Limiting
- Infrastructure Services
"""

import sys
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed

ROXY_DIR = Path.home() / ".roxy"
CORE_URL = "http://127.0.0.1:8766"
AUTH_TOKEN = None

# Load auth token
token_file = ROXY_DIR / "secret.token"
if token_file.exists():
    AUTH_TOKEN = token_file.read_text().strip()


class TestResults:
    """Track test results with detailed logging"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        self.start_time = datetime.now()
    
    def ok(self, name: str, details: str = ""):
        self.passed.append({"name": name, "details": details})
        print(f"  ✅ {name}")
    
    def fail(self, name: str, error: str):
        self.failed.append({"name": name, "error": error})
        print(f"  ❌ {name}: {error[:60]}")
    
    def warn(self, name: str, msg: str):
        self.warnings.append({"name": name, "msg": msg})
        print(f"  ⚠️  {name}: {msg[:60]}")
    
    def summary(self):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total = len(self.passed) + len(self.failed)
        pct = (len(self.passed) / total * 100) if total > 0 else 0
        
        print("\n" + "═" * 60)
        print("STRESS TEST RESULTS")
        print("═" * 60)
        print(f"Total Tests: {total}")
        print(f"✅ Passed:   {len(self.passed)}")
        print(f"❌ Failed:   {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"Success:    {pct:.1f}%")
        print(f"Duration:   {elapsed:.2f}s")
        print("═" * 60)
        
        if self.failed:
            print("\n❌ FAILURES:")
            for f in self.failed:
                print(f"  • {f['name']}: {f['error']}")
        
        return len(self.failed) == 0


results = TestResults()


def http_request(endpoint: str, method: str = "GET", data: dict = None, timeout: int = 10):
    """Make HTTP request to ROXY"""
    url = f"{CORE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["X-ROXY-Token"] = AUTH_TOKEN
    
    try:
        if method == "POST" and data:
            body = json.dumps(data).encode()
            req = Request(url, data=body, headers=headers, method="POST")
        else:
            req = Request(url, headers=headers)
        
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}", "status_code": e.code}
    except URLError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# CORE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_core_health():
    """Test core health endpoint"""
    print("\n🏥 CORE HEALTH")
    print("-" * 40)
    
    r = http_request("/health")
    if r.get("status") == "ok":
        results.ok("Health endpoint")
        
        # Check sub-services
        checks = r.get("checks", {})
        for service, status in checks.items():
            if isinstance(status, dict):
                if status.get("initialized"):
                    results.ok(f"  {service}")
                else:
                    results.warn(f"  {service}", "not initialized")
            elif status == "ok":
                results.ok(f"  {service}")
            else:
                results.warn(f"  {service}", str(status)[:40])
    else:
        results.fail("Health endpoint", r.get("error", "unknown"))


def test_core_endpoints():
    """Test core API endpoints"""
    print("\n📡 CORE ENDPOINTS")
    print("-" * 40)
    
    # Test /metrics
    r = http_request("/metrics")
    if r and "metrics" in r:
        results.ok("/metrics")
    else:
        results.warn("/metrics", "No metrics returned")
    
    # Test /modes
    r = http_request("/modes")
    if r and "modes" in r:
        results.ok("/modes")
    else:
        results.warn("/modes", "No modes returned")
    
    # Test /run with simple command
    r = http_request("/run", "POST", {"command": "what time is it"}, timeout=30)
    if r and r.get("status") == "success":
        results.ok("/run command routing")
    elif r and "error" in r:
        results.fail("/run command", r["error"])
    else:
        results.warn("/run command", "Unexpected response")


# ═══════════════════════════════════════════════════════════════════════════════
# MCP MUSIC TOOLS (Sprint 5)
# ═══════════════════════════════════════════════════════════════════════════════

def test_mcp_music_tools():
    """Test all 9 MCP music tools"""
    print("\n🎸 MCP MUSIC TOOLS")
    print("-" * 40)
    
    tests = [
        ("play_chord", {"chord": "Am7", "instrument": "guitar"}),
        ("get_scale", {"root": "E", "scale_type": "pentatonic_minor"}),
        ("suggest_next_chord", {"current_chords": ["C", "Am", "F"]}),
        ("transpose_song", {"chords": ["C", "Am", "F", "G"], "from_key": "C major", "to_key": "E major"}),
        ("identify_chord_from_notes", {"notes": ["E", "G#", "B"]}),
        ("play_progression", {"chords": ["G", "D", "Em", "C"], "tempo": 100}),
        ("get_chord_voicing", {"chord": "Dm", "instrument": "guitar"}),
        ("search_songs_by_progression", {"progression": "I-V-vi-IV"}),
        ("generate_practice_routine", {"skill_level": "intermediate", "instrument": "guitar"}),
    ]
    
    for tool, params in tests:
        r = http_request(f"/mcp/music_tools/{tool}", "POST", params, timeout=5)
        if r.get("status") == "success":
            results.ok(f"mcp/{tool}")
        elif "error" in r:
            results.fail(f"mcp/{tool}", r["error"])
        else:
            results.warn(f"mcp/{tool}", "Missing status field")


def test_mcp_edge_cases():
    """Test MCP edge cases and error handling"""
    print("\n🔧 MCP EDGE CASES")
    print("-" * 40)
    
    # Invalid tool
    r = http_request("/mcp/music_tools/nonexistent_tool", "POST", {})
    if "error" in r:
        results.ok("Invalid tool rejected")
    else:
        results.fail("Invalid tool", "Should return error")
    
    # Invalid module
    r = http_request("/mcp/fake_module/fake_tool", "POST", {})
    if "error" in r or r.get("status_code") == 404:
        results.ok("Invalid module rejected")
    else:
        results.fail("Invalid module", "Should return 404")
    
    # Empty params
    r = http_request("/mcp/music_tools/play_chord", "POST", {})
    if r.get("status") == "success" or r.get("chord"):  # Should use defaults
        results.ok("Empty params → defaults")
    else:
        results.warn("Empty params", str(r)[:40])
    
    # Invalid chord
    r = http_request("/mcp/music_tools/play_chord", "POST", {"chord": "ZZZZ123"})
    if "error" in r:  # Should return error for invalid note
        results.ok("Invalid chord → error")
    elif r.get("status") == "success":
        results.warn("Invalid chord", "Accepted unexpectedly")
    else:
        results.warn("Invalid chord", str(r)[:40])


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL PERSONA (Sprint 5)
# ═══════════════════════════════════════════════════════════════════════════════

def test_dual_persona():
    """Test dual persona system (Rocky/ROXY)"""
    print("\n🎭 DUAL PERSONA")
    print("-" * 40)
    
    # Test Rocky persona via /run
    rocky_query = "[PERSONA: ROCKY] What are the notes in a G major chord?"
    r = http_request("/run", "POST", {"command": rocky_query}, timeout=60)
    if r.get("status") == "success":
        results.ok("Rocky persona query")
    else:
        results.warn("Rocky persona", r.get("error", "timeout")[:40])
    
    # Test ROXY persona via /run  
    roxy_query = "[PERSONA: ROXY] List files in current directory"
    r = http_request("/run", "POST", {"command": roxy_query}, timeout=60)
    if r.get("status") == "success":
        results.ok("ROXY persona query")
    else:
        results.warn("ROXY persona", r.get("error", "timeout")[:40])


# ═══════════════════════════════════════════════════════════════════════════════
# SPECULATIVE DECODER (Sprint 6)
# ═══════════════════════════════════════════════════════════════════════════════

def test_speculative_decoder():
    """Test speculative decoder initialization"""
    print("\n⚡ SPECULATIVE DECODER")
    print("-" * 40)
    
    spec_file = ROXY_DIR / "speculative_decoder.py"
    if not spec_file.exists():
        results.fail("speculative_decoder.py", "File not found")
        return
    
    results.ok("speculative_decoder.py exists")
    
    # Test import
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("speculative_decoder", spec_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        sd = module.SpeculativeDecoder()
        if sd.draft_model == "tinyllama:latest":
            results.ok("Draft model configured")
        else:
            results.warn("Draft model", f"Using {sd.draft_model}")
        
        if sd.target_model == "qwen2.5:32b":
            results.ok("Target model configured")
        else:
            results.warn("Target model", f"Using {sd.target_model}")
            
    except Exception as e:
        results.fail("Decoder import", str(e)[:50])


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_security():
    """Test security features"""
    print("\n🔒 SECURITY")
    print("-" * 40)
    
    # Test auth requirement (if enabled)
    test_token = AUTH_TOKEN
    AUTH_TOKEN_backup = AUTH_TOKEN
    
    # Test dangerous command blocking
    dangerous = ["rm -rf /", "sudo rm -rf", "; cat /etc/passwd"]
    blocked = 0
    for cmd in dangerous:
        r = http_request("/run", "POST", {"command": cmd})
        if r.get("status_code") == 403 or "blocked" in str(r).lower():
            blocked += 1
    
    if blocked > 0:
        results.ok(f"Blocked {blocked}/{len(dangerous)} dangerous commands")
    else:
        results.warn("Dangerous command filter", "Not blocking test commands")
    
    # Test SQL injection attempt
    r = http_request("/run", "POST", {"command": "'; DROP TABLE users; --"})
    if r.get("status_code") == 403 or r.get("status") != "success":
        results.ok("SQL injection blocked")
    else:
        results.warn("SQL injection", "Query executed (may be handled safely)")


# ═══════════════════════════════════════════════════════════════════════════════
# INFRASTRUCTURE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_infrastructure():
    """Test infrastructure services"""
    print("\n🏗️ INFRASTRUCTURE")
    print("-" * 40)
    
    r = http_request("/infrastructure")
    if r and r.get("status") == "ok":
        results.ok("Infrastructure endpoint")
        infra = r.get("infrastructure", {})
        for service, status in infra.items():
            if status == "ready" or status == True:
                results.ok(f"  {service}")
            else:
                results.warn(f"  {service}", str(status)[:30])
    else:
        results.warn("Infrastructure", r.get("error", "unknown"))
    
    # Test infrastructure stats
    r = http_request("/infrastructure/stats")
    if r and "stats" in r:
        results.ok("Infrastructure stats")
    else:
        results.warn("Infrastructure stats", "Not available")


# ═══════════════════════════════════════════════════════════════════════════════
# CONCURRENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_concurrency():
    """Test concurrent request handling"""
    print("\n🔄 CONCURRENCY")
    print("-" * 40)
    
    def make_quick_request(i):
        return http_request("/health", timeout=5)
    
    success = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_quick_request, i) for i in range(20)]
        for f in as_completed(futures, timeout=15):
            try:
                r = f.result()
                if r.get("status") == "ok":
                    success += 1
            except:
                pass
    
    if success >= 18:  # Allow some failures
        results.ok(f"Concurrent requests ({success}/20 succeeded)")
    elif success >= 10:
        results.warn("Concurrent requests", f"Only {success}/20 succeeded")
    else:
        results.fail("Concurrent requests", f"Only {success}/20 succeeded")


# ═══════════════════════════════════════════════════════════════════════════════
# RAG & SEARCH TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_rag():
    """Test RAG search functionality"""
    print("\n🔍 RAG & SEARCH")
    print("-" * 40)
    
    r = http_request("/run", "POST", {"command": "search for chord progressions"}, timeout=30)
    if r.get("status") == "success":
        results.ok("RAG query")
    else:
        results.warn("RAG query", r.get("error", "timeout")[:40])
    
    # Test memory recall
    r = http_request("/memory/recall", "POST", {"query": "test", "limit": 5})
    if r and "error" not in r:
        results.ok("Memory recall")
    else:
        results.warn("Memory recall", r.get("error", "unknown")[:40])


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 60)
    print("🔬 ROXY STRESS TEST v2.0")
    print("═" * 60)
    print(f"Target: {CORE_URL}")
    print(f"Auth: {'Configured' if AUTH_TOKEN else 'None'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_core_health()
    test_core_endpoints()
    test_mcp_music_tools()
    test_mcp_edge_cases()
    test_dual_persona()
    test_speculative_decoder()
    test_security()
    test_infrastructure()
    test_concurrency()
    test_rag()
    
    # Print summary
    success = results.summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
