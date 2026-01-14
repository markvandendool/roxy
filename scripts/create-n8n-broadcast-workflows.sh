#!/bin/bash
# Create n8n workflows for broadcasting automation

set -e

ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"

echo "=== Creating n8n Broadcast Workflows ==="
echo ""

N8N_URL="http://localhost:5678"
WORKFLOWS_DIR="$ROXY_ROOT/n8n-workflows"

mkdir -p "$WORKFLOWS_DIR"

# Workflow 1: Auto-Transcribe on Recording Complete
cat > "$WORKFLOWS_DIR/auto-transcribe.json" << 'EOF'
{
  "name": "Auto-Transcribe Recording",
  "nodes": [
    {
      "parameters": {
        "path": "${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/recordings",
        "options": {
          "fileExtension": ".mp4,.mkv"
        }
      },
      "name": "Watch for New Recording",
      "type": "n8n-nodes-base.watchFile",
      "position": [250, 300]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/whisperx_transcriber.py {{ $json.path }} ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/transcripts/",
        "options": {}
      },
      "name": "Run WhisperX",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 300]
    },
    {
      "parameters": {
        "operation": "create",
        "resource": "collection",
        "collectionName": "transcripts",
        "properties": {
          "recording_path": "={{ $json.path }}",
          "transcript_path": "={{ $json.output }}",
          "timestamp": "={{ $now }}"
        }
      },
      "name": "Store in ChromaDB",
      "type": "n8n-nodes-base.chromadb",
      "position": [650, 300]
    }
  ],
  "connections": {
    "Watch for New Recording": {
      "main": [[{"node": "Run WhisperX", "type": "main", "index": 0}]]
    },
    "Run WhisperX": {
      "main": [[{"node": "Store in ChromaDB", "type": "main", "index": 0}]]
    }
  }
}
EOF

# Workflow 2: Auto-Extract Clips
cat > "$WORKFLOWS_DIR/auto-extract-clips.json" << 'EOF'
{
  "name": "Auto-Extract Clips",
  "nodes": [
    {
      "parameters": {
        "path": "${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/transcripts",
        "options": {
          "fileExtension": ".json"
        }
      },
      "name": "Watch for Transcript",
      "type": "n8n-nodes-base.watchFile",
      "position": [250, 300]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/clip_extractor.py --input {{ $json.recording_path }} --transcript {{ $json.path }} --output ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/clips/ --platform all",
        "options": {}
      },
      "name": "Extract Clips",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 300]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/viral_detector.py --input ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/clips/ --transcript {{ $json.path }}",
        "options": {}
      },
      "name": "Score Clips",
      "type": "n8n-nodes-base.executeCommand",
      "position": [650, 300]
    }
  ],
  "connections": {
    "Watch for Transcript": {
      "main": [[{"node": "Extract Clips", "type": "main", "index": 0}]]
    },
    "Extract Clips": {
      "main": [[{"node": "Score Clips", "type": "main", "index": 0}]]
    }
  }
}
EOF

# Workflow 3: Auto-Encode for Platforms
cat > "$WORKFLOWS_DIR/auto-encode.json" << 'EOF'
{
  "name": "Auto-Encode for Platforms",
  "nodes": [
    {
      "parameters": {
        "path": "${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/clips",
        "options": {
          "fileExtension": ".mp4"
        }
      },
      "name": "Watch for Clips",
      "type": "n8n-nodes-base.watchFile",
      "position": [250, 300]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/encoding_presets.py --input {{ $json.path }} --platform tiktok --output ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/encoded/tiktok/",
        "options": {}
      },
      "name": "Encode TikTok",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 200]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/encoding_presets.py --input {{ $json.path }} --platform youtube-shorts --output ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/encoded/youtube-shorts/",
        "options": {}
      },
      "name": "Encode YouTube Shorts",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 300]
    },
    {
      "parameters": {
        "command": "cd ${ROXY_ROOT:-$HOME/.roxy} && source venv/bin/activate && python content-pipeline/encoding_presets.py --input {{ $json.path }} --platform instagram-reels --output ${ROXY_ROOT:-$HOME/.roxy}/content-pipeline/encoded/instagram-reels/",
        "options": {}
      },
      "name": "Encode Instagram",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 400]
    }
  ],
  "connections": {
    "Watch for Clips": {
      "main": [[
        {"node": "Encode TikTok", "type": "main", "index": 0},
        {"node": "Encode YouTube Shorts", "type": "main", "index": 0},
        {"node": "Encode Instagram", "type": "main", "index": 0}
      ]]
    }
  }
}
EOF

echo "✅ n8n workflows created in $WORKFLOWS_DIR"
echo ""
echo "To import workflows:"
echo "1. Open n8n: http://localhost:5678"
echo "2. Import workflow from: $WORKFLOWS_DIR"
echo "3. Configure API keys and paths"
echo "4. Activate workflows"


# Replace legacy root paths in generated workflows
if [ -d "$WORKFLOWS_DIR" ]; then
  sed -i "s|${ROXY_ROOT:-$HOME/.roxy}|$ROXY_ROOT|g" "$WORKFLOWS_DIR"/*.json 2>/dev/null || true
fi
