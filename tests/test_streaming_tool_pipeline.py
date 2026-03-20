import roxy_core


def test_extract_stream_tool_calls_tagged_bash():
    text = "<<bash>>ls -la /home/mark/.roxy<</bash>>"
    calls = roxy_core._extract_stream_tool_calls(text)
    assert calls
    assert calls[0]["name"] == "bash"
    assert "ls -la" in calls[0]["arguments"]["command"]


def test_extract_stream_tool_calls_tagged_opencode():
    text = "<<opencode>>Analyze this repo and propose 3 refactors<</opencode>>"
    calls = roxy_core._extract_stream_tool_calls(text)
    assert calls
    assert calls[0]["name"] == "opencode"
    assert "propose 3 refactors" in calls[0]["arguments"]["prompt"]


def test_extract_stream_tool_calls_fenced_json_alias():
    text = """```json
{
  "tool": "read_file",
  "args": {
    "file_path": "README.md",
    "offset": 1,
    "limit": 10
  }
}
```"""
    calls = roxy_core._extract_stream_tool_calls(text)
    assert calls
    assert calls[0]["name"] == "read"
    assert calls[0]["arguments"]["file_path"] == "README.md"


def test_extract_stream_tool_calls_opencode_alias():
    text = """```json
{
  "tool": "opencode_chain",
  "args": {
    "prompt": "Fix failing tests",
    "action": "chain",
    "chain_steps": 2
  }
}
```"""
    calls = roxy_core._extract_stream_tool_calls(text)
    assert calls
    assert calls[0]["name"] == "opencode"
    assert calls[0]["arguments"]["action"] == "chain"


def test_pre_tool_use_policy_blocks_dangerous_bash():
    verdict = roxy_core._pre_tool_use_policy("bash", {"command": "rm -rf /"})
    assert verdict["allow"] is False
    assert "blocked_pattern" in verdict["reason"]


def test_pre_tool_use_policy_allows_safe_read():
    verdict = roxy_core._pre_tool_use_policy("read", {"file_path": "/home/mark/.roxy/README.md"})
    assert verdict["allow"] is True


def test_pre_tool_use_policy_blocks_write_outside_roots():
    verdict = roxy_core._pre_tool_use_policy("write", {"file_path": "/etc/hosts", "content": "x"})
    assert verdict["allow"] is False
    assert verdict["reason"] in {"path_outside_allowed_roots", "path_resolution_failed"}


def test_pre_tool_use_policy_blocks_empty_opencode_prompt():
    verdict = roxy_core._pre_tool_use_policy("opencode", {})
    assert verdict["allow"] is False
    assert verdict["reason"] == "missing_prompt"


def test_pre_tool_use_policy_allows_opencode_models_action_without_prompt():
    verdict = roxy_core._pre_tool_use_policy("opencode", {"action": "models"})
    assert verdict["allow"] is True
    assert verdict["safety_level"] == "guarded"
