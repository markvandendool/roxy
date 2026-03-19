#!/usr/bin/env python3
"""
Tool Executor Core - Async bash tool execution with streaming output
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-001)
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional, List

logger = logging.getLogger("roxy.tool_executor")

DEFAULT_TIMEOUT = 30.0
MAX_OUTPUT_SIZE = 1024 * 1024


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0
    tool_name: str = "bash"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


class ToolExecutor:
    """Async tool executor for bash commands with streaming output."""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT, workdir: Optional[str] = None):
        self.timeout = timeout
        self.default_workdir = workdir or os.getcwd()
        self.active_processes: Dict[int, asyncio.subprocess.Process] = {}
    
    async def execute_bash(
        self,
        command: str,
        timeout: Optional[float] = None,
        workdir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        stream_callback=None
    ) -> ToolResult:
        """
        Execute a bash command asynchronously with optional streaming.
        
        Args:
            command: Shell command to execute
            timeout: Override default timeout (seconds)
            workdir: Working directory for command
            env: Environment variables
            stream_callback: Optional async callback for streaming output
            
        Returns:
            ToolResult with success, output, error, exit_code
        """
        start_time = time.time()
        effective_timeout = timeout or self.timeout
        effective_workdir = workdir or self.default_workdir
        
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        
        logger.info(f"Executing: {command[:100]}...")
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=effective_workdir,
                env=merged_env,
                preexec_fn=os.setsid
            )
            
            self.active_processes[process.pid] = process
            
            output_chunks = []
            error_chunks = []
            
            async def read_stream(stream: asyncio.StreamReader, is_error: bool) -> None:
                try:
                    while True:
                        chunk = await stream.read(4096)
                        if not chunk:
                            break
                        
                        decoded = chunk.decode('utf-8', errors='replace')
                        
                        if stream_callback and callable(stream_callback):
                            await stream_callback(decoded, is_error=is_error)
                        
                        if is_error:
                            error_chunks.append(decoded)
                        else:
                            output_chunks.append(decoded)
                            
                except Exception as e:
                    logger.error(f"Stream read error: {e}")
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, False),
                        read_stream(process.stderr, True)
                    ),
                    timeout=effective_timeout
                )
                
                exit_code = await process.wait()
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {effective_timeout}s: {command[:50]}...")
                
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    await process.wait()
                
                return ToolResult(
                    success=False,
                    error="Command timed out",
                    exit_code=-1,
                    duration=time.time() - start_time,
                    metadata={"timeout": effective_timeout, "command": command[:100]}
                )
            
            finally:
                self.active_processes.pop(process.pid, None)
            
            output = "".join(output_chunks)
            error = "".join(error_chunks)
            duration = time.time() - start_time
            
            if len(output) > MAX_OUTPUT_SIZE:
                output = output[:MAX_OUTPUT_SIZE] + f"\n... [truncated, {len(output)} bytes total]"
            
            return ToolResult(
                success=exit_code == 0,
                output=output,
                error=error,
                exit_code=exit_code,
                duration=duration,
                metadata={"command": command[:100], "workdir": effective_workdir}
            )
            
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Command not found: {command.split()[0]}",
                exit_code=127,
                duration=time.time() - start_time
            )
        except PermissionError:
            return ToolResult(
                success=False,
                error=f"Permission denied: {command.split()[0]}",
                exit_code=126,
                duration=time.time() - start_time
            )
        except Exception as e:
            logger.error(f"Bash execution error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                exit_code=-1,
                duration=time.time() - start_time
            )
    
    async def execute_streaming(
        self,
        command: str,
        timeout: Optional[float] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a command with streaming output as SSE-like events.
        
        Yields:
            Dict events with 'type' and 'data' keys
        """
        start_time = time.time()
        
        yield {"type": "start", "data": {"command": command, "timestamp": start_time}}
        
        async def stream_callback(chunk: str, is_error: bool):
            yield {"type": "error" if is_error else "output", "data": chunk}
        
        result = await self.execute_bash(
            command,
            timeout=timeout,
            stream_callback=stream_callback
        )
        
        yield {"type": "complete", "data": {
            "success": result.success,
            "exit_code": result.exit_code,
            "duration": result.duration,
            "output_size": len(result.output),
            "error_size": len(result.error)
        }}
    
    async def kill_process(self, pid: int) -> bool:
        """Kill an active process by PID."""
        if pid in self.active_processes:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                await asyncio.wait_for(self.active_processes[pid].wait(), timeout=5.0)
                self.active_processes.pop(pid, None)
                return True
            except Exception as e:
                logger.error(f"Failed to kill process {pid}: {e}")
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    self.active_processes.pop(pid, None)
                    return True
                except:
                    return False
        return False
    
    async def kill_all(self) -> int:
        """Kill all active processes. Returns count killed."""
        killed = 0
        for pid in list(self.active_processes.keys()):
            if await self.kill_process(pid):
                killed += 1
        return killed
    
    def parse_tool_call(self, text: str) -> Optional[ToolCall]:
        """
        Parse a tool call from text (e.g., from model output).
        
        Supports formats:
        - <<tool_call>>
          name: "bash"
          arguments:
            command: "ls -la"
        - <<bash>>ls -la<</bash>>
        """
        text = text.strip()
        
        if text.startswith("<<tool_call>>"):
            try:
                data = json.loads(text[len("<<tool_call>>"):].strip())
                return ToolCall(
                    name=data.get("name", "bash"),
                    arguments=data.get("arguments", {}),
                    call_id=data.get("call_id")
                )
            except json.JSONDecodeError:
                pass
        
        tool_patterns = ["<<bash>>", "<<read>>", "<<write>>", "<<edit>>", "<<glob>>", "<<grep>>"]
        for pattern in tool_patterns:
            if text.startswith(pattern):
                tool_name = pattern[2:-2]
                content = text[len(pattern):]
                if f"<</{tool_name}>>" in content:
                    content = content.split(f"<</{tool_name}>>")[0]
                return ToolCall(name=tool_name, arguments={"content": content})
        
        return None
    
    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """Execute a parsed ToolCall."""
        if tool_call.name == "bash":
            command = tool_call.arguments.get("command", "")
            return await self.execute_bash(
                command,
                timeout=tool_call.arguments.get("timeout"),
                workdir=tool_call.arguments.get("workdir")
            )
        else:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_call.name}",
                metadata={"available_tools": ["bash"]}
            )


async def test_basic_execution():
    """Test basic bash execution."""
    executor = ToolExecutor(timeout=10.0)
    
    print("Test 1: Simple echo")
    result = await executor.execute_bash("echo 'Hello, World!'")
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output.strip()}")
    print(f"  Duration: {result.duration:.3f}s")
    
    print("\nTest 2: Command with error")
    result = await executor.execute_bash("ls /nonexistent_directory")
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error.strip()}")
    
    print("\nTest 3: Timeout test")
    result = await executor.execute_bash("sleep 5", timeout=1.0)
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")
    
    print("\nTest 4: Streaming test")
    result = await executor.execute_bash("for i in 1 2 3; do echo $i; sleep 0.1; done")
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output.strip()}")


if __name__ == "__main__":
    asyncio.run(test_basic_execution())
