# OpenCode Bridge Runbook

## Purpose

Use ROXY to delegate coding/reasoning work to OpenCode cloud models, then ingest output back into ROXY responses.

This bridge is implemented in:
- `tools/streaming_tools.py` (`opencode` tool)
- `roxy_core.py` (`<<opencode>>...<</opencode>>` tool-call support)

## Default Model

ROXY defaults to:
- `opencode/mimo-v2-pro-free`
- `mode=primary` (ULTRAMAX profile)

Override with:
```bash
export ROXY_OPENCODE_MODEL="opencode/mimo-v2-pro-free"
export ROXY_OPENCODE_PROFILE="primary"
export ROXY_OPENCODE_ULTRAMAX=1
export ROXY_OPENCODE_BOOTSTRAP=1
export ROXY_OPENCODE_FREE_FALLBACK=1
```

## Quick Health Checks

```bash
opencode-cli providers list
opencode-cli models --verbose | head -n 60
opencode-cli run --format json --model opencode/mimo-v2-pro-free "Reply with exactly: OPENCODE_OK"
```

Expected output includes a JSON event with text `OPENCODE_OK`.

## Command Center Usage

### 1) Single-shot OpenCode call

In ROXY prompt:
```text
<<opencode>>Analyze the current repo and list 5 highest-risk regressions.<</opencode>>
```

Equivalent JSON tool payload:
```json
{
  "tool": "opencode",
  "args": {
    "action": "run",
    "mode": "primary",
    "prompt": "Analyze current repo and list 5 highest-risk regressions."
  }
}
```

### 2) Multi-step chain (reprompt loop)

Use chained mode to run iterative steps where each output becomes the next prompt context:
```json
{
  "tool": "opencode_chain",
  "args": {
    "action": "chain",
    "mode": "reasoning",
    "prompt": "Plan and implement a safe refactor for memory retrieval; output COMPLETE: <summary> when done.",
    "chain_steps": 3,
    "chain_stop_prefix": "COMPLETE:"
  }
}
```

CLI equivalent:
```bash
cd ~/.roxy
./venv/bin/python scripts/opencode_feedback_loop.py \
  --prompt "Plan and implement memory retrieval hardening. Output COMPLETE: <summary> when done." \
  --steps 3 \
  --mode reasoning \
  --output-json ~/.roxy/briefings/opencode-loop-latest.json
```

### 3) ULTRAMAX launcher from shell

```bash
~/.local/bin/opencode-ultramax list
~/.local/bin/opencode-ultramax primary "Audit this repo and produce a prioritized patch plan."
~/.local/bin/opencode-ultramax reasoning "Root-cause this flaky test and propose fixes."
```

Modes:
- `primary` -> `opencode/mimo-v2-pro-free`
- `reasoning` -> `opencode/big-pickle`
- `fast` -> `opencode/gpt-5-nano`
- `bigbrain` -> `opencode/nemotron-3-super-free`
- `architect` -> `opencode/mimo-v2-omni-free`
- `free` -> `opencode/minimax-m2.5-free`
- `max` -> `openai/gpt-5.4`
- `codexmax` -> `openai/gpt-5.1-codex-max`
- `copilot` / `gmodels` -> provider-backed models (fallback to free chain if locked/quota)

## Tool Arguments

`action=run` supports:
- `prompt` (required)
- `mode` (`primary|reasoning|fast|bigbrain|architect|free|max|codexmax|copilot|gmodels`)
- `model`
- `agent`
- `variant`
- `thinking` (bool)
- `files` (array of file paths)
- `timeout` (seconds)
- `dir` (working directory)
- `attach_url`, `password`, `session`, `continue_session`, `fork`
- `ultramax` (bool; profile-level defaults)
- `bootstrap` (bool; inject Luno/SKOREQ/skills onboarding context)
- `fallback_free` (bool; auto-fallback on provider auth/quota locks)

`action=chain` supports:
- all `run` args +
- `chain_steps` (1-8)
- `chain_followup_template`
- `chain_stop_prefix` (default `COMPLETE:`)
- `chain_max_output_chars`

`action=models` supports:
- `provider`
- `verbose`
- `refresh`

`action=providers`:
- lists configured providers and credentials status.

## Troubleshooting

If you see:
- `403 ... account has locked billing`:
  - Your current provider/model is blocked.
  - ROXY now auto-retries with free fallback chain:
    - `opencode/mimo-v2-pro-free`
    - `opencode/nemotron-3-super-free`
    - `opencode/minimax-m2.5-free`
    - `opencode/gpt-5-nano`
  - To disable fallback for debugging, set `fallback_free=false`.

If command times out:
- Increase timeout:
```json
{"tool":"opencode","args":{"action":"run","prompt":"...","timeout":240}}
```

If `opencode-cli not found`:
- Ensure `/usr/bin/opencode-cli` exists and is executable.
