#!/usr/bin/env python3
"""
Canonical trace spine for ROXY operator actions and evals.

This keeps one structured artifact format even when external sinks are absent.
If Langfuse is configured, traces are mirrored there as well.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


ROXY_DIR = Path.home() / ".roxy"
TRACE_DIR = ROXY_DIR / "data" / "agent_traces"
TRACE_DIR.mkdir(parents=True, exist_ok=True)

try:
    from opentelemetry import trace as otel_trace  # type: ignore
    OTEL_AVAILABLE = True
except Exception:
    otel_trace = None
    OTEL_AVAILABLE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_sanitize(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_sanitize(v) for v in value]
    return value


class TraceSpine:
    def __init__(self) -> None:
        self._lock = Lock()
        self._langfuse = None
        self._tracer = otel_trace.get_tracer("roxy.trace_spine") if OTEL_AVAILABLE else None
        self._init_langfuse()

    def _init_langfuse(self) -> None:
        try:
            sys.path.insert(0, str(ROXY_DIR / "observability"))
            from langfuse_integration import get_observability  # type: ignore

            obs = get_observability()
            if getattr(obs, "enabled", False):
                self._langfuse = obs
        except Exception:
            self._langfuse = None

    def _append_jsonl(self, prefix: str, payload: Dict[str, Any]) -> str:
        path = TRACE_DIR / f"{prefix}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        sanitized = _json_sanitize(payload)
        with self._lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(sanitized) + "\n")
        return str(path)

    def record_run_trace(
        self,
        trace_id: str,
        prompt: str,
        response: str,
        metadata: Dict[str, Any],
        spans: Optional[List[Dict[str, Any]]] = None,
        status: str = "success",
    ) -> str:
        entry = {
            "trace_id": trace_id,
            "timestamp": _now_iso(),
            "kind": "run",
            "status": status,
            "prompt": prompt,
            "response_preview": str(response)[:4000],
            "metadata": metadata,
            "spans": spans or [],
        }
        path = self._append_jsonl("runs", entry)

        if self._tracer is not None:
            try:
                attrs = {
                    "roxy.trace_id": trace_id,
                    "roxy.route": str(metadata.get("route") or "unknown"),
                    "roxy.operator_surface": str(metadata.get("operator_surface") or "api"),
                    "roxy.truth_primary": str((metadata.get("truth_sources") or {}).get("primary") or "unknown"),
                }
                with self._tracer.start_as_current_span("roxy.run", attributes=attrs):
                    for span in spans or []:
                        span_attrs = {str(k): str(v) for k, v in (span.get("attributes") or {}).items()}
                        with self._tracer.start_as_current_span(str(span.get("name") or "roxy.step"), attributes=span_attrs):
                            pass
            except Exception:
                pass

        if self._langfuse is not None:
            try:
                self._langfuse.record_generation(
                    name="roxy.run",
                    model=str(metadata.get("selected_model") or metadata.get("model_used") or "none"),
                    prompt=prompt,
                    completion=response,
                    metadata={
                        "trace_id": trace_id,
                        "route": metadata.get("route"),
                        "operator_surface": metadata.get("operator_surface"),
                        "truth_sources": metadata.get("truth_sources"),
                        "repo": metadata.get("repo"),
                    },
                )
            except Exception:
                pass

        return path

    def record_eval_trace(
        self,
        trace_id: str,
        prompt: str,
        response_payload: Dict[str, Any],
        verdict: Dict[str, Any],
    ) -> str:
        entry = {
            "trace_id": trace_id,
            "timestamp": _now_iso(),
            "kind": "eval",
            "prompt": prompt,
            "response": response_payload,
            "verdict": verdict,
        }
        return self._append_jsonl("evals", entry)


_TRACE_SPINE: Optional[TraceSpine] = None


def get_trace_spine() -> TraceSpine:
    global _TRACE_SPINE
    if _TRACE_SPINE is None:
        _TRACE_SPINE = TraceSpine()
    return _TRACE_SPINE

