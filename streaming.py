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

# Import TruthPacket for reality grounding
try:
    from truth_packet import generate_truth_packet, format_truth_for_prompt, get_system_prompt_header
    TRUTH_PACKET_AVAILABLE = True
except ImportError:
    TRUTH_PACKET_AVAILABLE = False
    logger.warning("TruthPacket module not available - time grounding disabled")


# Time/date query patterns that should SKIP RAG (Directive #3)
import re

TIME_DATE_PATTERNS = [
    # Direct time questions
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:time|date|day|month|year)\b",
    r"\bwhat\s+time\s+is\s+it\b",
    r"\bwhat\s+day\s+(?:is\s+)?(?:it|today)\b",
    r"\bwhat(?:'s|\s+is)\s+today(?:'s)?\s+date\b",
    r"\btoday(?:'s)?\s+date\b",
    r"\bcurrent\s+(?:time|date|day|timestamp)\b",
    # Time-relative questions
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:weekday|week\s+day)\b",
    r"\bis\s+it\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bwhat\s+(?:month|year)\s+(?:is\s+)?(?:it|this)\b",
    # Time now patterns
    r"\bright\s+now\b.*\b(?:time|date)\b",
    r"\b(?:time|date)\b.*\bright\s+now\b",
    # Tell me the time
    r"\btell\s+me\s+(?:the\s+)?(?:current\s+)?(?:time|date)\b",
]

_TIME_DATE_REGEX = re.compile("|".join(TIME_DATE_PATTERNS), re.IGNORECASE)


def is_time_date_query(query: str) -> bool:
    """
    Detect if query is asking about current time/date.

    These queries should SKIP RAG entirely (Directive #3) because:
    1. RAG context may contain historical dates that confuse the model
    2. Time/date answers come solely from TruthPacket
    3. No indexed content is relevant for "what time is it"

    Returns:
        True if query is about time/date and should skip RAG
    """
    return bool(_TIME_DATE_REGEX.search(query))


# Repo/git query patterns that should use TruthPacket + git (Directive #5)
REPO_PATTERNS = [
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:branch|commit|sha|head)\b",
    r"\bwhich\s+branch\b",
    r"\bgit\s+(?:status|branch|log|diff)\b",
    r"\bare\s+(?:there\s+)?(?:any\s+)?(?:uncommitted|unstaged|modified)\s+(?:changes|files)\b",
    r"\bwhat\s+(?:was\s+)?(?:the\s+)?last\s+commit\b",
    r"\bis\s+(?:the\s+)?(?:repo|repository)\s+(?:clean|dirty)\b",
    r"\bwhat\s+(?:commit|sha)\s+(?:are\s+)?(?:we\s+)?on\b",
]

_REPO_REGEX = re.compile("|".join(REPO_PATTERNS), re.IGNORECASE)


def is_repo_query(query: str) -> bool:
    """
    Detect if query is asking about repository state (Directive #5).

    These queries should use TruthPacket.git and/or direct git commands.

    Returns:
        True if query is about repo/git state
    """
    return bool(_REPO_REGEX.search(query))


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
                               request_id: Optional[str] = None,
                               base_url: Optional[str] = None) -> Iterator[str]:
        """
        Stream tokens from Ollama API

        Args:
            base_url: Optional override for Ollama endpoint (from router)

        Yields:
            str: JSON-encoded SSE event data
        """
        full_prompt = prompt
        request_tag = request_id or "n/a"
        if context:
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}\n\nAnswer:"

        # Use provided base_url or fall back to instance default
        effective_url = base_url or self.ollama_url

        start_time = time.time()

        try:
            # Call Ollama streaming API with retry and circuit breaker protection
            @retry(max_attempts=3, delay=1.0, backoff=2.0) if RESILIENCE_AVAILABLE else lambda f: f
            def _make_request():
                return requests.post(
                    f"{effective_url}/api/generate",
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
                           request_id: Optional[str] = None,
                           base_url: Optional[str] = None) -> Iterator[str]:
        """
        Stream RAG response with context.

        PROMPT LAYOUT (Chief's Directive #2):
        A) SYSTEM: identity + hard rules
        B) TRUTH PACKET (authoritative - overrides all other sources)
        C) USER QUERY
        D) OPTIONAL REFERENCE MATERIAL (RAG) marked as historical/may be stale

        Args:
            query: User query
            context: RAG context chunks (optional)
            model: Ollama model name
            temperature: Generation temperature
            base_url: Optional Ollama endpoint from router (Directive #8)

        Yields:
            str: SSE event data
        """
        start_time = time.time()
        request_tag = request_id or "n/a"

        # === PART A: SYSTEM PROMPT (identity + hard rules) ===
        # Load from ROXY_IDENTITY.md via get_system_prompt_header() (Directive #6-7)
        if TRUTH_PACKET_AVAILABLE:
            system_prompt = get_system_prompt_header()
        else:
            # Fallback hardcoded identity
            system_prompt = """You are ROXY, an advanced AI assistant created by Mark for MindSong operations.

IDENTITY:
- Warm, witty, and efficient like JARVIS
- Left-brain focused: operations, business, systems, coding
- Proactive and anticipatory
- Professional with occasional dry humor

HARD RULES:
1. The TRUTH PACKET below contains REAL data from system calls - it is AUTHORITATIVE
2. If ANY reference material conflicts with the TRUTH PACKET, the TRUTH PACKET wins
3. For time/date questions, ONLY use the TRUTH PACKET timestamps
4. Reference material may contain historical dates - these are NOT the current date

RESPONSE GUIDELINES:
- Be direct and helpful
- When you have context, synthesize it into a clear answer
- Cite sources when relevant
- Keep responses concise unless detail is requested"""

        # === PART B: TRUTH PACKET (authoritative reality) ===
        if TRUTH_PACKET_AVAILABLE:
            truth_packet = generate_truth_packet(include_pools=False, include_git=True)
            truth_section = format_truth_for_prompt(truth_packet)
        else:
            # Fallback if truth_packet module not available
            from datetime import datetime
            import socket
            import os
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hostname = socket.gethostname()
            repo_root = os.getenv("ROXY_DIR", os.path.expanduser("~/.roxy"))
            truth_section = f"""=== TRUTH PACKET (AUTHORITATIVE - OVERRIDES ALL OTHER SOURCES) ===
Current Date/Time: {current_time}
Host: {hostname}
ROXY Directory: {repo_root}
=== END TRUTH PACKET ==="""

        # === PART C: USER QUERY ===
        query_section = f"""
=== USER QUERY ===
{query}
=== END USER QUERY ==="""

        # === PART D: REFERENCE MATERIAL (optional, marked as historical) ===
        if context:
            rag_section = f"""
=== REFERENCE MATERIAL (HISTORICAL - MAY BE STALE) ===
WARNING: This material was indexed at various past dates. Dates mentioned in this
material are historical and DO NOT represent the current date/time.
Use for background information only. The TRUTH PACKET above is authoritative.

{context}
=== END REFERENCE MATERIAL ==="""
        else:
            rag_section = ""

        # === BUILD FINAL PROMPT ===
        # Order: System → Truth → Query → RAG (if any)
        prompt = f"""{system_prompt}

{truth_section}
{query_section}
{rag_section}

Respond to the user's query. If using reference material, synthesize it but remember:
the TRUTH PACKET is AUTHORITATIVE for current date/time and system state."""

        logger.debug(f"[RAG] Built prompt for requestId={request_tag}, context_len={len(context) if context else 0}")

        # Stream response (pass endpoint from router if provided)
        for event in self.stream_ollama_response(
            model=model,
            prompt=prompt,
            context=None,  # Already included in prompt
            temperature=temperature,
            num_predict=500,
            request_id=request_id,
            base_url=base_url
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

