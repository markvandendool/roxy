#!/usr/bin/env python3
"""
SSE Streaming Module - Real-time token streaming for ROXY
Implements Server-Sent Events (SSE) for streaming LLM responses
"""
import json
import time
import logging
import requests
from typing import Iterator, Optional, Dict, Any

logger = logging.getLogger("roxy.streaming")

# Import metrics
try:
    from prometheus_metrics import record_ollama_call, record_rag_query
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Import retry and circuit breaker
try:
    from retry_utils import retry
    from circuit_breaker import get_circuit_breaker, CircuitBreakerError
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False
    logger.warning("Retry and circuit breaker not available")


class SSEStreamer:
    """Server-Sent Events streamer for LLM responses"""
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11435"):
        self.ollama_url = ollama_url
        self.heartbeat_interval = 8  # seconds (faster for proxy compatibility)
        # Initialize circuit breaker for Ollama
        if RESILIENCE_AVAILABLE:
            self.ollama_circuit = get_circuit_breaker(
                "ollama",
                failure_threshold=5,
                timeout=60.0
            )
        else:
            self.ollama_circuit = None
    
    def stream_ollama_response(self, 
                               model: str,
                               prompt: str,
                               context: Optional[str] = None,
                               temperature: float = 0.7,
                               num_predict: int = 300,
                               request_id: Optional[str] = None) -> Iterator[str]:
        """
        Stream tokens from Ollama API
        
        Yields:
            str: JSON-encoded SSE event data
        """
        full_prompt = prompt
        request_tag = request_id or "n/a"
        if context:
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:"
        
        start_time = time.time()
        
        try:
            # Call Ollama streaming API with retry and circuit breaker protection
            @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
            def _make_request():
                return requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": num_predict
                        }
                    },
                    stream=True,
                    timeout=120
                )
            
            # Use circuit breaker if available
            if self.ollama_circuit:
                try:
                    response = self.ollama_circuit.call(_make_request)
                except CircuitBreakerError as e:
                    error_msg = f"Ollama circuit breaker is OPEN: {e}"
                    logger.error(error_msg)
                    yield self._format_sse_event("error", {"message": error_msg})
                    return
            else:
                response = _make_request()
            
            if response.status_code == 404:
                downstream_url = f"{self.ollama_url}/api/generate"
                logger.error(
                    f"[OLLAMA] model_missing requestId={request_tag} status=404 model={model} url={downstream_url}"
                )
                for event in self._fallback_response(prompt, model, request_tag):
                    yield event
                return

            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code}"
                logger.error(f"{error_msg} requestId={request_tag}")
                # Mark as circuit breaker failure
                if self.ollama_circuit:
                    self.ollama_circuit._on_failure()
                yield self._format_sse_event("error", {"message": error_msg})
                return
            
            last_heartbeat = time.time()
            buffer = ""
            parse_errors = 0
            max_parse_errors = 10  # Allow some parse errors before giving up
            
            for line in response.iter_lines():
                # Check for client disconnect (simplified - in production use proper detection)
                try:
                    if not line:
                        # Send heartbeat on empty lines to keep connection alive
                        if time.time() - last_heartbeat > self.heartbeat_interval:
                            yield ":keepalive\n\n"
                            last_heartbeat = time.time()
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Check for completion
                        if data.get("done", False):
                            if buffer:
                                yield self._format_sse_event("token", {"token": buffer, "done": False})
                                buffer = ""
                            
                            # Record metrics
                            latency = time.time() - start_time
                            if METRICS_AVAILABLE:
                                record_ollama_call(model, latency)
                            
                            yield self._format_sse_event("complete", {"done": True})
                            break
                        
                        # Extract token
                        token = data.get("response", "")
                        if token:
                            buffer += token
                            # Yield token immediately for real-time feel
                            yield self._format_sse_event("token", {"token": token, "done": False})
                        
                        # Periodic heartbeat to prevent timeout
                        if time.time() - last_heartbeat > self.heartbeat_interval:
                            yield ":keepalive\n\n"
                            last_heartbeat = time.time()
                        
                        # Reset parse error counter on successful parse
                        parse_errors = 0
                            
                    except json.JSONDecodeError as e:
                        parse_errors += 1
                        logger.warning(
                            f"Failed to parse Ollama response line ({parse_errors}/{max_parse_errors}) requestId={request_tag}: {line[:100]}"
                        )
                        
                        # Mark as circuit breaker failure if too many parse errors
                        if parse_errors >= max_parse_errors and self.ollama_circuit:
                            self.ollama_circuit._on_failure()
                            yield self._format_sse_event("error", {"message": "Too many parse errors"})
                            break
                        continue
                    except Exception as e:
                        logger.error(f"Error processing stream requestId={request_tag}: {e}")
                        # Mark as circuit breaker failure
                        if self.ollama_circuit:
                            self.ollama_circuit._on_failure()
                        yield self._format_sse_event("error", {"message": str(e)})
                        break
                except Exception as e:
                    # Client disconnect or other error
                    logger.warning(f"Stream interrupted requestId={request_tag}: {e}")
                    break
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed requestId={request_tag}: {e}")
            yield self._format_sse_event("error", {"message": f"Connection error: {e}"})
        except Exception as e:
            logger.error(f"Streaming error requestId={request_tag}: {e}")
            yield self._format_sse_event("error", {"message": str(e)})

    def _fallback_response(self, prompt: str, model: str, request_tag: str) -> Iterator[str]:
        """Provide deterministic fallback output when Ollama is unavailable."""
        fallback_text = (
            f"⚠️ Ollama model '{model}' is not available. "
            "I'm returning a fallback response instead of live generation. "
            "Run 'ollama pull {model}' and ensure the service is running to restore streaming."
        )
        logger.warning(f"[OLLAMA] fallback response served model={model} requestId={request_tag}")
        yield self._format_sse_event(
            "token",
            {"token": fallback_text, "done": False, "fallback": True}
        )
        yield self._format_sse_event("complete", {"done": True, "fallback": True})
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def stream_rag_response(self,
                           query: str,
                           context: Optional[str] = None,
                           model: str = "llama3:8b",
                           temperature: float = 0.7,
                           request_id: Optional[str] = None) -> Iterator[str]:
        """
        Stream RAG response with context
        
        Args:
            query: User query
            context: RAG context chunks (optional)
            model: Ollama model name
            temperature: Generation temperature
            
        Yields:
            str: SSE event data
        """
        start_time = time.time()
        from datetime import datetime
        import socket
        import os

        # Context Pack - inject essential awareness
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hostname = socket.gethostname()
        repo_root = os.getenv("ROXY_DIR", os.path.expanduser("~/.roxy"))

        # ROXY System Prompt - her identity
        system_prompt = f"""You are ROXY, an advanced AI assistant created by Mark for MindSong operations.

IDENTITY:
- Warm, witty, and efficient like JARVIS
- Left-brain focused: operations, business, systems, coding
- Proactive and anticipatory
- Professional with occasional dry humor

CURRENT CONTEXT:
- Current time: {current_time}
- Host machine: {hostname}
- Repository root: {repo_root}

RESPONSE GUIDELINES:
- Be direct and helpful
- When you have context, synthesize it into a clear answer
- Cite sources when relevant
- Keep responses concise unless detail is requested"""

        # Build RAG prompt with identity + context
        # Put time at the end so model sees it last (recency bias)
        time_reminder = f"\n\n⏰ IMPORTANT: The current date/time is {current_time}. Any dates in reference material are historical."

        if context:
            prompt = f"""{system_prompt}

REFERENCE MATERIAL (historical context - use for background only):
{context}

USER QUERY: {query}
{time_reminder}

Answer the user's query. Synthesize reference material when relevant. For questions about current time/date, use the CURRENT CONTEXT from above, not reference material."""
        else:
            prompt = f"""{system_prompt}

USER QUERY: {query}
{time_reminder}

Provide a helpful response."""
        
        # Stream response
        for event in self.stream_ollama_response(
            model=model,
            prompt=prompt,
            context=None,  # Already included in prompt
            temperature=temperature,
            num_predict=500,
            request_id=request_id
        ):
            yield event
        
        # Record RAG query metrics
        latency = time.time() - start_time
        if METRICS_AVAILABLE:
            record_rag_query(latency)


# Global streamer instance
_streamer = None


def get_streamer() -> SSEStreamer:
    """Get or create global SSE streamer instance"""
    global _streamer
    if _streamer is None:
        _streamer = SSEStreamer()
    return _streamer

