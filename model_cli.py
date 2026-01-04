#!/usr/bin/env python3
"""
ROXY Model CLI - Seamless model swapping

Usage:
    roxy-model list              # List available models
    roxy-model active            # Show active model
    roxy-model set <model>       # Set active model
    roxy-model info <model>      # Show model capabilities
    roxy-model eval              # Run quick eval on active model
    roxy-model compare           # Compare all models
"""
import sys
from pathlib import Path

# Add ROXY dir to path
ROXY_DIR = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_DIR))

from model_provider import get_provider, set_active_model, list_models


def cmd_list():
    """List available models"""
    models = list_models()
    print("\nAvailable Models:")
    print("-" * 60)
    for m in models:
        active = "→" if m["active"] else " "
        specs = ", ".join(m["specialized_for"]) if m["specialized_for"] else "general"
        ctx = f"{m['context_window']//1024}k ctx"
        print(f" {active} {m['name']:<30} {ctx:<10} [{specs}]")
    print("-" * 60)
    print(f"\nActive model: {get_provider().active_model}")


def cmd_active():
    """Show active model"""
    provider = get_provider()
    print(f"Active model: {provider.active_model}")
    caps = provider.get_capabilities()
    print(f"  Context window: {caps.context_window}")
    print(f"  Specialized for: {', '.join(caps.specialized_for) or 'general'}")
    print(f"  Streaming: {caps.supports_streaming}")
    print(f"  JSON mode: {caps.supports_json_mode}")


def cmd_set(model: str):
    """Set active model"""
    try:
        set_active_model(model)
        print(f"✓ Active model set to: {model}")
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("\nAvailable models:")
        for m in list_models():
            print(f"  - {m['name']}")
        sys.exit(1)


def cmd_info(model: str):
    """Show model info"""
    provider = get_provider()
    caps = provider.get_capabilities(model)
    print(f"\nModel: {model}")
    print("-" * 40)
    print(f"Context window:     {caps.context_window:,} tokens")
    print(f"Streaming:          {caps.supports_streaming}")
    print(f"JSON mode:          {caps.supports_json_mode}")
    print(f"Function calling:   {caps.supports_function_calling}")
    print(f"Specialized for:    {', '.join(caps.specialized_for) or 'general'}")
    print(f"Cost tier:          {caps.cost_tier}")


def cmd_eval():
    """Run quick eval"""
    from eval_harness import EvalHarness
    harness = EvalHarness()
    summary = harness.run_eval(quick=True)
    
    print("\n" + "=" * 50)
    print(f"EVAL: {summary.model}")
    print("=" * 50)
    print(f"Pass rate: {summary.pass_rate*100:.1f}%")
    print(f"Avg score: {summary.avg_score:.2f}")
    print(f"Avg latency: {summary.avg_latency:.2f}s")


def cmd_compare():
    """Compare models"""
    from eval_harness import EvalHarness
    harness = EvalHarness()
    harness.compare_models()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        cmd_list()
    elif cmd == "active":
        cmd_active()
    elif cmd == "set" and len(sys.argv) > 2:
        cmd_set(sys.argv[2])
    elif cmd == "info" and len(sys.argv) > 2:
        cmd_info(sys.argv[2])
    elif cmd == "eval":
        cmd_eval()
    elif cmd == "compare":
        cmd_compare()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
