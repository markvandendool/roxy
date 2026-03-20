import asyncio
from pathlib import Path

import pytest

from tools.streaming_tools import StreamingTools


def test_get_profile_defaults_to_primary():
    profile = StreamingTools._get_profile("not-a-real-mode")
    assert profile["model"] == "opencode/mimo-v2-pro-free"
    assert profile["variant"] == "high"


def test_build_fallback_model_chain_dedupes_primary():
    chain = StreamingTools._build_fallback_model_chain("opencode/minimax-m2.5-free")
    assert chain[0] == "opencode/minimax-m2.5-free"
    assert len(chain) == len(set(chain))
    assert "opencode/mimo-v2-pro-free" in chain


def test_should_use_free_fallback_for_provider_lock_errors():
    assert StreamingTools._should_use_free_fallback("Status code 403: locked billing for provider")
    assert StreamingTools._should_use_free_fallback("insufficient_quota")
    assert not StreamingTools._should_use_free_fallback("syntax error in generated patch")


def test_build_spawn_boost_context_uses_bootstrap_files(monkeypatch, tmp_path: Path):
    onboarding = tmp_path / "START_HERE.md"
    plan = tmp_path / "00_PLAN.md"
    onboarding.write_text("# START\nLuno orchestrator onboarding content", encoding="utf-8")
    plan.write_text("# PLAN\nSKOREQ execution priorities", encoding="utf-8")

    monkeypatch.setenv("ROXY_OPENCODE_BOOTSTRAP_FILES", f"{onboarding},{plan}")

    tools = StreamingTools(workdir=str(tmp_path))
    context = tools._build_spawn_boost_context(max_chars=1200)
    assert "ULTRAMAX SPAWN BRIEFING" in context
    assert "START_HERE.md" in context
    assert "00_PLAN.md" in context
    assert "SKOREQ" in context


class _FakeProc:
    def __init__(self, returncode: int, stdout: str, stderr: str = ""):
        self.returncode = returncode
        self._stdout = stdout.encode("utf-8")
        self._stderr = stderr.encode("utf-8")

    async def communicate(self):
        await asyncio.sleep(0)
        return self._stdout, self._stderr

    def kill(self):
        return None


@pytest.mark.asyncio
async def test_opencode_run_fallbacks_to_free_model(monkeypatch, tmp_path: Path):
    tools = StreamingTools(workdir=str(tmp_path))
    commands = []
    calls = [
        _FakeProc(
            returncode=1,
            stdout='{"type":"error","error":{"message":"Status code 403: locked billing"}}\n',
            stderr="locked billing",
        ),
        _FakeProc(
            returncode=0,
            stdout='{"type":"text","part":{"text":"fallback-success"}}\n{"type":"step_finish","part":{"reason":"stop","tokens":{"input":1,"output":1}}}\n',
        ),
    ]

    async def fake_create_subprocess_exec(*cmd, **_kwargs):
        commands.append(list(cmd))
        return calls.pop(0)

    monkeypatch.setattr("tools.streaming_tools.shutil.which", lambda _: "/usr/bin/opencode-cli")
    monkeypatch.setattr("tools.streaming_tools.asyncio.create_subprocess_exec", fake_create_subprocess_exec)

    result = await tools.opencode(
        action="run",
        mode="gmodels",
        prompt="Return fallback success",
        fallback_free=True,
        bootstrap=False,
    )

    assert result.success is True
    assert "fallback-success" in str(result.data)
    assert len(commands) == 2
    assert "github-models/deepseek/deepseek-r1-0528" in commands[0]
    assert "opencode/mimo-v2-pro-free" in commands[1]
    assert result.metadata["model"] == "opencode/mimo-v2-pro-free"
    assert result.metadata["attempt"] == 2
    assert len(result.metadata["attempt_failures"]) == 1


@pytest.mark.asyncio
async def test_opencode_bootstrap_injected_into_prompt(monkeypatch, tmp_path: Path):
    briefing = tmp_path / "START_HERE.md"
    briefing.write_text("Luno onboarding rules", encoding="utf-8")
    monkeypatch.setenv("ROXY_OPENCODE_BOOTSTRAP_FILES", str(briefing))

    tools = StreamingTools(workdir=str(tmp_path))
    commands = []

    async def fake_create_subprocess_exec(*cmd, **_kwargs):
        commands.append(list(cmd))
        return _FakeProc(
            returncode=0,
            stdout='{"type":"text","part":{"text":"ok"}}\n{"type":"step_finish","part":{"reason":"stop","tokens":{}}}\n',
        )

    monkeypatch.setattr("tools.streaming_tools.shutil.which", lambda _: "/usr/bin/opencode-cli")
    monkeypatch.setattr("tools.streaming_tools.asyncio.create_subprocess_exec", fake_create_subprocess_exec)

    result = await tools.opencode(
        action="run",
        mode="primary",
        prompt="Summarize infra health",
        bootstrap=True,
        fallback_free=False,
    )

    assert result.success is True
    assert commands
    sent_prompt = commands[0][-1]
    assert "ULTRAMAX SPAWN BRIEFING" in sent_prompt
    assert "Luno onboarding rules" in sent_prompt
    assert "USER TASK" in sent_prompt
