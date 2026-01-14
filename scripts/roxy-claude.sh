#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# ROXY Claude Code CLI launcher with MCP integration

echo "🚀 Starting Claude Code CLI with ROXY MCP integration..."
echo ""
echo "✅ 32 ROXY tools available:"
echo "   • Desktop: 9 tools (screenshot, type, mouse, etc.)"
echo "   • Browser: 4 tools (browse, search, etc.)"
echo "   • Voice: 4 tools (speak, TTS, etc.)"
echo "   • OBS: 9 tools (recording, scenes, etc.)"
echo "   • Content: 6 tools (transcribe, clips, etc.)"
echo ""
echo "💡 Try commands like:"
echo "   • 'Take a screenshot'"
echo "   • 'Type Hello ROXY'"
echo "   • 'Start OBS recording'"
echo "   • 'Search the web for Python tutorials'"
echo ""
echo "─────────────────────────────────────────────────────────"
echo ""

claude --mcp-config ~/.config/claude/mcp.json "$@"