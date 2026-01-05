# Roxy ↔ Home Assistant Integration

## Quick Setup

### 1. Get Your Long-Lived Access Token
1. Open http://localhost:8123
2. Click your profile (bottom-left)
3. Scroll to "Long-Lived Access Tokens"
4. Create token named "roxy"
5. Save token to `~/.roxy/ha-integration/.env`

### 2. SmartLife/Tuya Setup
```bash
cd ~/.roxy && source venv/bin/activate
python3 -m tinytuya wizard
```

### 3. Test Connection
```bash
./test-ha.sh
```

## Files
- `ha-control.py` - Control HA entities
- `tuya-bridge.py` - Bridge TinyTuya to HA
- `.env` - Credentials (gitignored)
