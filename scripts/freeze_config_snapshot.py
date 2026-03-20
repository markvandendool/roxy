#!/usr/bin/env python3
"""Create a reproducible ROXY configuration freeze snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List
from urllib.error import URLError
from urllib.request import urlopen

ROXY_ROOT = Path(os.environ.get("ROXY_ROOT", str(Path.home() / ".roxy")))
DEFAULT_OUTPUT = ROXY_ROOT / "ROXY_CONFIG_FROZEN.md"
DEFAULT_BASE_URL = os.environ.get("ROXY_BASE_URL", "http://127.0.0.1:8766")

SENSITIVE_MARKERS = ("TOKEN", "PASSWORD", "SECRET", "API_KEY", "JWT")

TRACKED_ENV_KEYS = [
    "ROXY_USER_ID",
    "ROXY_DEFAULT_USER_ID",
    "ROXY_CANONICAL_USER_ID",
    "ROXY_MEMORY_RECALL_ITEMS",
    "ROXY_MEMORY_RECALL_MIN_SCORE",
    "ROXY_MEMORY_RECALL_MIN_SIMILARITY",
    "ROXY_MEMORY_RECALL_MIN_LEXICAL",
    "ROXY_MEMORY_CONTEXT_MAX_CHARS",
    "ROXY_MEMORY_SNIPPET_CHARS",
    "ROXY_REFLECTION_RETRY_THRESHOLD",
    "ROXY_REFLECTION_MAX_RETRIES",
    "ROXY_ENABLE_REFLECTION_RETRY",
    "ROXY_EVAL_PASS_THRESHOLD",
    "ROXY_ENABLE_AGENTIC_PIPELINE",
    "ROXY_ENABLE_PROACTIVE_HINTS",
    "ROXY_IDENTITY_ENFORCE_CANONICAL",
    "ROXY_OLLAMA_6900XT_URL",
    "ROXY_OLLAMA_W5700X_URL",
    "OLLAMA_HOST",
    "OLLAMA_BASE_URL",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
]

SERVICE_UNITS = [
    "roxy-core.service",
    "ollama.service",
    "ollama-fast.service",
    "ollama-6900xt.service",
    "ollama-w5700x.service",
]


def run(cmd: List[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return (proc.stdout or proc.stderr or "").strip()


def service_env() -> Dict[str, str]:
    raw = run(["systemctl", "--user", "show", "roxy-core.service", "--property", "Environment", "--value"])
    values: Dict[str, str] = {}
    if not raw:
        return values
    for token in shlex.split(raw):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        values[key] = value
    return values


def redact(key: str, value: str) -> str:
    upper = key.upper()
    if any(marker in upper for marker in SENSITIVE_MARKERS):
        if not value:
            return "<redacted-empty>"
        return f"<redacted:{len(value)}-chars>"
    return value


def fetch_json(url: str) -> Dict:
    try:
        with urlopen(url, timeout=5) as resp:
            payload = resp.read().decode("utf-8")
        return json.loads(payload)
    except (URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return {"error": "unavailable"}


def collect_env_snapshot() -> Dict[str, str]:
    svc_env = service_env()
    snapshot: Dict[str, str] = {}
    for key in TRACKED_ENV_KEYS:
        value = os.environ.get(key)
        if value is None:
            value = svc_env.get(key)
        if value is None:
            value = "<unset>"
        snapshot[key] = redact(key, value)
    return snapshot


def collect_service_states() -> Dict[str, str]:
    states: Dict[str, str] = {}
    for unit in SERVICE_UNITS:
        states[unit] = run(["systemctl", "--user", "is-active", unit]) or "unknown"
    return states


def build_markdown(base_url: str) -> str:
    now = dt.datetime.now().astimezone().isoformat()
    env_snapshot = collect_env_snapshot()
    states = collect_service_states()
    health = fetch_json(f"{base_url}/health")
    ready = fetch_json(f"{base_url}/ready")
    infrastructure = fetch_json(f"{base_url}/infrastructure")

    lines: List[str] = []
    lines.append("# ROXY Config Freeze")
    lines.append("")
    lines.append(f"- Captured: `{now}`")
    lines.append(f"- Host: `{platform.node()}`")
    lines.append(f"- Platform: `{platform.platform()}`")
    lines.append(f"- Python: `{platform.python_version()}`")
    lines.append(f"- Base URL: `{base_url}`")
    lines.append("")

    lines.append("## Service States")
    for unit, state in states.items():
        lines.append(f"- `{unit}`: `{state}`")
    lines.append("")

    lines.append("## Frozen Environment")
    for key in TRACKED_ENV_KEYS:
        lines.append(f"- `{key}`: `{env_snapshot.get(key, '<unset>')}`")
    lines.append("")

    lines.append("## Health Snapshot")
    lines.append("```json")
    lines.append(json.dumps(health, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")

    lines.append("## Ready Snapshot")
    lines.append("```json")
    lines.append(json.dumps(ready, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")

    lines.append("## Infrastructure Snapshot")
    lines.append("```json")
    lines.append(json.dumps(infrastructure, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")

    lines.append("## Qualification Commands")
    lines.append("```bash")
    lines.append("cd ~/.roxy")
    lines.append("./scripts/capture_eval_baseline.sh")
    lines.append("./venv/bin/python scripts/eval_harness.py")
    lines.append("./venv/bin/python scripts/freeze_config_snapshot.py")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate ROXY config freeze markdown")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output markdown path")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ROXY base URL")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown(args.base_url)
    output_path.write_text(markdown)
    print(f"WROTE={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
