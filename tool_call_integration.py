#!/usr/bin/env python3
"""
Tool Call Integration - Detects and executes tool calls in streaming output
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-003)
"""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, Optional, List, Callable, Awaitable

logger = logging.getLogger("roxy.tool_call")

TOOL_PATTERNS = {
    "json_tool": r'<<tool_call>>([\s\S]*?)<</tool_call>>',
    "fenced_bash": r'<<bash>>([\s\S]*?)<</bash>>',
    "fenced_read": r'<<read>>([\s\S]*?)<</read>>',
    "fenced_write": r'<<write>>([\s\S]*?)<</write>>',
    "fenced_edit": r'<<edit>>([\s\S]*?)<</edit>>',
    "fenced_glob": r'<<glob>>([\s\S]*?)<</glob>>',
    "fenced_grep": r'<<grep>>([\s\S]*?)<</grep>>',
}


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None
    source: str = "model"
    safety_level: str = "safe"


@dataclass
class ToolEvent:
    event_type: str
    data: Dict[str, Any]
    call_id: Optional[str] = None
    tool_name: Optional[str] = None


PolicyCheck = Callable[[ToolCall], Awaitable[bool]]
PolicyReason = Callable[[ToolCall], Awaitable[str]]


class GovernanceHooks:
    """Pre/Post tool execution hooks for safety and audit."""
    
    def __init__(self):
        self.pre_tool_checks: List[PolicyCheck] = []
        self.pre_tool_reasons: List[PolicyReason] = []
        self.post_tool_logs: List[Callable] = []
        
        self.dangerous_tools = {"bash", "shell", "exec", "delete", "remove"}
        self.dangerous_patterns = [
            r'rm\s+-rf\s+/\s', r'dd\s+if=.*of=/dev/', r'mkfs\.',
            r'drop\s+(table|database)', r'truncate\s+--no-preserve-root',
            r'shutdown|reboot|halt|poweroff', r':\(\){.*}',
        ]
    
    def add_pre_check(self, check: PolicyCheck, reason: Optional[PolicyReason] = None):
        self.pre_tool_checks.append(check)
        if reason:
            self.pre_tool_reasons.append(reason)
    
    def add_post_logger(self, logger_fn: Callable):
        self.post_tool_logs.append(logger_fn)
    
    async def check_pre(self, tool_call: ToolCall) -> tuple[bool, str]:
        """Run pre-tool checks. Returns (allowed, reason)."""
        for check in self.pre_tool_checks:
            try:
                if not await check(tool_call):
                    reason = "Pre-check denied"
                    for reason_fn in self.post_tool_reasons:
                        try:
                            reason = await reason_fn(tool_call)
                        except:
                            pass
                    logger.warning(f"Tool {tool_call.name} denied by policy: {reason}")
                    return False, reason
            except Exception as e:
                logger.error(f"Pre-check error: {e}")
        
        if tool_call.name.lower() in self.dangerous_tools:
            return False, f"Tool '{tool_call.name}' is in dangerous tools list"
        
        for pattern in self.dangerous_patterns:
            args_str = json.dumps(tool_call.arguments)
            if re.search(pattern, args_str, re.IGNORECASE):
                return False, f"Argument matches dangerous pattern: {pattern}"
        
        return True, "allowed"
    
    async def run_post(self, tool_call: ToolCall, result: Dict[str, Any]):
        """Run post-tool logging."""
        log_entry = {
            "timestamp": time.time(),
            "tool": tool_call.name,
            "args_hash": hash(json.dumps(tool_call.arguments, sort_keys=True)),
            "duration": result.get("duration", 0),
            "success": result.get("success", False),
            "exit_code": result.get("exit_code", -1),
            "output_size": len(result.get("output", "")),
            "error_size": len(result.get("error", "")),
        }
        
        for logger_fn in self.post_tool_logs:
            try:
                logger_fn(log_entry)
            except Exception as e:
                logger.error(f"Post-log error: {e}")


class ToolCallDetector:
    """Detects structured tool calls from model output."""
    
    def __init__(self):
        self.patterns = {k: re.compile(v) for k, v in TOOL_PATTERNS.items()}
    
    def detect(self, text: str) -> List[ToolCall]:
        """Detect tool calls in text. Returns list of found calls."""
        calls = []
        
        for pattern_name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                if pattern_name == "json_tool":
                    try:
                        data = json.loads(match.group(1).strip())
                        calls.append(ToolCall(
                            name=data.get("name", "bash"),
                            arguments=data.get("arguments", {}),
                            call_id=data.get("call_id"),
                            source="model",
                            safety_level=self._assess_safety(data.get("name", "bash"))
                        ))
                    except json.JSONDecodeError:
                        pass
                else:
                    tool_name = pattern_name.replace("fenced_", "")
                    content = match.group(1).strip()
                    
                    if pattern_name == "fenced_bash":
                        calls.append(ToolCall(
                            name="bash",
                            arguments={"command": content},
                            source="model",
                            safety_level="guarded"
                        ))
                    elif pattern_name == "fenced_read":
                        calls.append(ToolCall(
                            name="read",
                            arguments={"file_path": content},
                            source="model",
                            safety_level="safe"
                        ))
                    elif pattern_name == "fenced_write":
                        parts = content.split("\n", 1)
                        calls.append(ToolCall(
                            name="write",
                            arguments={
                                "file_path": parts[0] if parts else "",
                                "content": parts[1] if len(parts) > 1 else ""
                            },
                            source="model",
                            safety_level="guarded"
                        ))
                    elif pattern_name == "fenced_edit":
                        parts = content.split("\n---\n", 2)
                        calls.append(ToolCall(
                            name="edit",
                            arguments={
                                "file_path": parts[0] if parts else "",
                                "old_string": parts[1] if len(parts) > 1 else "",
                                "new_string": parts[2] if len(parts) > 2 else ""
                            },
                            source="model",
                            safety_level="dangerous"
                        ))
                    elif pattern_name == "fenced_glob":
                        calls.append(ToolCall(
                            name="glob",
                            arguments={"pattern": content},
                            source="model",
                            safety_level="safe"
                        ))
                    elif pattern_name == "fenced_grep":
                        parts = content.split("\n", 1)
                        calls.append(ToolCall(
                            name="grep",
                            arguments={
                                "pattern": parts[0] if parts else "",
                                "path": parts[1] if len(parts) > 1 else None
                            },
                            source="model",
                            safety_level="safe"
                        ))
        
        return calls
    
    def _assess_safety(self, tool_name: str) -> str:
        """Assess safety level of a tool."""
        tool_lower = tool_name.lower()
        if tool_lower in {"bash", "shell", "exec"}:
            return "dangerous"
        elif tool_lower in {"read", "glob", "grep"}:
            return "safe"
        elif tool_lower in {"write", "edit", "delete", "remove"}:
            return "guarded"
        return "unknown"


class ToolCallExecutor:
    """Executes detected tool calls through the tool executor."""
    
    def __init__(self):
        self._tool_executor = None
        self._streaming_tools = None
        self._governance = GovernanceHooks()
    
    async def _get_tool_executor(self):
        if self._tool_executor is None:
            from tool_executor import ToolExecutor
            self._tool_executor = ToolExecutor()
        return self._tool_executor
    
    async def _get_streaming_tools(self):
        if self._streaming_tools is None:
            from tools.streaming_tools import StreamingTools
            self._streaming_tools = StreamingTools()
        return self._streaming_tools
    
    async def execute(self, tool_call: ToolCall) -> Dict[str, Any]:
        """Execute a tool call and return structured result."""
        allowed, reason = await self._governance.check_pre(tool_call)
        
        if not allowed:
            return {
                "success": False,
                "error": f"Policy denied: {reason}",
                "tool": tool_call.name,
                "call_id": tool_call.call_id,
                "policy_denied": True,
                "reason": reason
            }
        
        start_time = time.time()
        result = {"tool": tool_call.name, "call_id": tool_call.call_id}
        
        try:
            if tool_call.name == "bash":
                executor = await self._get_tool_executor()
                exec_result = await executor.execute_bash(
                    tool_call.arguments.get("command", ""),
                    timeout=tool_call.arguments.get("timeout")
                )
                result.update({
                    "success": exec_result.success,
                    "output": exec_result.output,
                    "error": exec_result.error,
                    "exit_code": exec_result.exit_code,
                    "duration": exec_result.duration
                })
            
            elif tool_call.name in {"read", "write", "edit", "glob", "grep"}:
                tools = await self._get_streaming_tools()
                tool_result = await tools.execute_tool(tool_call.name, tool_call.arguments)
                result.update({
                    "success": tool_result.success,
                    "output": str(tool_result.data) if tool_result.data else "",
                    "error": tool_result.error,
                    "duration": time.time() - start_time,
                    "metadata": tool_result.metadata
                })
            
            else:
                result.update({
                    "success": False,
                    "error": f"Unknown tool: {tool_call.name}",
                    "duration": time.time() - start_time
                })
        
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            result.update({
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            })
        
        await self._governance.run_post(tool_call, result)
        return result
    
    def set_governance(self, governance: GovernanceHooks):
        self._governance = governance


class StreamingToolIntegration:
    """
    Integrates tool call detection and execution into streaming pipeline.
    Streams tool events as SSE alongside text tokens.
    """
    
    def __init__(
        self,
        max_tool_calls: int = 10,
        max_tool_runtime: float = 60.0
    ):
        self.detector = ToolCallDetector()
        self.executor = ToolCallExecutor()
        self.max_tool_calls = max_tool_calls
        self.max_tool_runtime = max_tool_runtime
        self.total_tool_runtime = 0.0
    
    async def process_stream(
        self,
        text_buffer: str,
        tool_callback: Optional[Callable[[ToolEvent], Awaitable]] = None
    ) -> AsyncIterator[ToolEvent]:
        """
        Process text buffer for tool calls and execute them.
        
        Args:
            text_buffer: Accumulated text from model output
            tool_callback: Optional async callback for each tool event
            
        Yields:
            ToolEvent for each stage of tool execution
        """
        self.total_tool_runtime = 0.0
        calls = self.detector.detect(text_buffer)
        
        if not calls:
            return
        
        calls_to_execute = calls[:self.max_tool_calls]
        
        for call in calls_to_execute:
            if self.total_tool_runtime >= self.max_tool_runtime:
                yield ToolEvent(
                    event_type="tool_execution_failed",
                    data={
                        "error": "Max total tool runtime exceeded",
                        "calls_executed": len(calls_to_execute),
                        "total_runtime": self.total_tool_runtime
                    },
                    call_id=call.call_id,
                    tool_name=call.name
                )
                break
            
            yield ToolEvent(
                event_type="tool_call_detected",
                data={
                    "tool": call.name,
                    "args": call.arguments,
                    "call_id": call.call_id,
                    "safety_level": call.safety_level
                },
                call_id=call.call_id,
                tool_name=call.name
            )
            
            if tool_callback:
                await tool_callback(ToolEvent(
                    event_type="tool_execution_started",
                    data={"started_at": time.time()},
                    call_id=call.call_id,
                    tool_name=call.name
                ))
            
            start_time = time.time()
            result = await self.executor.execute(call)
            duration = time.time() - start_time
            
            self.total_tool_runtime += duration
            result["duration"] = duration
            
            if result.get("policy_denied"):
                yield ToolEvent(
                    event_type="tool_execution_failed",
                    data=result,
                    call_id=call.call_id,
                    tool_name=call.name
                )
            elif result.get("success"):
                output_preview = result.get("output", "")[:500]
                yield ToolEvent(
                    event_type="tool_execution_finished",
                    data={
                        "success": True,
                        "output_preview": output_preview,
                        "output_size": len(result.get("output", "")),
                        "duration": duration,
                        "call_id": call.call_id
                    },
                    call_id=call.call_id,
                    tool_name=call.name
                )
            else:
                yield ToolEvent(
                    event_type="tool_execution_failed",
                    data={
                        "error": result.get("error", "Unknown error"),
                        "exit_code": result.get("exit_code", -1),
                        "duration": duration
                    },
                    call_id=call.call_id,
                    tool_name=call.name
                )
    
    def format_tool_event(self, event: ToolEvent) -> str:
        """Format a ToolEvent as SSE."""
        return f"event: {event.event_type}\ndata: {json.dumps(event.data)}\n\n"


async def test_tool_call_integration():
    """Test tool call detection and execution."""
    integration = StreamingToolIntegration()
    
    test_cases = [
        "<<bash>>echo 'Hello from tool call'<<  /bash>>",
        '<<tool_call>>{"name": "bash", "arguments": {"command": "pwd"}}',
        "<<read>>/tmp/test.txt<</read>>",
        "Here is some text <<bash>>ls -la<</bash>> and more text",
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest {i+1}: {test[:50]}...")
        calls = integration.detector.detect(test)
        print(f"  Detected: {len(calls)} tool call(s)")
        for call in calls:
            print(f"    - {call.name}: {call.arguments}")
    
    print("\n\nExecution test:")
    call = ToolCall(name="bash", arguments={"command": "echo 'Executed!'"})
    result = await integration.executor.execute(call)
    print(f"  Success: {result.get('success')}")
    print(f"  Output: {result.get('output', '').strip()}")


if __name__ == "__main__":
    asyncio.run(test_tool_call_integration())
