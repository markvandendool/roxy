#!/bin/bash
# Import n8n workflows for broadcasting automation

set -e

N8N_URL="http://localhost:5678"
WORKFLOWS_DIR="/opt/roxy/n8n-workflows"

echo "=== Importing n8n Workflows ==="
echo ""

# Check if n8n is running
if ! curl -s "${N8N_URL}/healthz" > /dev/null 2>&1; then
    echo "⚠️  n8n not accessible at ${N8N_URL}"
    echo "   Start it: docker compose -f /opt/roxy/compose/docker-compose.foundation.yml up -d roxy-n8n"
    exit 1
fi

echo "✅ n8n is running"
echo ""

# Check if workflows exist
if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo "⚠️  Workflows directory not found: $WORKFLOWS_DIR"
    echo "   Run: bash /opt/roxy/scripts/create-n8n-broadcast-workflows.sh"
    exit 1
fi

echo "Workflows to import:"
ls -1 "$WORKFLOWS_DIR"/*.json 2>/dev/null | while read workflow; do
    echo "  - $(basename $workflow)"
done

echo ""
echo "📝 Manual Import Instructions:"
echo ""
echo "1. Open n8n: http://localhost:5678"
echo "2. Click 'Workflows' → 'Import from File'"
echo "3. Import each workflow from: $WORKFLOWS_DIR"
echo ""
echo "Workflows:"
echo "  - auto-transcribe.json (Auto-transcribe recordings)"
echo "  - auto-extract-clips.json (Auto-extract clips from transcripts)"
echo "  - auto-encode.json (Auto-encode for platforms)"
echo ""
echo "After importing:"
echo "1. Configure API keys (YouTube, Discord, Telegram)"
echo "2. Update file paths if needed"
echo "3. Activate workflows"
echo "4. Test with sample files"

