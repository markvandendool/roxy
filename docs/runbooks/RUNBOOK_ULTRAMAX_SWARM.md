# ROXY ULTRAMAX Swarm Runbook

## Objective

Maximize per-spawn agent quality by combining:
- strongest available OpenCode models
- deterministic fallback on provider lock/quota errors
- startup context injection from Luno/SKOREQ/onboarding docs
- command-center chain loops with stop conditions

## Verified Models On This Host

Validated on 2026-03-20 with `opencode-cli run --format json ...`:

- `opencode/mimo-v2-pro-free` (OK)
- `opencode/big-pickle` (OK)
- `opencode/nemotron-3-super-free` (OK)
- `opencode/mimo-v2-omni-free` (OK)
- `opencode/minimax-m2.5-free` (OK)
- `opencode/gpt-5-nano` (OK)
- `openai/gpt-5.4` (OK)
- `openai/gpt-5.3-codex` (OK)
- `openai/gpt-5.2-codex` (OK)
- `openai/gpt-5.1-codex-max` (OK)

Known restricted/locked in current credentials:
- `github-models/deepseek/deepseek-r1-0528` (locked billing)
- `github-copilot/claude-opus-4.6` (requested model not supported in current provider context)

## ULTRAMAX Profile Map

ROXY `opencode` tool supports these modes:

- `primary` -> `opencode/mimo-v2-pro-free`
- `reasoning` -> `opencode/big-pickle`
- `fast` -> `opencode/gpt-5-nano`
- `bigbrain` -> `opencode/nemotron-3-super-free`
- `architect` -> `opencode/mimo-v2-omni-free`
- `free` -> `opencode/minimax-m2.5-free`
- `max` -> `openai/gpt-5.4`
- `codexmax` -> `openai/gpt-5.1-codex-max`
- `copilot` -> `github-copilot/claude-opus-4.6` (optional/provider-dependent)
- `gmodels` -> `github-models/deepseek/deepseek-r1-0528` (optional/provider-dependent)

Fallback chain on provider lock/quota:

1. `opencode/mimo-v2-pro-free`
2. `opencode/nemotron-3-super-free`
3. `opencode/minimax-m2.5-free`
4. `opencode/gpt-5-nano`

## Spawn Bootstrap Context

When `bootstrap=true`, ROXY prepends condensed context from:

- `~/.roxy/ROXY_IDENTITY.md`
- `~/.roxy/docs/ROXY_STATUS_DOCTRINE.md`
- `~/.roxy/docs/ROXY_RUNBOOK_CORE.md`
- `~/.roxy/docs/docs/onboarding/START_HERE.md`
- `~/.roxy/docs/docs/brain/INDEX.md`
- `~/.roxy/docs/skoreq/**/00_PLAN.md` (first 4)
- latest qualification summary from `~/.roxy/briefings/qualification-day4-day7-*.json`

Override file list:

```bash
export ROXY_OPENCODE_BOOTSTRAP_FILES="/path/a.md,/path/b.md"
```

## Required Environment Defaults

```bash
export ROXY_OPENCODE_PROFILE="primary"
export ROXY_OPENCODE_ULTRAMAX=1
export ROXY_OPENCODE_BOOTSTRAP=1
export ROXY_OPENCODE_FREE_FALLBACK=1
export ROXY_OPENCODE_DEFAULT_VARIANT="high"
export ROXY_OPENCODE_TIMEOUT_SEC=180
export ROXY_OPENCODE_CHAIN_MAX_STEPS=8
```

## Command Center Patterns

Single-shot:

```json
{
  "tool": "opencode",
  "args": {
    "action": "run",
    "mode": "max",
    "prompt": "Audit this diff and provide a high-risk regression checklist.",
    "bootstrap": true,
    "fallback_free": true
  }
}
```

Chain loop:

```json
{
  "tool": "opencode_chain",
  "args": {
    "action": "chain",
    "mode": "reasoning",
    "prompt": "Implement the failing test fix and output COMPLETE: <summary> when done.",
    "chain_steps": 4,
    "chain_stop_prefix": "COMPLETE:",
    "bootstrap": true,
    "fallback_free": true
  }
}
```

## Operator Commands

List ULTRAMAX modes:

```bash
~/.local/bin/opencode-ultramax list
```

Run with free-first resilience:

```bash
~/.local/bin/opencode-ultramax gmodels "Reply with exactly: FALLBACK_OK"
```

Run command-center loop:

```bash
cd ~/.roxy
./venv/bin/python scripts/opencode_feedback_loop.py \
  --mode reasoning \
  --prompt "Output COMPLETE: LOOP_OK" \
  --steps 1 \
  --output-json ~/.roxy/briefings/opencode-loop-latest.json
```

## Success Criteria

- `opencode` tool metadata shows `attempt` and `attempt_failures`.
- Locked provider attempts auto-fallback to free chain and still return output.
- Bootstrap prompt includes Luno/SKOREQ material in first attempt.
- Eval harness remains >= 95% pass after changes.
