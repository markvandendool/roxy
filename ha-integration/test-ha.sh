#!/bin/bash
# Test Home Assistant connection

source "$(dirname "$0")/../venv/bin/activate"

if [ ! -f "$(dirname "$0")/.env" ]; then
    echo "❌ No .env file found!"
    echo ""
    echo "Create ~/.roxy/ha-integration/.env with:"
    echo "  HA_URL=http://localhost:8123"
    echo "  HA_TOKEN=your_long_lived_access_token"
    echo ""
    echo "Get token from: http://localhost:8123/profile → Long-Lived Access Tokens"
    exit 1
fi

source "$(dirname "$0")/.env"

echo "🏠 Testing Home Assistant connection..."
echo "   URL: $HA_URL"

response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    "$HA_URL/api/")

if [ "$response" = "200" ]; then
    echo "✅ Connected successfully!"
    echo ""
    echo "📋 Entity summary:"
    python3 "$(dirname "$0")/ha-control.py" list | head -20
else
    echo "❌ Connection failed (HTTP $response)"
    if [ "$response" = "401" ]; then
        echo "   → Invalid or expired token"
    elif [ "$response" = "000" ]; then
        echo "   → Cannot reach Home Assistant"
    fi
fi
