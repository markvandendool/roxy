#!/bin/bash
# Setup Claude Desktop to use ROXY MCP servers

echo "🔧 Setting up Claude Desktop integration for ROXY..."

# Find Claude Desktop config location
CLAUDE_CONFIG_DIRS=(
    "$HOME/.config/claude"
    "$HOME/.config/Claude"
    "$HOME/.config/claude-desktop"
    "$HOME/.config/Claude Desktop"
)

ROXY_CONFIG="/opt/roxy/config/claude-mcp.json"
CLAUDE_CONFIG_FILE=""

# Find existing config or create new location
for dir in "${CLAUDE_CONFIG_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        CLAUDE_CONFIG_FILE="$dir/mcp.json"
        echo "✅ Found Claude config directory: $dir"
        break
    fi
done

# If not found, use first location
if [ -z "$CLAUDE_CONFIG_FILE" ]; then
    CLAUDE_CONFIG_FILE="${CLAUDE_CONFIG_DIRS[0]}/mcp.json"
    mkdir -p "$(dirname "$CLAUDE_CONFIG_FILE")"
    echo "📁 Created config directory: $(dirname "$CLAUDE_CONFIG_FILE")"
fi

# Copy ROXY config
if [ -f "$ROXY_CONFIG" ]; then
    cp "$ROXY_CONFIG" "$CLAUDE_CONFIG_FILE"
    echo "✅ Copied ROXY MCP config to: $CLAUDE_CONFIG_FILE"
    echo ""
    echo "📋 ROXY MCP Servers configured:"
    echo "   • roxy-desktop (9 tools)"
    echo "   • roxy-browser (4 tools)"
    echo "   • roxy-voice (4 tools)"
    echo "   • roxy-obs (9 tools)"
    echo "   • roxy-content (6 tools)"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Restart Claude Desktop"
    echo "   2. Open Claude Desktop"
    echo "   3. Start chatting - ROXY tools will be available!"
    echo ""
    echo "💡 Try commands like:"
    echo "   • 'Take a screenshot'"
    echo "   • 'Type Hello ROXY'"
    echo "   • 'Press Ctrl+Alt+T'"
    echo "   • 'Start OBS recording'"
else
    echo "❌ Error: ROXY config not found at $ROXY_CONFIG"
    exit 1
fi
















