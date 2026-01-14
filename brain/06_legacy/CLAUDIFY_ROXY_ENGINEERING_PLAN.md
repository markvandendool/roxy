# CLAUDIFY ROXY - ENGINEERING PLAN
**Date:** 2026-01-01  
**Objective:** Eliminate dual-stack interference, fix P0/P1/P2 issues, achieve Claude Code-class reliability  
**Duration:** 4-6 hours (6 phases)  
**Success Criteria:** 100% stress test pass rate, deterministic tool execution, zero hallucinations

---

## PHASE 0: ENVIRONMENT CLEANUP (CRITICAL - 30 MINUTES)
**Status:** 🚨 **BLOCKING ALL OTHER WORK**  
**Problem:** Multiple ROXY processes competing for port 8766, causing hangs/timeouts/mixed responses

### 0.1 Diagnostic Evidence Collection
```bash
# Evidence 1: Who owns port 8766
ss -lptn 'sport = :8766' > /tmp/roxy_port_check.txt

# Evidence 2: All ROXY-related processes
ps aux | egrep -i '(roxy|jarvis).*python' | egrep -v 'egrep|grep' > /tmp/roxy_processes.txt

# Evidence 3: Systemd units
systemctl --user list-units --all | egrep -i '(roxy|jarvis)' > /tmp/roxy_units.txt
systemctl --user status roxy-core --no-pager -l > /tmp/roxy_core_status.txt

# Evidence 4: Legacy /opt/roxy presence
ls -la /opt/roxy/ > /tmp/opt_roxy_contents.txt 2>&1 || echo "Not found" > /tmp/opt_roxy_contents.txt
```

### 0.2 Kill All Legacy Processes (Deterministic)
```bash
#!/bin/bash
# File: /tmp/kill_legacy_roxy.sh

echo "=== Killing Legacy ROXY Processes ==="

# Kill by exact path match
pkill -9 -f '/opt/roxy/services/roxy_interface.py' || true
pkill -9 -f '/opt/roxy/services/roxy_core.py' || true
pkill -9 -f '/opt/roxy/services/jarvis_core.py' || true
pkill -9 -f 'roxy_interface.py' || true

# Kill any python process binding to 8766 that ISN'T our systemd service
for pid in $(lsof -ti:8766 2>/dev/null); do
  cmdline=$(ps -p $pid -o args= | head -1)
  if ! echo "$cmdline" | grep -q "/home/mark/.roxy/roxy_core.py"; then
    echo "Killing PID $pid: $cmdline"
    kill -9 $pid 2>/dev/null || true
  fi
done

# Wait for cleanup
sleep 2

# Verify nothing left
ps aux | egrep -i '(roxy|jarvis).*python' | egrep -v 'egrep|grep' || echo "✅ All legacy processes killed"
```

### 0.3 Archive /opt/roxy Stack (Permanent)
```bash
#!/bin/bash
# File: /tmp/archive_opt_roxy.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_PATH="/opt/roxy.LEGACY.$TIMESTAMP"

if [ -d "/opt/roxy" ]; then
  echo "Archiving /opt/roxy to $ARCHIVE_PATH"
  sudo mv /opt/roxy "$ARCHIVE_PATH"
  
  # Create marker file
  sudo tee "$ARCHIVE_PATH/ARCHIVED_REASON.txt" << 'EOF'
This stack was archived on 2026-01-01 due to dual-stack interference.

Issues caused:
- Port 8766 conflicts (multiple listeners)
- Hallucinations (roxy_interface.py broken)
- Mixed responses (sometimes ~/.roxy, sometimes /opt/roxy)
- Connection timeouts (competing services)

Canonical ROXY location: ~/.roxy/
Canonical service: systemctl --user status roxy-core
EOF

  echo "✅ Archived to $ARCHIVE_PATH"
else
  echo "⚠️  /opt/roxy not found (already archived?)"
fi
```

### 0.4 Single-Listener Enforcement (Systemd Guard)
**File:** `~/.config/systemd/user/roxy-core.service`

Add pre-start check:
```ini
[Service]
ExecStartPre=/bin/bash -c 'if ss -lptn "sport = :8766" | grep -v roxy_core; then echo "ERROR: Port 8766 already bound"; exit 1; fi'
ExecStart=/home/mark/.roxy/venv/bin/python /home/mark/.roxy/roxy_core.py
Restart=on-failure
RestartSec=5
```

### 0.5 Verification (MUST PASS)
```bash
# Test 1: Single listener only
ss -lptn 'sport = :8766' | wc -l  # Must be 2 (header + one listener)

# Test 2: Only ~/.roxy process
ps aux | grep roxy_core | grep -v grep | grep -c "/home/mark/.roxy"  # Must be 1

# Test 3: Health check responds
curl -s -H "X-ROXY-Token: $(cat ~/.roxy/secret.token)" http://127.0.0.1:8766/health | jq -e '.status == "ok"'

# Test 4: No legacy units
systemctl --user list-units --all | egrep -i '(roxy|jarvis)' | grep -v roxy-core | wc -l  # Must be 0
```

**Exit Criteria:** All 4 tests pass, zero legacy processes, single listener confirmed

---

## PHASE 1: FIX REQUEST ENCODING (P0 - 45 MINUTES)
**Problem:** Current stress tests send malformed JSON, causing "Expecting ',' delimiter" errors

### 1.1 Create Gold-Standard Request Helper
**File:** `~/.roxy/test_helpers.sh`

```bash
#!/bin/bash

roxy_request() {
  local command="$1"
  local timeout="${2:-10}"
  
  local token=$(cat ~/.roxy/secret.token)
  
  # Use jq to build JSON (NO manual escaping)
  jq -n --arg c "$command" '{command:$c}' | \
    curl -sS \
      --max-time "$timeout" \
      --retry 2 \
      --retry-all-errors \
      -H "X-ROXY-Token: $token" \
      -H "Content-Type: application/json" \
      -d @- \
      http://127.0.0.1:8766/run
}

# Export for use in tests
export -f roxy_request
```

### 1.2 Example Correct Usage
```bash
# Simple command
roxy_request "what are your capabilities"

# JSON tool call (NO escaping needed)
roxy_request '{"tool": "read_file", "args": {"file_path": "~/.roxy/config.json"}}'

# RUN_TOOL syntax
roxy_request 'RUN_TOOL list_files {"path": "~/.roxy", "pattern": "*.json"}'
```

### 1.3 Verification Test
```bash
# Test valid JSON reaches server
roxy_request "test" | jq -e '.status == "success"'

# Test tool call doesn't cause JSON errors
roxy_request '{"tool": "list_files", "args": {"path": "~/.roxy"}}' | jq -e '.result' | grep -q "roxy_core.py"
```

**Exit Criteria:** Zero "Expecting delimiter" errors in logs, all requests return valid JSON

---

## PHASE 2: ELIMINATE JSON FOOTER (P1 - 60 MINUTES)
**Problem:** Current "__TOOLS_EXECUTED__" footer parsing is fragile, causes hangs

### 2.1 Define Structured Return Format
**File:** `~/.roxy/roxy_commands.py` (refactor)

```python
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class ToolExecution:
    name: str
    args: Dict[str, Any]
    result: str
    ok: bool
    error: Optional[str] = None

@dataclass
class CommandResponse:
    text: str
    tools_executed: List[ToolExecution]
    mode: str  # "rag" | "tool_direct" | "blocked" | "error"
    errors: List[str]
    confidence: Optional[float] = None

def to_json(self) -> str:
    return json.dumps(asdict(self), indent=2)
```

### 2.2 Refactor execute_command() to Return Structured Object
**Before:**
```python
def execute_command(cmd_type, args):
    # ... execute logic ...
    return result_string  # ❌ Unstructured text
```

**After:**
```python
def execute_command(cmd_type, args) -> CommandResponse:
    tools_executed = []
    errors = []
    
    try:
        if cmd_type == "tool_direct":
            tool_name = args[0]
            tool_args = args[1]
            result = execute_tool_direct(tool_name, tool_args)
            
            return CommandResponse(
                text=result,
                tools_executed=TOOLS_EXECUTED.copy(),  # Global tracking
                mode="tool_direct",
                errors=[]
            )
        
        elif cmd_type == "rag":
            result = query_rag(" ".join(args))
            return CommandResponse(
                text=result,
                tools_executed=[],
                mode="rag",
                errors=[],
                confidence=0.7  # From RAG metadata
            )
        
        elif cmd_type == "unavailable":
            capability = args[0]
            error_msg = get_capability_error(capability)
            return CommandResponse(
                text=error_msg,
                tools_executed=[],
                mode="blocked",
                errors=[f"Capability not available: {capability}"]
            )
    
    except Exception as e:
        return CommandResponse(
            text=f"ERROR: {e}",
            tools_executed=[],
            mode="error",
            errors=[str(e)]
        )
```

### 2.3 Update roxy_core.py to Handle Structured Response
**File:** `~/.roxy/roxy_core.py`

```python
# Parse structured response from roxy_commands.py
try:
    # Commands script now returns JSON
    result = subprocess.run([...], capture_output=True, text=True)
    response_data = json.loads(result.stdout)
    
    # Extract components
    text = response_data.get("text", "")
    tools_executed = response_data.get("tools_executed", [])
    mode = response_data.get("mode", "unknown")
    
    # Apply Truth Gate with actual tool evidence
    if TRUTH_GATE_AVAILABLE and mode in ["rag", "tool_direct"]:
        truth_gate = get_truth_gate()
        text = truth_gate.validate_response(text, tools_executed)
    
    # Return to client
    return {
        "status": "success",
        "result": text,
        "metadata": {
            "mode": mode,
            "tools_used": [t["name"] for t in tools_executed],
            "confidence": response_data.get("confidence")
        }
    }
except json.JSONDecodeError:
    # Fallback for backwards compatibility
    logger.error("roxy_commands.py returned non-JSON output")
    return {"status": "error", "result": result.stdout}
```

### 2.4 Update main() in roxy_commands.py
**Before:**
```python
result = execute_command(cmd_type, args)
print(f"\n{result}")

if TOOLS_EXECUTED:
    print("\n__TOOLS_EXECUTED__")  # ❌ Footer hack
    print(json.dumps(TOOLS_EXECUTED))
```

**After:**
```python
response = execute_command(cmd_type, args)  # Returns CommandResponse
print(response.to_json())  # ✅ Clean structured output
```

**Exit Criteria:** Zero footer parsing, all responses are valid JSON, tools_executed always present

---

## PHASE 3: FILE VERIFICATION INVARIANT (P2 - 45 MINUTES)
**Problem:** RAG invents file existence ("roxy_assistant.py", "45% Phase P1 completion")

### 3.1 Add File Claim Detection to Truth Gate
**File:** `~/.roxy/truth_gate.py`

```python
import re
from pathlib import Path

class TruthGate:
    # New pattern category
    FILE_CLAIM_PATTERNS = [
        r'(?:^|\s)(/[/\w.-]+\.\w+)',  # Absolute paths: /home/mark/file.py
        r'(?:^|\s)(~[/\w.-]+\.\w+)',  # Home paths: ~/file.py
        r'(?:^|\s)(\w+/(docs|src|scripts|tests)/[/\w.-]+)',  # Repo paths: mindsong/docs/X.md
        r'(?:file|document|script):\s*([/\w.-]+\.\w+)',  # Labeled: file: config.py
        r'(\d+)\s+(?:files?|documents?)',  # Counts: "5 documents", "3 files"
    ]
    
    def _extract_file_claims(self, text: str) -> List[str]:
        """Extract all file path mentions from response"""
        claimed_files = []
        for pattern in self.FILE_CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE)
            claimed_files.extend(matches if isinstance(matches[0], str) else [m[0] for m in matches])
        return list(set(claimed_files))
    
    def _verify_file_claims(self, claimed_files: List[str], tools_executed: List[Dict]) -> Dict[str, bool]:
        """Check which file claims have tool evidence"""
        verified = {}
        
        # Get all files mentioned in tool executions
        tool_files = set()
        for tool in tools_executed:
            if tool['name'] in ['read_file', 'list_files', 'search_code']:
                # Extract files from tool result
                if 'result' in tool and tool['result']:
                    tool_files.update(re.findall(r'[\w/.-]+\.\w+', tool['result']))
                # Extract from args
                if 'args' in tool:
                    if 'file_path' in tool['args']:
                        tool_files.add(tool['args']['file_path'])
                    if 'path' in tool['args']:
                        tool_files.add(tool['args']['path'])
        
        # Check each claimed file
        for claimed in claimed_files:
            # Normalize paths for comparison
            claimed_norm = str(Path(claimed).expanduser())
            verified[claimed] = any(claimed_norm in str(Path(tf).expanduser()) for tf in tool_files)
        
        return verified
    
    def validate_response(self, llm_output: str, tools_executed: List[Dict]) -> str:
        """Enhanced validation with file claim checking"""
        
        # Existing action claim validation
        has_action_claims = any(pattern.search(llm_output) for pattern in self.action_patterns)
        has_tool_evidence = len(tools_executed) > 0
        
        if has_action_claims and not has_tool_evidence:
            return self._rewrite_hallucination(llm_output)
        
        # NEW: File claim validation
        claimed_files = self._extract_file_claims(llm_output)
        if claimed_files:
            verification = self._verify_file_claims(claimed_files, tools_executed)
            unverified = [f for f, verified in verification.items() if not verified]
            
            if unverified and not has_tool_evidence:
                # Block unverified file claims from RAG
                return self._rewrite_unverified_files(llm_output, unverified)
        
        # Add tool citations if we have evidence
        if has_tool_evidence:
            return self._add_tool_citations(llm_output, tools_executed)
        
        return llm_output
    
    def _rewrite_unverified_files(self, original: str, unverified_files: List[str]) -> str:
        """Rewrite response when files mentioned without proof"""
        return f"""⚠️ **FILE VERIFICATION REQUIRED**

The response mentioned files that haven't been verified:
{chr(10).join(f"- {f}" for f in unverified_files[:5])}

To verify these files exist, run:
```
RUN_TOOL list_files {{"path": "~/.roxy", "pattern": "*"}}
```

Or search for specific files:
```
RUN_TOOL search_code {{"query": "filename", "root": "~/.roxy"}}
```

**I cannot confirm file existence without running filesystem tools.**
"""
```

### 3.2 Add Preflight Verification for File Queries
**File:** `~/.roxy/roxy_commands.py`

```python
def parse_command(text):
    """Enhanced parser with preflight file verification"""
    
    text_lower = text.lower().strip()
    
    # Detect file-listing queries
    file_query_patterns = [
        "which files", "list files", "what files", "show files",
        "which documents", "list documents", "onboarding docs",
        "what's in the", "contents of"
    ]
    
    if any(pattern in text_lower for pattern in file_query_patterns):
        # Extract target directory from query
        repo_match = re.search(r'(mindsong|jarvis|roxy|gym)', text_lower)
        if repo_match:
            repo_name = repo_match.group(1)
            repo_map = {
                "mindsong": "/home/mark/mindsong-juke-hub",
                "jarvis": "/home/mark/jarvis-docs",
                "roxy": "/home/mark/.roxy",
                "gym": "/home/mark/gym"
            }
            
            # FORCE tool execution before RAG
            return ("tool_direct", ["list_files", {
                "path": repo_map.get(repo_name, "~/.roxy"),
                "pattern": "*"
            }])
    
    # ... rest of routing logic ...
```

**Exit Criteria:** Zero unverified file mentions in RAG responses, all file claims have tool evidence

---

## PHASE 4: ADD MISSING TOOLS TO REGISTRY (P1 - 60 MINUTES)
**Problem:** Only 3 tools in tool_direct (read_file, list_files, execute_command), missing search_code, git, obs

### 4.1 Add search_code Tool
**File:** `~/.roxy/roxy_commands.py`

```python
def execute_tool_direct(tool_name, tool_args):
    """Execute a tool directly without LLM"""
    
    # ... existing tools ...
    
    elif tool_name == "search_code":
        query = tool_args.get("query")
        root = tool_args.get("root", "~/.roxy")
        pattern = tool_args.get("pattern", "*.py")
        
        if not query:
            return "ERROR: search_code requires 'query' argument"
        
        root_path = Path(root).expanduser()
        if not root_path.exists():
            track_tool_execution(tool_name, tool_args, None, ok=False, error="Root path not found")
            return f"ERROR: Root path not found: {root}"
        
        # Use ripgrep if available, else grep
        try:
            import subprocess
            result = subprocess.run(
                ["rg", "--no-heading", "--line-number", query, str(root_path)],
                capture_output=True, text=True, timeout=10
            )
            matches = result.stdout
            if not matches:
                matches = f"No matches found for '{query}' in {root_path}"
            
            track_tool_execution(tool_name, tool_args, f"Found {len(matches.splitlines())} matches", ok=True)
            return matches
        
        except FileNotFoundError:
            # Fallback to Python glob + grep
            import fnmatch
            matches = []
            for file_path in root_path.rglob(pattern):
                if file_path.is_file():
                    try:
                        content = file_path.read_text()
                        if query.lower() in content.lower():
                            matches.append(str(file_path))
                    except:
                        pass
            
            result = "\n".join(matches) if matches else f"No matches found for '{query}'"
            track_tool_execution(tool_name, tool_args, f"Found {len(matches)} files", ok=True)
            return result
```

### 4.2 Add git_operations Tool
```python
elif tool_name == "git_operations":
    operation = tool_args.get("operation", "status")
    repo_path = tool_args.get("repo_path", "~/.roxy")
    
    repo = Path(repo_path).expanduser()
    if not (repo / ".git").exists():
        track_tool_execution(tool_name, tool_args, None, ok=False, error="Not a git repo")
        return f"ERROR: Not a git repository: {repo_path}"
    
    git_commands = {
        "status": ["git", "status", "--short"],
        "log": ["git", "log", "--oneline", "-10"],
        "diff": ["git", "diff", "--stat"],
        "branch": ["git", "branch", "-v"]
    }
    
    if operation not in git_commands:
        return f"ERROR: Unknown git operation '{operation}'. Available: {', '.join(git_commands.keys())}"
    
    result = subprocess.run(
        git_commands[operation],
        cwd=repo, capture_output=True, text=True, timeout=10
    )
    
    output = result.stdout or result.stderr
    track_tool_execution(tool_name, tool_args, f"Git {operation} completed", ok=(result.returncode == 0))
    return output
```

### 4.3 Add obs_control Tool
```python
elif tool_name == "obs_control":
    # Delegate to existing obs_skill.py
    command = tool_args.get("command", "status")
    
    obs_script = ROXY_DIR / "obs_skill.py"
    if not obs_script.exists():
        return "ERROR: OBS control not available (obs_skill.py missing)"
    
    result = subprocess.run(
        ["python3", str(obs_script), command],
        capture_output=True, text=True, timeout=30
    )
    
    output = result.stdout or result.stderr
    track_tool_execution(tool_name, tool_args, "OBS command executed", ok=(result.returncode == 0))
    return output
```

**Exit Criteria:** 6 tools operational (read_file, list_files, search_code, git_operations, obs_control, execute_command)

---

## PHASE 5: COMPREHENSIVE STRESS TEST (VALIDATION - 30 MINUTES)
**Prerequisites:** Phases 0-4 complete, single listener verified, structured responses working

### 5.1 New Stress Test Suite
**File:** `~/.roxy/stress_test_v2.sh`

```bash
#!/bin/bash
source ~/.roxy/test_helpers.sh

PASS=0
FAIL=0

test_case() {
    local name="$1"
    local command="$2"
    local expect="$3"
    
    echo "━━━ TEST: $name"
    
    start=$(date +%s%N)
    response=$(roxy_request "$command" 10)
    latency=$(( ($(date +%s%N) - start) / 1000000 ))
    
    # Validate JSON response
    if ! echo "$response" | jq -e '.status' > /dev/null 2>&1; then
        echo "❌ FAIL (${latency}ms) - Invalid JSON response"
        FAIL=$((FAIL + 1))
        return 1
    fi
    
    result=$(echo "$response" | jq -r '.result')
    
    if echo "$result" | grep -qi "$expect"; then
        echo "✅ PASS (${latency}ms)"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL (${latency}ms)"
        echo "   Expected: $expect"
        echo "   Got: $(echo "$result" | head -3)"
        FAIL=$((FAIL + 1))
    fi
    echo ""
}

echo "═══════════════════════════════════════════════════════════"
echo "         ROXY V2 STRESS TEST - STRUCTURED RESPONSES"
echo "═══════════════════════════════════════════════════════════"
echo ""

# SECTION 1: Tool Forcing
test_case "JSON tool call - read_file" \
    '{"tool": "read_file", "args": {"file_path": "~/.roxy/config.json"}}' \
    "port"

test_case "RUN_TOOL - list_files" \
    'RUN_TOOL list_files {"path": "~/.roxy", "pattern": "*.json"}' \
    "config.json"

test_case "JSON tool call - search_code" \
    '{"tool": "search_code", "args": {"query": "TruthGate", "root": "~/.roxy"}}' \
    "truth_gate.py"

# SECTION 2: Evidence Citations
test_case "Tool evidence present" \
    'RUN_TOOL list_files {"path": "~/.roxy", "pattern": "config.json"}' \
    "Actions Taken"

# SECTION 3: Truth Gate Blocking
test_case "Block browser" \
    "open firefox to google" \
    "BROWSER CONTROL NOT AVAILABLE"

test_case "Block shell" \
    "execute bash -lc echo test" \
    "SHELL EXECUTION DISABLED"

test_case "Block cloud" \
    "deploy to aws ec2" \
    "CLOUD INTEGRATIONS NOT AVAILABLE"

# SECTION 4: File Verification
test_case "File claim requires proof" \
    "list all onboarding documents in mindsong repo" \
    "list_files"  # Should force tool execution, not RAG

# SECTION 5: Capabilities
test_case "Capabilities query" \
    "what are your capabilities" \
    "llama3:8b"

test_case "Model info" \
    "what model are you using" \
    "llama3:8b"

# SECTION 6: Error Handling
test_case "Missing args" \
    '{"tool": "read_file", "args": {}}' \
    "ERROR"

test_case "Unknown tool" \
    '{"tool": "hack_the_planet", "args": {}}' \
    "ERROR"

test_case "Non-existent file" \
    '{"tool": "read_file", "args": {"file_path": "/tmp/nonexistent_12345.txt"}}' \
    "not found"

# SECTION 7: Git Operations
test_case "Git status" \
    '{"tool": "git_operations", "args": {"operation": "status", "repo_path": "~/.roxy"}}' \
    "."

# SUMMARY
echo "═══════════════════════════════════════════════════════════"
echo "                     RESULTS"
echo "═══════════════════════════════════════════════════════════"
echo "Passed: ✅ $PASS"
echo "Failed: ❌ $FAIL"
echo "Success Rate: $(( PASS * 100 / (PASS + FAIL) ))%"
echo "═══════════════════════════════════════════════════════════"

if [ $FAIL -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED - ROXY IS CLAUDIFIED!"
    exit 0
else
    echo "⚠️  FAILURES DETECTED - Review logs"
    exit 1
fi
```

**Exit Criteria:** 100% pass rate, zero timeouts, zero JSON errors, zero unverified files

---

## PHASE 6: PRODUCTION HARDENING (SAFETY - 45 MINUTES)

### 6.1 Implement Allowlists/Denylists
**File:** `~/.roxy/config.json`

```json
{
  "port": 8766,
  "repo_roots": [
    "/home/mark/mindsong-juke-hub",
    "/home/mark/jarvis-docs",
    "/home/mark/.roxy",
    "/home/mark/gym"
  ],
  "allowed_file_operations": [
    "/home/mark/mindsong-juke-hub",
    "/home/mark/jarvis-docs",
    "/home/mark/Documents",
    "/home/mark/.roxy"
  ],
  "security": {
    "execute_command": {
      "enabled": false,
      "allowlist": [
        "echo *",
        "ls *",
        "cat *",
        "git *"
      ],
      "denylist": [
        "rm -rf",
        "sudo *",
        "dd if=*",
        "mkfs.*",
        "> /dev/*"
      ]
    },
    "confirmation_required": [
      "git push",
      "git commit",
      "rm *",
      "mv *",
      "pip install *",
      "npm install *"
    ]
  }
}
```

### 6.2 Enforce Allowlists in execute_tool_direct
```python
def execute_tool_direct(tool_name, tool_args):
    """Execute tool with security checks"""
    
    # Load config
    config_path = ROXY_DIR / "config.json"
    config = json.load(open(config_path))
    
    if tool_name == "execute_command":
        cmd = tool_args.get("cmd")
        security = config.get("security", {}).get("execute_command", {})
        
        # Check enabled
        if not security.get("enabled", False):
            return "❌ execute_command DISABLED by security policy"
        
        # Check denylist
        for pattern in security.get("denylist", []):
            if fnmatch.fnmatch(cmd, pattern):
                return f"❌ BLOCKED by denylist: {pattern}"
        
        # Check allowlist
        allowlist = security.get("allowlist", [])
        if allowlist and not any(fnmatch.fnmatch(cmd, p) for p in allowlist):
            return f"❌ NOT in allowlist. Allowed patterns: {', '.join(allowlist)}"
        
        # Check confirmation
        if any(fnmatch.fnmatch(cmd, p) for p in config.get("security", {}).get("confirmation_required", [])):
            return f"⚠️ CONFIRMATION REQUIRED for: {cmd}\n\nAdd 'confirmed=true' to args to proceed"
    
    # ... rest of tool execution ...
```

### 6.3 Add Audit Logging
```python
def track_tool_execution(tool_name, args, result, ok=True, error=None):
    """Track and log tool execution"""
    global TOOLS_EXECUTED
    
    execution = {
        "timestamp": datetime.utcnow().isoformat(),
        "name": tool_name,
        "args": args,
        "result": str(result)[:500],
        "ok": ok,
        "error": error
    }
    
    TOOLS_EXECUTED.append(execution)
    
    # Append to audit log
    audit_log = ROXY_DIR / "audit.log"
    with open(audit_log, "a") as f:
        f.write(json.dumps(execution) + "\n")
```

**Exit Criteria:** All destructive commands require confirmation, audit log populated, denylist enforced

---

## EXECUTION CHECKLIST

### Pre-Flight Checks
- [ ] Backup current ROXY state: `tar -czf ~/roxy_backup_$(date +%Y%m%d).tar.gz ~/.roxy`
- [ ] Commit any changes: `cd ~/.roxy && git add -A && git commit -m "Pre-Claudify snapshot"`
- [ ] Stop all ROXY services: `systemctl --user stop roxy-core`

### Phase Execution Order (STRICT)
- [ ] **Phase 0:** Environment cleanup (BLOCKING)
  - [ ] 0.1 Collect diagnostic evidence
  - [ ] 0.2 Kill legacy processes
  - [ ] 0.3 Archive /opt/roxy
  - [ ] 0.4 Add systemd guard
  - [ ] 0.5 Verify single listener
  
- [ ] **Phase 1:** Fix request encoding
  - [ ] 1.1 Create test_helpers.sh
  - [ ] 1.2 Test with examples
  - [ ] 1.3 Verify zero JSON errors
  
- [ ] **Phase 2:** Structured responses
  - [ ] 2.1 Define CommandResponse dataclass
  - [ ] 2.2 Refactor execute_command()
  - [ ] 2.3 Update roxy_core.py parser
  - [ ] 2.4 Update main() output
  
- [ ] **Phase 3:** File verification
  - [ ] 3.1 Add file claim detection
  - [ ] 3.2 Add preflight verification
  - [ ] Test: Query "list files" forces tool_direct
  
- [ ] **Phase 4:** Add tools
  - [ ] 4.1 Add search_code
  - [ ] 4.2 Add git_operations
  - [ ] 4.3 Add obs_control
  - [ ] Test: All 6 tools working
  
- [ ] **Phase 5:** Stress test
  - [ ] 5.1 Run stress_test_v2.sh
  - [ ] Verify 100% pass rate
  
- [ ] **Phase 6:** Production hardening
  - [ ] 6.1 Add allowlists to config
  - [ ] 6.2 Enforce in tools
  - [ ] 6.3 Enable audit logging

### Post-Implementation Validation
- [ ] Single listener confirmed: `ss -lptn 'sport = :8766' | wc -l == 2`
- [ ] Zero legacy processes: `ps aux | grep roxy_interface | wc -l == 0`
- [ ] All tests pass: `bash ~/.roxy/stress_test_v2.sh`
- [ ] Zero JSON errors in logs: `journalctl --user -u roxy-core -n 100 | grep -c "JSON" == 0`
- [ ] Audit log populated: `wc -l ~/.roxy/audit.log > 0`

---

## SUCCESS CRITERIA (BINARY)

### Must All Be True
1. ✅ Only ONE process listening on port 8766
2. ✅ Zero "connection refused" errors
3. ✅ Zero "Expecting delimiter" JSON errors
4. ✅ 100% stress test pass rate (14/14 tests)
5. ✅ All tool calls return structured JSON
6. ✅ Zero unverified file claims in RAG responses
7. ✅ Evidence citations present for all tool executions
8. ✅ Denylist blocks dangerous commands
9. ✅ Audit log records all tool usage
10. ✅ /opt/roxy archived, no legacy processes

---

## ESTIMATED TIMELINE

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0 | 30 min | None (CRITICAL PATH) |
| Phase 1 | 45 min | Phase 0 complete |
| Phase 2 | 60 min | Phase 1 complete |
| Phase 3 | 45 min | Phase 2 complete |
| Phase 4 | 60 min | Phase 2 complete |
| Phase 5 | 30 min | Phases 2,3,4 complete |
| Phase 6 | 45 min | Phase 5 passed |
| **TOTAL** | **4-6 hours** | Sequential execution |

---

## ROLLBACK PLAN

If any phase fails:
```bash
# Stop service
systemctl --user stop roxy-core

# Restore backup
cd ~
tar -xzf roxy_backup_$(date +%Y%m%d).tar.gz

# Restart
systemctl --user start roxy-core
systemctl --user status roxy-core
```

---

## CHIEF'S EVIDENCE REQUIREMENTS

Before declaring success, provide:

1. **Single-listener proof:**
```bash
ss -lptn 'sport = :8766'
ps aux | egrep -i '(roxy|jarvis).*python'
```

2. **Clean request/response:**
```bash
source ~/.roxy/test_helpers.sh
roxy_request 'RUN_TOOL list_files {"path": "~/.roxy", "pattern": "*.py"}'
```

3. **Stress test results:**
```bash
bash ~/.roxy/stress_test_v2.sh
```

4. **Zero errors in logs:**
```bash
journalctl --user -u roxy-core -n 100 --no-pager | grep -E "(ERROR|WARNING)"
```

---

## NOTES

- **CRITICAL:** Phase 0 MUST complete before any other work
- Phases 2-4 can partially overlap if Phase 1 is stable
- Phase 5 is the ONLY true validation - don't skip it
- Phase 6 can be deferred if time-constrained, but recommended for production

**END OF PLAN**
