#!/usr/bin/env python3
"""
Langfuse Integration for ROXY Core
===================================
Full observability for ROXY AI operations:
- LLM request/response tracing
- Tool execution tracking
- Cost attribution
- Performance metrics

Replaces minimal observability with production-grade tracing.
"""

import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger("roxy.observability")

# Lazy import langfuse
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("Langfuse not installed. Observability disabled.")


@dataclass
class LLMCall:
    """Record of an LLM API call"""
    model: str
    provider: str
    prompt: str
    response: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecution:
    """Record of a tool execution"""
    tool_name: str
    server_name: str
    arguments: Dict[str, Any]
    result: Any
    latency_ms: float
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ROXYObservability:
    """
    Production observability for ROXY Core.
    
    Features:
    - Automatic LLM call tracing
    - Tool execution tracking
    - RAG retrieval metrics
    - Cost tracking
    - Performance dashboards
    """
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "http://localhost:3000",
        enabled: bool = True
    ):
        self.enabled = enabled and LANGFUSE_AVAILABLE
        self.host = host
        
        if not self.enabled:
            logger.info("Observability disabled (Langfuse unavailable or disabled)")
            self._langfuse = None
            return
        
        # Load from environment if not provided
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        
        if not self.public_key or not self.secret_key:
            logger.warning("Langfuse keys not configured. Observability disabled.")
            self.enabled = False
            self._langfuse = None
            return
        
        self._langfuse = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=host
        )
        
        logger.info(f"Langfuse observability enabled at {host}")
    
    @contextmanager
    def trace_llm_call(
        self,
        model: str,
        provider: str = "ollama",
        metadata: Optional[Dict] = None
    ) -> Generator[Dict, None, None]:
        """
        Context manager for tracing LLM calls.
        
        Usage:
            with observability.trace_llm_call("qwen2.5-coder:14b") as trace:
                response = await llm.generate(prompt)
                trace.record(response, tokens_in, tokens_out, latency_ms)
        """
        if not self.enabled or not self._langfuse:
            yield _NoOpTrace()
            return
        
        trace_id = f"llm_{datetime.utcnow().timestamp()}"
        start_time = datetime.utcnow()
        
        # Create Langfuse span
        span = self._langfuse.span(
            id=trace_id,
            name=f"llm_call_{model}",
            input={"model": model, "provider": provider},
            metadata=metadata or {}
        )
        
        trace_data = {
            "span": span,
            "model": model,
            "provider": provider,
            "start_time": start_time,
            "recorded": False
        }
        
        try:
            yield _LangfuseTrace(trace_data, self._langfuse)
        except Exception as e:
            span.update(
                level="ERROR",
                status_message=str(e),
                output={"error": str(e)}
            )
            raise
        finally:
            if not trace_data["recorded"]:
                span.update(
                    status_message="Call not recorded - possible early exit"
                )
    
    def trace_tool_execution(
        self,
        tool_name: str,
        server_name: str,
        arguments: Dict[str, Any],
        result: Any,
        latency_ms: float,
        error: Optional[str] = None
    ):
        """Record a tool execution"""
        if not self.enabled or not self._langfuse:
            return
        
        # Create event
        self._langfuse.event(
            name=f"tool_{tool_name}",
            input={
                "server": server_name,
                "arguments": arguments
            },
            output={
                "result": str(result)[:1000] if result else None,
                "error": error
            },
            metadata={
                "latency_ms": latency_ms,
                "tool_name": tool_name
            }
        )
    
    def trace_rag_query(
        self,
        query: str,
        num_chunks: int,
        query_time_ms: float,
        sources: List[str]
    ):
        """Record a RAG retrieval"""
        if not self.enabled or not self._langfuse:
            return
        
        self._langfuse.event(
            name="rag_retrieval",
            input={"query": query},
            output={
                "chunks_retrieved": num_chunks,
                "sources": sources
            },
            metadata={
                "query_time_ms": query_time_ms
            }
        )
    
    def record_generation(
        self,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        model_parameters: Optional[Dict] = None,
        usage: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Record a full generation (prompt + completion).
        
        This is the primary method for ROXY Core integration.
        """
        if not self.enabled or not self._langfuse:
            return
        
        try:
            self._langfuse.generation(
                name=name,
                model=model,
                input=prompt,
                output=completion,
                model_parameters=model_parameters or {},
                usage=usage or {},
                metadata=metadata or {}
            )
            logger.debug(f"Recorded generation: {name}")
        except Exception as e:
            logger.error(f"Failed to record generation: {e}")
    
    def flush(self):
        """Flush pending events to Langfuse"""
        if self.enabled and self._langfuse:
            self._langfuse.flush()
    
    def get_trace_url(self, trace_id: str) -> str:
        """Get URL to view trace in Langfuse UI"""
        return f"{self.host}/trace/{trace_id}"


class _NoOpTrace:
    """No-op trace for when observability is disabled"""
    
    def record(self, response: str, tokens_in: int, tokens_out: int, latency_ms: float):
        pass


class _LangfuseTrace:
    """Active trace wrapper for Langfuse span"""
    
    def __init__(self, trace_data: Dict, langfuse_client):
        self._data = trace_data
        self._client = langfuse_client
    
    def record(
        self,
        response: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        metadata: Optional[Dict] = None
    ):
        """Record the LLM response to Langfuse"""
        span = self._data["span"]
        
        # Calculate cost (approximate)
        cost = self._estimate_cost(
            self._data["model"],
            tokens_in,
            tokens_out
        )
        
        span.update(
            output={"response": response[:2000]},  # Truncate long responses
            usage={
                "input": tokens_in,
                "output": tokens_out,
                "total": tokens_in + tokens_out,
                "cost": cost
            },
            metadata={
                **(metadata or {}),
                "latency_ms": latency_ms,
                "model": self._data["model"],
                "provider": self._data["provider"]
            }
        )
        
        self._data["recorded"] = True
        
        # Also create a generation for dashboard visibility
        self._client.generation(
            name=f"gen_{self._data['model']}",
            model=self._data["model"],
            input=self._data.get("prompt", "")[:1000],
            output=response[:2000],
            usage={
                "input": tokens_in,
                "output": tokens_out,
                "total": tokens_in + tokens_out
            }
        )
    
    def _estimate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Rough cost estimation for local models"""
        # Local inference costs are electricity + amortized hardware
        # Rough estimate: $0.001 per 1K tokens for home GPU setup
        total_tokens = tokens_in + tokens_out
        return (total_tokens / 1000) * 0.001


# Global observability instance
_observability: Optional[ROXYObservability] = None


def get_observability() -> ROXYObservability:
    """Get or create global observability instance"""
    global _observability
    if _observability is None:
        _observability = ROXYObservability()
    return _observability


def init_observability(
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: str = "http://localhost:3000"
) -> ROXYObservability:
    """Initialize global observability with explicit config"""
    global _observability
    _observability = ROXYObservability(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    return _observability


# Decorator for automatic function tracing
def trace_function(name: Optional[str] = None):
    """Decorator to trace function execution"""
    def decorator(func):
        if not LANGFUSE_AVAILABLE:
            return func
        
        trace_name = name or func.__name__
        
        @observe(name=trace_name)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @observe(name=trace_name)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# CLI for setup verification
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test observability setup
        obs = init_observability()
        
        if not obs.enabled:
            print("\n❌ Observability not enabled")
            print("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
            sys.exit(1)
        
        # Record test generation
        obs.record_generation(
            name="test_generation",
            model="qwen2.5-coder:14b",
            prompt="Test prompt for observability",
            completion="Test completion from ROXY",
            usage={"input": 10, "output": 20, "total": 30}
        )
        obs.flush()
        
        print("\n✅ Observability test successful")
        print(f"View traces at: {obs.host}")
    else:
        print("Usage: langfuse_integration.py test")
