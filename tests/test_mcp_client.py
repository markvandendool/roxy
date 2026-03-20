import json
from pathlib import Path

from mcp_client import MCPClient


def test_expand_env_template_supports_defaults(monkeypatch):
    monkeypatch.setenv("ROXY_TEST_ENV", "present-value")

    assert MCPClient._expand_env_template("${ROXY_TEST_ENV:-fallback}") == "present-value"
    assert MCPClient._expand_env_template("${ROXY_MISSING_ENV:-fallback-value}") == "fallback-value"


def test_load_configs_merges_and_expands(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", "/tmp/roxy-project")
    monkeypatch.setenv("PYTHON_BIN", "python3")

    config_primary = tmp_path / "primary.json"
    config_secondary = tmp_path / "secondary.json"

    config_primary.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "server_a": {
                        "command": "${PYTHON_BIN:-python}",
                        "args": ["${PROJECT_ROOT:-/fallback}/server_a.py"],
                        "env": {"ROOT": "${PROJECT_ROOT:-/fallback}"},
                        "url": "http://example.com/${PROJECT_ROOT:-fallback}",
                    }
                }
            }
        )
    )

    config_secondary.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "server_a": {
                        "command": "SHOULD_NOT_OVERRIDE",
                        "args": ["ignored.py"],
                    },
                    "server_b": {
                        "command": "node",
                        "args": ["server_b.js"],
                    },
                }
            }
        )
    )

    client = MCPClient(config_path=str(config_primary))
    client.config_paths = [str(config_primary), str(config_secondary)]
    configs = client._load_configs()
    by_name = {cfg.name: cfg for cfg in configs}

    assert {"server_a", "server_b"} <= set(by_name)
    assert by_name["server_a"].command.endswith("/venv/bin/python")
    assert by_name["server_a"].args == ["/tmp/roxy-project/server_a.py"]
    assert by_name["server_a"].env["ROOT"] == "/tmp/roxy-project"
    assert by_name["server_a"].command != "SHOULD_NOT_OVERRIDE"


def test_stdio_message_parsing_supports_content_length():
    payload = {"jsonrpc": "2.0", "id": 7, "result": {"ok": True}}
    encoded = MCPClient._encode_stdio_framed_message(payload)

    parsed, rest = MCPClient._try_parse_buffered_message(encoded, "test-server")

    assert parsed == payload
    assert rest == b""


def test_stdio_line_encoder_outputs_json_line():
    payload = {"jsonrpc": "2.0", "id": 9, "method": "ping"}
    encoded = MCPClient._encode_stdio_line_message(payload)

    assert encoded.endswith(b"\n")
    assert b"Content-Length" not in encoded


def test_stdio_message_parsing_supports_newline_fallback():
    buffer = b"not-json\n{\"jsonrpc\":\"2.0\",\"id\":2,\"result\":{\"ok\":1}}\n"

    first, remaining = MCPClient._try_parse_buffered_message(buffer, "test-server")
    second, tail = MCPClient._try_parse_buffered_message(remaining, "test-server")

    assert first is None
    assert isinstance(second, dict)
    assert second.get("id") == 2
    assert tail == b""
