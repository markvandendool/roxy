#!/usr/bin/env python3
"""
Run a deterministic OpenCode feedback loop from CLI.

Use this when an external agent (ROXY/Codex/Claude CLI) wants to:
1) Prompt OpenCode
2) Capture output
3) Re-prompt with prior output
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROXY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROXY_ROOT))

from tools.streaming_tools import StreamingTools  # noqa: E402


async def _run(args: argparse.Namespace) -> int:
    tools = StreamingTools(workdir=str(args.workdir))
    result = await tools.execute_tool(
        "opencode",
        {
            "action": "chain",
            "mode": args.mode,
            "model": args.model,
            "prompt": args.prompt,
            "chain_steps": args.steps,
            "chain_stop_prefix": args.stop_prefix,
            "timeout": args.timeout,
            "dir": str(args.workdir),
            "agent": args.agent,
            "variant": args.variant,
            "thinking": args.thinking,
            "ultramax": args.ultramax,
            "bootstrap": args.bootstrap,
            "fallback_free": args.fallback_free,
        },
    )

    payload = {
        "success": result.success,
        "output": result.data,
        "error": result.error,
        "metadata": result.metadata,
    }

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))
    return 0 if result.success else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OpenCode feedback loop")
    parser.add_argument("--prompt", required=True, help="Initial prompt/task")
    parser.add_argument("--steps", type=int, default=3, help="Max chain steps (1-8)")
    parser.add_argument("--stop-prefix", default="COMPLETE:", help="Stop when output starts with this prefix")
    parser.add_argument("--mode", default="primary", help="ULTRAMAX profile: primary/reasoning/fast/bigbrain/architect/free/max/codexmax/copilot/gmodels")
    parser.add_argument("--model", default="", help="Optional explicit OpenCode model id override")
    parser.add_argument("--timeout", type=float, default=180.0, help="Per-step timeout seconds")
    parser.add_argument("--agent", default="", help="Optional OpenCode agent name")
    parser.add_argument("--variant", default="", help="Optional model variant")
    parser.add_argument("--thinking", action="store_true", help="Enable OpenCode thinking output")
    parser.add_argument("--ultramax", dest="ultramax", action="store_true", default=True, help="Enable ULTRAMAX profile defaults")
    parser.add_argument("--no-ultramax", dest="ultramax", action="store_false", help="Disable ULTRAMAX defaults")
    parser.add_argument("--bootstrap", dest="bootstrap", action="store_true", default=True, help="Inject onboarding/SKOREQ context")
    parser.add_argument("--no-bootstrap", dest="bootstrap", action="store_false", help="Disable onboarding/SKOREQ context injection")
    parser.add_argument("--fallback-free", dest="fallback_free", action="store_true", default=True, help="Enable free-model fallback on provider lock/quota errors")
    parser.add_argument("--no-fallback-free", dest="fallback_free", action="store_false", help="Disable free-model fallback")
    parser.add_argument("--workdir", type=Path, default=ROXY_ROOT, help="Working directory")
    parser.add_argument("--output-json", type=Path, default=None, help="Optional output JSON file")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
