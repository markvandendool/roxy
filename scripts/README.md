# Roxy Automation Scripts

## Quick Reference

| Script | Purpose | Command |
|--------|---------|---------|
| system-health-check.sh | Full system status | `/opt/roxy/scripts/system-health-check.sh` |
| test-voice-loop.sh | Test voice pipeline | `/opt/roxy/scripts/test-voice-loop.sh` |
| friday-inference-client.py | Send jobs to Friday | `python3 /opt/roxy/scripts/friday-inference-client.py "prompt"` |
| nats-job-publisher.py | NATS job queue | `python3 /opt/roxy/scripts/nats-job-publisher.py` |
| deploy-integrations.sh | Setup integration configs | `/opt/roxy/scripts/deploy-integrations.sh` |
| roxy-assistant.py | Voice assistant demo | `python3 /opt/roxy/voice/roxy-assistant.py` |

## Service Endpoints

| Service | URL | Port |
|---------|-----|------|
| n8n | http://10.0.0.69:5678 | 5678 |
| Home Assistant | http://10.0.0.69:8123 | 8123 |
| Ollama | http://10.0.0.69:11434 | 11434 |
| ChromaDB | http://10.0.0.69:8000 | 8000 |
| Friday Health | http://10.0.0.65:8765 | 8765 |

## Voice Stack

- **Wake Word**: hey_jarvis (OpenWakeWord)
- **STT**: Wyoming-Whisper
- **LLM**: Ollama (llama3.2:1b, qwen2.5-coder:14b)
- **TTS**: Wyoming-Piper (904 voices)

## Score: 92/100
