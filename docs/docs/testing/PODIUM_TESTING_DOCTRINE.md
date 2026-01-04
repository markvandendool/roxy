# Podium Testing Doctrine

## Critical Testing Protocol (Established Dec 2024)

### 🔴 MANDATORY: Server Restart Verification

**ALWAYS verify server restart BEFORE testing UI features.**

#### The Problem (Root Cause)

During Phase 5 Podium debugging (Dec 16-17, 2024), extensive debugging was performed under the false assumption that browser WebSocket messages were not reaching the server. This led to:
- Multiple incorrect hypotheses about message format, CORS, Bun API contracts
- Hours of instrumentation and forensic analysis
- False conclusions about "fake" components

**Reality:** The Podium server was running **stale code** from before instrumentation was added. The system was fully functional all along.

#### The Solution

**Before ANY Podium/WebSocket testing:**

```bash
# 1. Verify current server PID and start time
ps aux | grep "podium/standalone" | grep -v grep

# 2. Kill ALL instances forcefully
pkill -9 -f "podium/standalone"

# 3. Wait for clean termination
sleep 2

# 4. Start fresh server
cd luno-orchestrator && bun src/podium/standalone.ts 2>&1 &

# 5. VERIFY new PID
sleep 3 && ps aux | grep "podium/standalone" | grep -v grep

# 6. Check terminal output timestamp
# Ensure server logs show CURRENT timestamp, not old boot time
```

### 🔬 Runtime Evidence Requirements

**NEVER claim a feature is broken based on:**
- ❌ Absence of terminal logs (may be old process)
- ❌ UI behavior alone (may be caching)
- ❌ "No response" (timeout may be test harness issue)

**ALWAYS require:**
- ✅ Confirmed server PID matches current process
- ✅ Terminal logs show CURRENT timestamp
- ✅ Browser console shows connection to current WebSocket
- ✅ Runtime instrumentation (if debugging)

### 📊 Proven Performance Metrics

**Podium WebSocket Round-Trip (Measured Dec 17, 2024):**
```
Browser → Server:  10ms latency
Server processing: 522ms (orchestrator spawn)
Server → Browser:  2ms latency
Total round-trip:  ~534ms ✅
```

**Expected behavior:**
- WebSocket connections: <50ms
- Simple commands (PING): <100ms
- Complex commands (START_ORCHESTRATOR): 500-1000ms (process spawn)
- Message batching: Normal for TCP (bufferedAmount > 0 after send is OK)

### 🧪 Testing Best Practices

#### Browser Testing
1. **Hard refresh** (`Cmd+Shift+R`) after code changes
2. Clear browser cache if behavior seems stale
3. Check DevTools Network tab for WebSocket connection status
4. Verify WebSocket URL matches running server port

#### Server Testing
1. **Always check PID** before claiming "server not receiving"
2. **Check terminal timestamp** - old logs = old server
3. **Use process tree** to verify no zombie processes
4. **Test CLI WebSocket first** to isolate browser vs server issues

#### Debugging Instrumentation
1. Use **file-based logging** (`fs.appendFileSync`) for server-side
2. Use **HTTP ingest** (`fetch`) for browser-side
3. **Always clear log file** before each test run
4. **Verify instrumentation is active** - if no logs after action, code didn't reload

### 🚫 Anti-Patterns (DO NOT DO THIS)

#### ❌ Testing Without Verification
```bash
# BAD: Assume server restarted
bun src/podium/standalone.ts &
# ... immediately test UI ...
```

```bash
# GOOD: Verify restart
pkill -9 -f "podium/standalone"
sleep 2
bun src/podium/standalone.ts &
sleep 3
ps aux | grep "podium/standalone" | grep -v grep  # Verify new PID
```

#### ❌ Trusting Stale Terminal Output
```bash
# BAD: Looking at old terminal logs from previous server instance
# Check terminal 75.txt from 30 minutes ago: "no messages"
```

```bash
# GOOD: Check CURRENT terminal file and timestamp
tail -20 terminals/78.txt  # Most recent terminal
# Verify timestamp matches current time
```

#### ❌ Multiple Debugging Layers Simultaneously
```bash
# BAD: Change server code, browser code, and env vars all at once
```

```bash
# GOOD: Change one layer, verify, then proceed
# 1. Server instrumentation only
# 2. Test and verify logs
# 3. Add browser instrumentation
# 4. Test and verify logs
```

### 📚 Reference: Forensic Case Study

**Date:** Dec 16-17, 2024  
**Issue:** "Browser WebSocket messages not reaching server"  
**Diagnosis:** 5+ hours, 8 instrumentation points, 5 hypotheses tested  
**Root Cause:** Server process not restarted, running stale code  
**Evidence:** Runtime logs showed system working perfectly once server restarted  
**Lesson:** ALWAYS verify server restart before debugging

**Forensic Evidence (Actual Timings):**
```json
{"location":"useOrchestratorCommands.ts:224","timestamp":1765943843055,"message":"Browser pre-send"}
{"location":"websocket-server.ts:198","timestamp":1765943843065,"message":"handleCommand ENTRY"}
{"location":"websocket-server.ts:425","timestamp":1765943843587","message":"Sending COMMAND_RESULT"}
{"location":"useOrchestratorCommands.ts:68","timestamp":1765943843589","message":"Browser received"}
```
**Result:** 534ms end-to-end, fully functional.

### 🎯 Success Criteria

**System is WORKING if:**
- ✅ WebSocket connects within 100ms
- ✅ PING command returns PONG within 100ms
- ✅ START_ORCHESTRATOR returns result within 2 seconds
- ✅ ENQUEUE_STORY creates queue file within 500ms
- ✅ Browser receives COMMAND_RESULT for every command

**System is BROKEN if:**
- ❌ WebSocket never connects (after 5 seconds)
- ❌ Commands timeout (after 30 seconds) consistently
- ❌ Server logs show errors/exceptions
- ❌ Browser console shows WebSocket errors

**System is UNTESTED if:**
- ⚠️ Server PID not verified
- ⚠️ Terminal timestamp is old
- ⚠️ No runtime logs captured
- ⚠️ Browser cache not cleared

### 🔧 Quick Diagnostic Commands

```bash
# Check if Podium is running
ps aux | grep "podium/standalone" | grep -v grep

# Kill all Podium instances
pkill -9 -f "podium/standalone"

# Start Podium in foreground (for debugging)
cd luno-orchestrator && bun src/podium/standalone.ts

# Start Podium in background (for normal use)
cd luno-orchestrator && bun src/podium/standalone.ts 2>&1 &

# Test WebSocket via CLI (bypasses browser)
node -e "const ws=require('ws').WebSocket; const c=new ws('ws://localhost:3847/ws'); c.on('open',()=>{console.log('OK');c.close()});"

# Check Podium port
lsof -i :3847

# View real-time server logs
tail -f ~/.cursor/projects/*/terminals/*.txt | grep -i "podium\|websocket"
```

---

## Summary

**Golden Rule:** Trust nothing until the server PID is verified.

**Testing Protocol:**
1. Kill old server
2. Wait 2 seconds
3. Start new server
4. Verify PID
5. Test feature
6. Capture evidence

**Evidence Standard:** Runtime logs > Terminal output > UI behavior > Assumptions

This doctrine prevents hours of debugging phantom issues caused by stale processes.

