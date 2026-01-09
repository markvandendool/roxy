#!/bin/bash
# Deploy integration service configurations

echo '=== Deploying Integration Configs ==='

# Create integration config directory
mkdir -p /opt/roxy/integrations/config

# SmartLife/Tuya config template
cat > /opt/roxy/integrations/config/tuya.json << 'JSON'
{
    "api_region": "us",
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "devices": []
}
JSON
echo '✅ Created Tuya config template'

# Discord bot config template
cat > /opt/roxy/integrations/config/discord.json << 'JSON'
{
    "bot_token": "YOUR_DISCORD_BOT_TOKEN",
    "channel_id": "YOUR_CHANNEL_ID",
    "prefix": "!"
}
JSON
echo '✅ Created Discord config template'

# Telegram config template
cat > /opt/roxy/integrations/config/telegram.json << 'JSON'
{
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
}
JSON
echo '✅ Created Telegram config template'

# YouTube config template
cat > /opt/roxy/integrations/config/youtube.json << 'JSON'
{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "channel_id": "YOUR_CHANNEL_ID"
}
JSON
echo '✅ Created YouTube config template'

echo ''
echo 'Config templates created in /opt/roxy/integrations/config/'
echo 'Fill in API keys via Infisical or edit directly'
