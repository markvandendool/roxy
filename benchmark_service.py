#!/usr/bin/env python3
"""
ROXY Benchmark Service - lm-eval harness wrapper with evidence bundles

This module provides the authoritative benchmark execution for ROXY.
It wraps lm-evaluation-harness for reproducible, evidence-backed results.

Evidence bundles are stored in ~/ROXY_EVIDENCES/<topic>_<timestamp>/
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import shutil

# Module logger
logger = logging.getLogger(__name__)

# Evidence bundle root
EVIDENCE_ROOT = Path.home() / "ROXY_EVIDENCES"
EVIDENCE_ROOT.mkdir(exist_ok=True)

# Benchmark state
_current_run: Optional[dict] = None
_current_process: Optional[subprocess.Popen] = None
_run_lock = threading.Lock()
_run_history: list[dict] = []

# Import pool identity (single source of truth)
from pool_identity import (
    CANONICAL_POOLS,
    POOL_ALIASES,
    normalize_pool_key,
    resolve_pool as _pool_identity_resolve,
    get_all_pools_status,
)

# lm-eval binary path (in ROXY venv)
ROXY_VENV = Path.home() / ".roxy" / "venv"
LM_EVAL_BIN = ROXY_VENV / "bin" / "lm_eval"


def get_status() -> dict:
    """Get current benchmark status."""
    with _run_lock:
        if _current_run:
            return {
                "status": _current_run.get("status", "unknown"),
                "task": _current_run.get("task"),
                "model": _current_run.get("model"),
                "started_at": _current_run.get("started_at"),
                "progress": _current_run.get("progress", "running"),
                "evidence_id": _current_run.get("evidence_id"),
            }

        # Return last completed run if no current run
        if _run_history:
            last = _run_history[-1]
            return {
                "status": "idle",
                "last_run": {
                    "evidence_id": last.get("evidence_id"),
                    "task": last.get("task"),
                    "model": last.get("model"),
                    "completed_at": last.get("completed_at"),
                    "score": last.get("score"),
                    "success": last.get("success", False),
                }
            }

        return {"status": "idle", "last_run": None}


def get_history(limit: int = 10, include_paths: bool = False) -> list[dict]:
    """Get benchmark run history.

    Args:
        limit: Max number of entries to return
        include_paths: If True, include full local paths (requires auth)
    """
    history = []

    if EVIDENCE_ROOT.exists():
        for evidence_dir in sorted(EVIDENCE_ROOT.iterdir(), reverse=True):
            if not evidence_dir.is_dir():
                continue

            # Try summary.json first, fall back to manifest.json
            summary_path = evidence_dir / "summary.json"
            manifest_path = evidence_dir / "manifest.json"

            data_path = summary_path if summary_path.exists() else manifest_path
            if not data_path.exists():
                continue

            try:
                with open(data_path) as f:
                    data = json.load(f)

                entry = {
                    "evidence_id": evidence_dir.name,
                    "task": data.get("task"),
                    "model": data.get("model"),
                    "score": data.get("score"),
                    "metric": data.get("metric"),
                    "num_fewshot": data.get("num_fewshot"),
                    "limit": data.get("limit"),
                    "completed_at": data.get("completed_at"),
                    "success": data.get("success", False),
                    "authoritative": data.get("authoritative", False),
                }

                # Only include paths if authenticated
                if include_paths:
                    entry["path"] = str(evidence_dir)

                history.append(entry)
            except (json.JSONDecodeError, IOError):
                continue

            if len(history) >= limit:
                break

    return history


def get_artifact(evidence_id: str) -> Optional[dict]:
    """Get artifact metadata and file paths for an evidence bundle."""
    evidence_dir = EVIDENCE_ROOT / evidence_id

    if not evidence_dir.exists() or not evidence_dir.is_dir():
        return None

    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    # List all files in the evidence bundle
    files = []
    for f in evidence_dir.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
            })

    return {
        "evidence_id": evidence_id,
        "path": str(evidence_dir),
        "manifest": manifest,
        "files": files,
    }


def cancel_run() -> dict:
    """Cancel the currently running benchmark.

    Returns:
        dict with cancellation status
    """
    global _current_run, _current_process

    with _run_lock:
        if not _current_run:
            return {"error": "No benchmark currently running", "status": "idle"}

        if not _current_process:
            return {"error": "Benchmark in progress but no process to kill", "status": "unknown"}

        evidence_id = _current_run.get("evidence_id")
        task = _current_run.get("task")
        model = _current_run.get("model")

        # Kill the process
        try:
            _current_process.terminate()
            _current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _current_process.kill()
            _current_process.wait()

        # Update evidence bundle with cancellation info
        if evidence_id:
            evidence_dir = EVIDENCE_ROOT / evidence_id
            manifest_path = evidence_dir / "manifest.json"

            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    manifest["cancelled"] = True
                    manifest["cancelled_at"] = datetime.now().isoformat()
                    manifest["success"] = False
                    manifest["error"] = "Cancelled by operator"
                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=2)
                except (json.JSONDecodeError, IOError):
                    pass

            # Create summary.json for cancelled run
            summary = {
                "evidence_id": evidence_id,
                "task": task,
                "model": model,
                "score": None,
                "metric": None,
                "success": False,
                "cancelled": True,
                "cancelled_at": datetime.now().isoformat(),
            }
            try:
                with open(evidence_dir / "summary.json", "w") as f:
                    json.dump(summary, f, indent=2)
            except IOError:
                pass

        # Clear state
        _current_process = None
        cancelled_run = _current_run.copy()
        _current_run = None

    return {
        "status": "cancelled",
        "evidence_id": evidence_id,
        "task": task,
        "model": model,
        "message": "Benchmark cancelled by operator",
    }


def _create_evidence_bundle(task: str, model: str) -> tuple[str, Path]:
    """Create a new evidence bundle directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    evidence_id = f"{task}_{timestamp}"
    evidence_dir = EVIDENCE_ROOT / evidence_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    return evidence_id, evidence_dir


def _run_benchmark_thread(
    task: str,
    model: str,
    model_args: str,
    num_fewshot: int,
    limit: Optional[int],
    evidence_id: str,
    evidence_dir: Path,
    tokenizer: str,
    temperature: float,
    authoritative: bool,
    pool_requested: str,
    pool_used: str,
    base_url_used: str,
    ollama_service_hint: str,
    gpu_hint: str,
):
    """Background thread to run lm-eval benchmark."""
    global _current_run

    started_at = datetime.now().isoformat()

    # Build lm_eval command
    cmd = [
        str(LM_EVAL_BIN),
        "--model", "local-chat-completions",
        "--model_args", model_args,
        "--tasks", task,
        "--num_fewshot", str(num_fewshot),
        "--output_path", str(evidence_dir),
        "--log_samples",
        "--apply_chat_template",
    ]

    if limit:
        cmd.extend(["--limit", str(limit)])

    # Create manifest
    manifest = {
        "evidence_id": evidence_id,
        "task": task,
        "model": model,
        "model_args": model_args,
        "num_fewshot": num_fewshot,
        "limit": limit,
        "temperature": temperature,
        "tokenizer": tokenizer,
        "authoritative": authoritative,
        # Pool identity fields for truth.json
        "pool_requested": pool_requested,
        "pool_used": pool_used,
        "base_url_used": base_url_used,
        "ollama_service_hint": ollama_service_hint,
        "gpu_hint": gpu_hint,
        "started_at": started_at,
        "command": cmd,
        "success": False,
        "score": None,
        "metric": None,
        "completed_at": None,
    }

    # Save initial manifest
    manifest_path = evidence_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    stdout_path = evidence_dir / "stdout.log"
    stderr_path = evidence_dir / "stderr.log"

    try:
        with _run_lock:
            _current_run["progress"] = "executing lm-eval"

        # Run lm-eval using Popen for cancel support
        global _current_process
        with open(stdout_path, "w") as stdout_f, open(stderr_path, "w") as stderr_f:
            proc = subprocess.Popen(
                cmd,
                stdout=stdout_f,
                stderr=stderr_f,
                cwd=str(evidence_dir),
            )
            with _run_lock:
                _current_process = proc

            # Wait with timeout
            try:
                returncode = proc.wait(timeout=3600)  # 1 hour timeout
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise

        with _run_lock:
            _current_process = None

        manifest["exit_code"] = returncode
        manifest["success"] = returncode == 0

        # Try to parse results
        if manifest["success"]:
            # lm-eval outputs results to a subdirectory named after the model
            for results_file in evidence_dir.glob("**/results_*.json"):
                try:
                    with open(results_file) as f:
                        results_data = json.load(f)

                    # Extract score from results
                    if "results" in results_data:
                        task_results = results_data["results"]
                        if task in task_results:
                            task_data = task_results[task]
                            # Try flexible-extract first (more lenient), then strict
                            for metric in ["exact_match,flexible-extract", "exact_match,strict-match",
                                           "acc", "acc_norm", "exact_match", "em"]:
                                if metric in task_data:
                                    manifest["score"] = task_data[metric]
                                    manifest["metric"] = metric
                                    break

                    # Store lm-eval version and config
                    manifest["lm_eval_config"] = results_data.get("config", {})

                    # STOP-LINE #1: Copy lm_eval results to bundle root
                    try:
                        shutil.copy2(results_file, evidence_dir / "lm_eval_results.json")
                    except IOError:
                        pass

                    break
                except (json.JSONDecodeError, IOError):
                    continue

        # STOP-LINE #1: Create meta.json with execution metadata
        import platform
        import socket
        meta = {
            "evidence_id": evidence_id,
            "benchmark_tool": "lm-evaluation-harness",
            "benchmark_version": manifest.get("lm_eval_config", {}).get("version", "unknown"),
            "execution": {
                "started_at": started_at,
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": None,  # Will be calculated
                "exit_code": manifest.get("exit_code"),
                "success": manifest.get("success", False),
            },
            "environment": {
                "hostname": socket.gethostname(),
                "platform": platform.system(),
                "python_version": platform.python_version(),
            },
            "files": {
                "manifest": "manifest.json",
                "request": "request.json",
                "resolved": "resolved.json",
                "summary": "summary.json",
                "lm_eval_results": "lm_eval_results.json" if manifest.get("success") else None,
                "stdout": "stdout.log",
                "stderr": "stderr.log",
            }
        }
        # Calculate duration
        try:
            from datetime import datetime as dt
            start = dt.fromisoformat(started_at)
            end = dt.now()
            meta["execution"]["duration_seconds"] = (end - start).total_seconds()
        except:
            pass

        # CHIEF DIRECTIVE: Add throughput metrics
        lm_eval_path = evidence_dir / "lm_eval_results.json"
        if lm_eval_path.exists():
            try:
                with open(lm_eval_path) as f:
                    lm_data = json.load(f)
                # Get total effective samples across all tasks
                n_samples = lm_data.get("n-samples", {})
                samples_total = sum(
                    v.get("effective", v) if isinstance(v, dict) else v
                    for v in n_samples.values()
                )
                # Get wall time from lm_eval or use our own duration
                wall_seconds = lm_data.get("total_evaluation_time_seconds")
                if wall_seconds is not None:
                    wall_seconds = float(wall_seconds)
                else:
                    wall_seconds = meta["execution"]["duration_seconds"]
                meta["throughput"] = {
                    "samples_total": samples_total,
                    "wall_seconds": round(wall_seconds, 3) if wall_seconds else None,
                    "samples_per_sec": round(samples_total / wall_seconds, 4) if wall_seconds and samples_total else None,
                }
            except Exception:
                pass  # Throughput calculation is best-effort

        with open(evidence_dir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

    except subprocess.TimeoutExpired:
        manifest["error"] = "Benchmark timed out after 1 hour"
        manifest["success"] = False
    except Exception as e:
        manifest["error"] = str(e)
        manifest["success"] = False

    manifest["completed_at"] = datetime.now().isoformat()

    # Save final manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # GATE B3: Create summary.json with authoritative labeling
    summary = {
        "evidence_id": evidence_id,
        "task": task,
        "model": model,
        "score": manifest.get("score"),
        "metric": manifest.get("metric"),
        "num_fewshot": num_fewshot,
        "limit": limit,
        "temperature": temperature,
        "tokenizer": tokenizer,
        "success": manifest.get("success", False),
        "authoritative": authoritative,
        "completed_at": manifest.get("completed_at"),
    }

    # Add warning for small sample sizes
    if not authoritative:
        summary["warning"] = f"SMALL SAMPLE / NON-AUTHORITATIVE (limit={limit} < {AUTHORITATIVE_LIMIT})"

    # Add stderr excerpt if failed
    if not manifest.get("success") and stderr_path.exists():
        try:
            stderr_content = stderr_path.read_text()
            # Last 500 chars of stderr
            summary["stderr_tail"] = stderr_content[-500:] if len(stderr_content) > 500 else stderr_content
        except IOError:
            pass

    with open(evidence_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # CHIEF DIRECTIVE: Create truth.json for bundle self-sufficiency
    truth = {
        "captured_at": datetime.now().isoformat(),
        "evidence_id": evidence_id,
        "bench_resolved": {
            "pool_requested": manifest.get("pool_requested"),
            "pool_used": manifest.get("pool_used"),
            "base_url_used": manifest.get("base_url_used"),
            "ollama_service_hint": manifest.get("ollama_service_hint"),
            "gpu_hint": manifest.get("gpu_hint"),
        },
        "daemon_info_snapshot": _capture_daemon_info(),
    }
    with open(evidence_dir / "truth.json", "w") as f:
        json.dump(truth, f, indent=2)

    # Update history
    with _run_lock:
        _run_history.append(manifest)
        _current_run = None


# Map Ollama model names to HuggingFace tokenizer repos
TOKENIZER_MAP = {
    "qwen2.5-coder:14b": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "qwen2.5-coder:7b": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "qwen2.5:32b": "Qwen/Qwen2.5-32B-Instruct",
    "qwen2.5:14b": "Qwen/Qwen2.5-14B-Instruct",
    "qwen2.5:7b": "Qwen/Qwen2.5-7B-Instruct",
    "llama3.2:3b": "meta-llama/Llama-3.2-3B-Instruct",
    "llama3.1:8b": "meta-llama/Llama-3.1-8B-Instruct",
    "codellama:13b": "codellama/CodeLlama-13b-Instruct-hf",
    "mistral:7b": "mistralai/Mistral-7B-Instruct-v0.3",
    "deepseek-coder:6.7b": "deepseek-ai/deepseek-coder-6.7b-instruct",
}

# Authoritative threshold
AUTHORITATIVE_LIMIT = 50


def _capture_daemon_info() -> dict:
    """Capture /info snapshot from ROXY daemon for truth.json."""
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8766/info", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            import json as _json
            info = _json.loads(resp.read().decode())
            # Extract relevant fields for truth
            return {
                "ollama_pools": info.get("ollama", {}).get("pools", {}),
                "ollama_misconfigured": info.get("ollama", {}).get("misconfigured"),
                "github_configured": info.get("github", {}).get("configured"),
            }
    except Exception as e:
        return {"error": str(e), "captured": False}

# Pool identity now imported from pool_identity.py (single source of truth)
# CANONICAL_POOLS and POOL_ALIASES are imported at module level


def check_pool_invariants() -> dict:
    """
    CHIEF DIRECTIVE: Startup invariant to detect pool misconfiguration.

    Probes both pools for latency and verifies expected GPU hierarchy.
    The 6900XT should respond faster than W5700X for identical requests.
    If not, something may be misconfigured (wrong service on wrong port).

    Returns:
        {
            "ok": bool,
            "pools": {pool_name: {reachable, latency_ms, error}},
            "warning": str | None,
            "checked_at": str,
        }
    """
    import urllib.request
    import time

    result = {
        "ok": True,
        "pools": {},
        "warning": None,
        "checked_at": datetime.now().isoformat(),
    }

    def probe_latency(url: str, samples: int = 3) -> tuple[bool, float, str]:
        """Probe pool with multiple samples, return (reachable, avg_latency_ms, error)."""
        latencies = []
        try:
            for _ in range(samples):
                start = time.perf_counter()
                req = urllib.request.Request(f"{url}/api/version", method="GET")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        latency_ms = (time.perf_counter() - start) * 1000
                        latencies.append(latency_ms)
            if latencies:
                return True, sum(latencies) / len(latencies), None
            return False, 0, "No successful probes"
        except Exception as e:
            return False, 0, str(e)

    # Probe each pool (using CANONICAL_POOLS from pool_identity.py)
    for pool_name, pool_info in CANONICAL_POOLS.items():
        url = f"http://127.0.0.1:{pool_info['port']}"
        reachable, latency_ms, error = probe_latency(url)
        result["pools"][pool_name] = {
            "port": pool_info["port"],
            "gpu": pool_info["gpu"],
            "service": pool_info["service"],
            "reachable": reachable,
            "latency_ms": round(latency_ms, 2) if reachable else None,
            "error": error,
        }

    # Check invariant: both pools should be reachable for meaningful comparison
    w5700x_info = result["pools"].get("w5700x", {})
    xt6900_info = result["pools"].get("6900xt", {})

    if not w5700x_info.get("reachable") or not xt6900_info.get("reachable"):
        # Can't verify hierarchy if pools are down - not an invariant failure
        unreachable = [p for p, i in result["pools"].items() if not i.get("reachable")]
        if unreachable:
            result["warning"] = f"Pools unreachable (cannot verify GPU hierarchy): {unreachable}"
        return result

    # INVARIANT: 6900XT latency should be <= W5700X latency (it's the faster GPU)
    # Note: Simple version check doesn't test actual inference speed,
    # but significant latency difference on the SAME endpoint would indicate
    # possible misconfig (e.g., running wrong service on wrong port)
    w5700x_latency = w5700x_info["latency_ms"]
    xt6900_latency = xt6900_info["latency_ms"]

    # If W5700X responds much faster than 6900XT on basic health check,
    # the services might be swapped. Allow 50% tolerance for network noise.
    if w5700x_latency > 0 and xt6900_latency > w5700x_latency * 1.5:
        result["ok"] = False
        warning_msg = (
            f"POOL LATENCY ANOMALY: 6900XT ({xt6900_latency:.1f}ms) slower than "
            f"W5700X ({w5700x_latency:.1f}ms). Check if ollama services are on correct ports. "
            f"Expected: 6900XT on port 11435 (http://127.0.0.1:11435), "
            f"W5700X on port 11434 (http://127.0.0.1:11434)."
        )
        result["warning"] = warning_msg
        # CHIEF DIRECTIVE: Make failures LOUD
        logger.error(f"POOL INVARIANT FAILURE: {warning_msg}")

    return result


def _resolve_benchmark_pool(pool_requested: str) -> dict:
    """
    Resolve pool for benchmark execution.

    Args:
        pool_requested: "AUTO", "W5700X", "6900XT" (or legacy "BIG"/"FAST")
                        Case-insensitive, accepts all variants.

    Returns:
        {
            "pool_requested_raw": str,       # Exactly what user passed
            "pool_requested_canonical": str, # Normalized: "w5700x", "6900xt", or "auto"
            "pool_used": "w5700x" | "6900xt",
            "base_url": str,
            "base_url_chat": str (for lm-eval),
            "ollama_service_hint": str,
            "gpu_hint": str,
            "reachable": bool,
            "error": str | None,
        }

    Policy:
        - ACCEPT: "W5700X", "6900XT", "w5700x", "6900xt", "BIG", "FAST" (case-insensitive)
        - RETURN: Always canonical lowercase ("w5700x", "6900xt", "auto")
        - W5700X is default for benchmarks (port 11434)
        - 6900XT is the faster GPU (port 11435) - use for perf-critical
        - HARD-FAIL if requested pool unreachable
        - NO SILENT FALLBACK: If pool env var not set, return error
        - AUTO tries W5700X first, falls back to 6900XT
    """
    import urllib.request
    import os

    # Normalize pool input using pool_identity module (handles deprecation warnings)
    pool_requested_raw, pool_key = normalize_pool_key(pool_requested)

    # Get pool URLs from environment - NO HARDCODED DEFAULTS for operator-grade
    w5700x_url_raw = os.getenv("ROXY_OLLAMA_W5700X_URL") or os.getenv("OLLAMA_BIG_URL") or os.getenv("ROXY_OLLAMA_BIG_URL")
    xt6900_url_raw = os.getenv("ROXY_OLLAMA_6900XT_URL") or os.getenv("OLLAMA_FAST_URL") or os.getenv("ROXY_OLLAMA_FAST_URL")

    # Fallback to legacy OLLAMA_HOST only for AUTO mode
    legacy_url = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL")

    # Determine URLs with explicit unconfigured detection
    w5700x_url = w5700x_url_raw or legacy_url or "http://127.0.0.1:11434"
    xt6900_url = xt6900_url_raw or "http://127.0.0.1:11435"
    w5700x_configured = bool(w5700x_url_raw or legacy_url)
    xt6900_configured = bool(xt6900_url_raw)

    # Normalize localhost -> 127.0.0.1
    w5700x_url = w5700x_url.replace("localhost", "127.0.0.1").replace("[::1]", "127.0.0.1")
    xt6900_url = xt6900_url.replace("localhost", "127.0.0.1").replace("[::1]", "127.0.0.1")

    def check_reachable(url: str, timeout: float = 2.0) -> bool:
        try:
            req = urllib.request.Request(f"{url}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except:
            return False

    def get_identity(pool: str, url: str) -> dict:
        # Extract port from URL to determine identity
        import re
        port_match = re.search(r':(\d+)', url)
        port = int(port_match.group(1)) if port_match else None

        # Look up identity by port (using CANONICAL_POOLS from pool_identity.py)
        for pool_name, pool_info in CANONICAL_POOLS.items():
            if pool_info["port"] == port:
                return {
                    "ollama_service_hint": pool_info["service"],
                    "gpu_hint": pool_info["gpu"],
                }

        # Unknown port - no hints
        return {
            "ollama_service_hint": None,
            "gpu_hint": None,
        }

    # Determine canonical form for API response
    # pool_key is already lowercase and alias-resolved
    pool_requested_canonical = pool_key  # "w5700x", "6900xt", or "auto"

    def _make_result(result: dict) -> dict:
        """Add pool_requested_raw and pool_requested_canonical to all responses."""
        return {
            "pool_requested_raw": pool_requested_raw,
            "pool_requested_canonical": pool_requested_canonical,
            **result
        }

    # Handle canonical pool names and legacy aliases
    if pool_key == "w5700x" or pool_key == "big":
        # W5700X pool (port 11434)
        if not w5700x_configured:
            return _make_result({
                "pool_used": None,
                "base_url": w5700x_url,
                "base_url_chat": f"{w5700x_url}/v1/chat/completions",
                "reachable": False,
                "error": "W5700X pool not configured. Set ROXY_OLLAMA_W5700X_URL (or legacy OLLAMA_BIG_URL) environment variable.",
                "ollama_service_hint": None,
                "gpu_hint": None,
            })
        reachable = check_reachable(w5700x_url)
        if not reachable:
            return _make_result({
                "pool_used": None,
                "base_url": w5700x_url,
                "base_url_chat": f"{w5700x_url}/v1/chat/completions",
                "reachable": False,
                "error": f"W5700X pool unreachable at {w5700x_url}. Start ollama-w5700x.service or use pool=6900xt",
                **get_identity("w5700x", w5700x_url),
            })
        return _make_result({
            "pool_used": "w5700x",
            "base_url": w5700x_url,
            "base_url_chat": f"{w5700x_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            **get_identity("w5700x", w5700x_url),
        })

    elif pool_key == "6900xt" or pool_key == "fast":
        # 6900XT pool (port 11435) - the faster GPU
        if not xt6900_configured:
            return _make_result({
                "pool_used": None,
                "base_url": xt6900_url,
                "base_url_chat": f"{xt6900_url}/v1/chat/completions",
                "reachable": False,
                "error": "6900XT pool not configured. Set ROXY_OLLAMA_6900XT_URL (or legacy OLLAMA_FAST_URL) environment variable.",
                "ollama_service_hint": None,
                "gpu_hint": None,
            })
        reachable = check_reachable(xt6900_url)
        if not reachable:
            return _make_result({
                "pool_used": None,
                "base_url": xt6900_url,
                "base_url_chat": f"{xt6900_url}/v1/chat/completions",
                "reachable": False,
                "error": f"6900XT pool unreachable at {xt6900_url}. Start ollama-6900xt.service",
                **get_identity("6900xt", xt6900_url),
            })
        return _make_result({
            "pool_used": "6900xt",
            "base_url": xt6900_url,
            "base_url_chat": f"{xt6900_url}/v1/chat/completions",
            "reachable": True,
            "error": None,
            **get_identity("6900xt", xt6900_url),
        })

    else:  # AUTO - try W5700X first, fall back to 6900XT
        w5700x_reachable = check_reachable(w5700x_url)
        if w5700x_reachable:
            return _make_result({
                "pool_used": "w5700x",
                "base_url": w5700x_url,
                "base_url_chat": f"{w5700x_url}/v1/chat/completions",
                "reachable": True,
                "error": None,
                **get_identity("w5700x", w5700x_url),
            })

        xt6900_reachable = check_reachable(xt6900_url)
        if xt6900_reachable:
            return _make_result({
                "pool_used": "6900xt",
                "base_url": xt6900_url,
                "base_url_chat": f"{xt6900_url}/v1/chat/completions",
                "reachable": True,
                "error": None,
                **get_identity("6900xt", xt6900_url),
            })

        return _make_result({
            "pool_used": None,
            "base_url": w5700x_url,
            "base_url_chat": f"{w5700x_url}/v1/chat/completions",
            "reachable": False,
            "error": f"No pools reachable. W5700X={w5700x_url}, 6900XT={xt6900_url}",
            "ollama_service_hint": None,
            "gpu_hint": None,
        })


def start_run(
    task: str = "gsm8k",
    model: str = "qwen2.5-coder:14b",
    pool: str = "W5700X",
    num_fewshot: int = 5,
    limit: Optional[int] = 50,
    dry_run: bool = False,
) -> dict:
    """
    Start a benchmark run.

    Args:
        task: lm-eval task name (e.g., gsm8k, hellaswag, mmlu)
        model: Model name for identification
        pool: Pool to use - "W5700X" (default), "6900XT", or "AUTO"
              Legacy "BIG"/"FAST" still work but map to hardware names
        num_fewshot: Number of few-shot examples
        limit: Sample limit (None for full eval)

    Returns:
        dict with evidence_id and status
    """
    global _current_run

    with _run_lock:
        if _current_run:
            return {
                "error": "Benchmark already running",
                "current_run": {
                    "evidence_id": _current_run.get("evidence_id"),
                    "task": _current_run.get("task"),
                    "started_at": _current_run.get("started_at"),
                }
            }

    # Check lm-eval is available
    if not LM_EVAL_BIN.exists():
        return {"error": f"lm-eval not found at {LM_EVAL_BIN}"}

    # GATE B4: Hard fail on unknown tokenizer - DO NOT silently fallback
    tokenizer_path = TOKENIZER_MAP.get(model)
    if not tokenizer_path:
        supported = list(TOKENIZER_MAP.keys())
        return {
            "error": f"Unknown model: {model}",
            "hint": f"Tokenizer mapping not found. Supported models: {supported}",
            "action": "Add tokenizer mapping to TOKENIZER_MAP in benchmark_service.py"
        }

    # POOL RESOLUTION: Determine which GPU/service to use
    pool_result = _resolve_benchmark_pool(pool)
    if pool_result.get("error"):
        return {
            "error": pool_result["error"],
            "pool_requested": pool,
            "pool_checked": pool_result.get("base_url"),
        }

    # TRUE DRY RUN: return pool resolution only; NO evidence; NO threads; NO locks
    if dry_run:
        dry_run_result = {
            "status": "dry_run",
            "dry_run": True,
            "task": task,
            "model": model,
            # API CONTRACT fields
            "pool_requested_raw": pool_result.get("pool_requested_raw"),
            "pool_requested_canonical": pool_result.get("pool_requested_canonical"),
            "pool_used": pool_result.get("pool_used"),
            "gpu_hint": pool_result.get("gpu_hint"),
            # Helpful operator fields
            "base_url_used": pool_result.get("base_url"),
            "base_url_chat": pool_result.get("base_url_chat"),
            "reachable": pool_result.get("reachable"),
            "num_fewshot": num_fewshot,
            "limit": limit,
        }
        # Only include error key if there's an actual error
        if pool_result.get("error"):
            dry_run_result["error"] = pool_result["error"]
        return dry_run_result

    # Extract resolved pool info
    base_url = pool_result["base_url_chat"]
    pool_used = pool_result["pool_used"]

    # Create evidence bundle
    evidence_id, evidence_dir = _create_evidence_bundle(task, model)

    # Fixed temperature for reproducibility
    temperature = 0.0

    # Determine authoritative status
    authoritative = limit is None or limit >= AUTHORITATIVE_LIMIT

    # Build model_args with resolved base_url
    model_args = f"model={model},base_url={base_url},tokenizer_backend=huggingface,tokenizer={tokenizer_path}"

    started_at = datetime.now().isoformat()

    # GATE B3: Create request.json (original request params) - API CONTRACT fields
    request_data = {
        "task": task,
        "model": model,
        # API CONTRACT: capture exact user input
        "pool_requested_raw": pool_result.get("pool_requested_raw"),
        "pool_requested_canonical": pool_result.get("pool_requested_canonical"),
        "num_fewshot": num_fewshot,
        "limit": limit,
        "requested_at": started_at,
    }
    with open(evidence_dir / "request.json", "w") as f:
        json.dump(request_data, f, indent=2)

    # GATE B3: Create resolved.json (final resolved args) - INCLUDES POOL IDENTITY
    resolved_data = {
        "task": task,
        "model": model,
        # Pool identity fields (MANDATORY for "prove 5700" audit)
        # API CONTRACT: raw input + canonical form + actual pool used
        "pool_requested_raw": pool_result.get("pool_requested_raw"),
        "pool_requested_canonical": pool_result.get("pool_requested_canonical"),
        "pool_used": pool_used,
        "base_url_used": base_url,
        "ollama_service_hint": pool_result.get("ollama_service_hint"),
        "gpu_hint": pool_result.get("gpu_hint"),
        # Standard fields
        "num_fewshot": num_fewshot,
        "limit": limit,
        "temperature": temperature,
        "tokenizer": tokenizer_path,
        "tokenizer_backend": "huggingface",
        "model_args": model_args,
        "authoritative": authoritative,
        "authoritative_threshold": AUTHORITATIVE_LIMIT,
        "resolved_at": started_at,
    }
    with open(evidence_dir / "resolved.json", "w") as f:
        json.dump(resolved_data, f, indent=2)

    # Set current run state
    with _run_lock:
        _current_run = {
            "status": "running",
            "task": task,
            "model": model,
            "started_at": started_at,
            "progress": "initializing",
            "evidence_id": evidence_id,
        }

    # Start background thread
    thread = threading.Thread(
        target=_run_benchmark_thread,
        args=(task, model, model_args, num_fewshot, limit, evidence_id, evidence_dir,
              tokenizer_path, temperature, authoritative,
              pool, pool_used, base_url,
              pool_result.get("ollama_service_hint"), pool_result.get("gpu_hint")),
        daemon=True,
    )
    thread.start()

    return {
        "status": "started",
        "evidence_id": evidence_id,
        "task": task,
        "model": model,
        # API CONTRACT: Accept many forms, return canonical
        "pool_requested_raw": pool_result.get("pool_requested_raw"),
        "pool_requested_canonical": pool_result.get("pool_requested_canonical"),
        "pool_used": pool_used,
        "gpu_hint": pool_result.get("gpu_hint"),
        "base_url_used": base_url,
        "num_fewshot": num_fewshot,
        "limit": limit,
        "evidence_path": str(evidence_dir),
    }


# Supported benchmark tasks (subset of lm-eval tasks relevant to coding/reasoning)
SUPPORTED_TASKS = {
    "gsm8k": "Grade school math word problems (8-shot default)",
    "hellaswag": "Commonsense reasoning completion",
    "arc_challenge": "AI2 Reasoning Challenge (hard)",
    "arc_easy": "AI2 Reasoning Challenge (easy)",
    "winogrande": "Commonsense pronoun resolution",
    "truthfulqa_mc2": "TruthfulQA multiple choice",
    "mmlu": "Massive Multitask Language Understanding",
    "humaneval": "Code generation (requires special setup)",
    "mbpp": "Mostly Basic Python Problems",
}


def list_tasks() -> dict:
    """List supported benchmark tasks."""
    return {
        "tasks": SUPPORTED_TASKS,
        "note": "Additional lm-eval tasks may work but are not officially supported",
    }


if __name__ == "__main__":
    # Quick test
    print("Benchmark Service Status:", get_status())
    print("Supported Tasks:", list_tasks())
