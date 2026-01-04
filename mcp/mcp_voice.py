#!/usr/bin/env python3
"""
MCP Voice Stack Bridge - Unified voice interaction control
Part of ROCKY-ROXY-ROCKIN-V1: Unified Command Center

Story: RRR-004
Sprint: 1
Points: 8

Voice Stack Components:
- Whisper STT: Port 10300
- Piper TTS: Port 10200
- OpenWakeWord: Port 10400

Exposes:
- voice_transcribe: Convert speech to text via Whisper
- voice_synthesize: Convert text to speech via Piper
- voice_set_wake_word: Configure wake word detection
- voice_get_status: Get voice stack health status
- voice_set_personality: Switch TTS voice/personality (Rocky vs ROXY)
- voice_listen: Start listening for voice input
"""

import json
import logging
import base64
from typing import Dict, Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("roxy.mcp.voice")

# Configuration
WHISPER_BASE = "http://localhost:10300"
PIPER_BASE = "http://localhost:10200"
OPENWAKEWORD_BASE = "http://localhost:10400"
TIMEOUT = 30  # Voice operations can be slow

# Voice personalities
PERSONALITIES = {
    "rocky": {
        "voice": "en_US-amy-medium",  # Friendly, warm
        "rate": 1.0,
        "pitch": 1.0,
        "description": "Rocky - Friendly music teacher"
    },
    "roxy": {
        "voice": "en_US-lessac-medium",  # Clear, technical
        "rate": 1.1,  # Slightly faster for dev work
        "pitch": 0.95,
        "description": "ROXY - Technical dev assistant"
    }
}

# Current personality state
_current_personality = "roxy"

TOOLS = {
    "voice_transcribe": {
        "description": "Convert speech audio to text using Whisper",
        "parameters": {
            "audio_base64": {"type": "string", "required": True, "description": "Base64-encoded audio data"},
            "language": {"type": "string", "default": "en", "description": "Language code"},
            "format": {"type": "string", "default": "wav", "description": "Audio format: wav|mp3|ogg"}
        }
    },
    "voice_synthesize": {
        "description": "Convert text to speech using Piper TTS",
        "parameters": {
            "text": {"type": "string", "required": True, "description": "Text to synthesize"},
            "personality": {"type": "string", "default": None, "description": "Voice personality: rocky|roxy (uses current if not specified)"},
            "output_format": {"type": "string", "default": "wav", "description": "Output format: wav|mp3"}
        }
    },
    "voice_set_wake_word": {
        "description": "Configure wake word detection settings",
        "parameters": {
            "wake_words": {"type": "array", "default": ["hey_rocky", "hey_roxy"], "description": "Wake words to listen for"},
            "sensitivity": {"type": "number", "default": 0.5, "description": "Detection sensitivity 0.0-1.0"}
        }
    },
    "voice_get_status": {
        "description": "Get status of all voice stack components",
        "parameters": {}
    },
    "voice_set_personality": {
        "description": "Switch TTS voice personality between Rocky and ROXY",
        "parameters": {
            "personality": {"type": "string", "required": True, "description": "Personality: rocky|roxy"}
        }
    },
    "voice_listen": {
        "description": "Start listening for voice input (returns when speech detected)",
        "parameters": {
            "timeout_seconds": {"type": "integer", "default": 10, "description": "Max listen duration"},
            "silence_threshold": {"type": "number", "default": 0.5, "description": "Silence detection threshold"}
        }
    }
}


def _http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP GET request"""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _http_post(url: str, data: Any, content_type: str = "application/json", timeout: int = TIMEOUT) -> Dict[str, Any]:
    """Make HTTP POST request"""
    try:
        if content_type == "application/json":
            body = json.dumps(data).encode()
        else:
            body = data if isinstance(data, bytes) else data.encode()
        
        req = Request(url, data=body, headers={
            "Content-Type": content_type,
            "Accept": "application/json"
        })
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _check_service(base_url: str, port: int = None) -> Dict[str, Any]:
    """Check if a voice service is available via Wyoming protocol"""
    import asyncio
    import socket
    
    # Extract port from URL if not provided
    if port is None:
        if "10300" in base_url:
            port = 10300
        elif "10200" in base_url:
            port = 10200
        elif "10400" in base_url:
            port = 10400
        else:
            return {"status": "down", "response": None, "error": "Unknown port"}
    
    async def _check():
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=3
            )
            writer.write(b'{"type":"describe"}\n')
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=3)
            writer.close()
            await writer.wait_closed()
            
            import json as json_mod
            data = json_mod.loads(response.decode())
            return {"status": "up", "response": data, "protocol": "wyoming"}
        except Exception as e:
            return {"status": "down", "response": None, "error": str(e)}
    
    try:
        return asyncio.run(_check())
    except RuntimeError:
        # Already in async context
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_check())


def handle_tool(name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Handle MCP tool call"""
    global _current_personality
    
    if params is None:
        params = {}
    
    try:
        if name == "voice_transcribe":
            audio_base64 = params.get("audio_base64")
            language = params.get("language", "en")
            audio_format = params.get("format", "wav")
            
            if not audio_base64:
                return {"error": "audio_base64 is required"}
            
            # Decode audio
            try:
                audio_bytes = base64.b64decode(audio_base64)
            except Exception as e:
                return {"error": f"Invalid base64 audio: {e}"}
            
            # Send to Whisper
            result = _http_post(
                f"{WHISPER_BASE}/transcribe",
                {
                    "audio": audio_base64,
                    "language": language,
                    "format": audio_format
                }
            )
            
            if "error" not in result:
                logger.info(f"Transcribed {len(audio_bytes)} bytes of audio")
            
            return {
                "transcription": result.get("text", ""),
                "language": result.get("language", language),
                "confidence": result.get("confidence", 0.0),
                "service": "whisper",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "voice_synthesize":
            text = params.get("text")
            personality = params.get("personality", _current_personality)
            output_format = params.get("output_format", "wav")
            
            if not text:
                return {"error": "text is required"}
            
            if personality not in PERSONALITIES:
                personality = _current_personality
            
            voice_config = PERSONALITIES[personality]
            
            # Send to Piper
            result = _http_post(
                f"{PIPER_BASE}/synthesize",
                {
                    "text": text,
                    "voice": voice_config["voice"],
                    "rate": voice_config["rate"],
                    "pitch": voice_config["pitch"],
                    "format": output_format
                }
            )
            
            if "error" not in result:
                logger.info(f"Synthesized '{text[:50]}...' with {personality} voice")
            
            return {
                "audio_base64": result.get("audio", ""),
                "format": output_format,
                "personality": personality,
                "voice": voice_config["voice"],
                "duration_ms": result.get("duration_ms", 0),
                "service": "piper",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "voice_set_wake_word":
            wake_words = params.get("wake_words", ["hey_rocky", "hey_roxy"])
            sensitivity = params.get("sensitivity", 0.5)
            
            result = _http_post(
                f"{OPENWAKEWORD_BASE}/configure",
                {
                    "wake_words": wake_words,
                    "sensitivity": sensitivity
                }
            )
            
            return {
                "wake_words": wake_words,
                "sensitivity": sensitivity,
                "configured": "error" not in result,
                "service": "openwakeword",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "voice_get_status":
            whisper_status = _check_service(WHISPER_BASE)
            piper_status = _check_service(PIPER_BASE)
            oww_status = _check_service(OPENWAKEWORD_BASE)
            
            all_up = all(s["status"] == "up" for s in [whisper_status, piper_status, oww_status])
            
            return {
                "overall_status": "healthy" if all_up else "degraded",
                "current_personality": _current_personality,
                "services": {
                    "whisper_stt": {
                        "url": WHISPER_BASE,
                        "port": 10300,
                        "status": whisper_status["status"]
                    },
                    "piper_tts": {
                        "url": PIPER_BASE,
                        "port": 10200,
                        "status": piper_status["status"]
                    },
                    "openwakeword": {
                        "url": OPENWAKEWORD_BASE,
                        "port": 10400,
                        "status": oww_status["status"]
                    }
                },
                "personalities": PERSONALITIES,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "voice_set_personality":
            personality = params.get("personality")
            
            if personality not in PERSONALITIES:
                return {
                    "error": f"Unknown personality: {personality}. Available: {list(PERSONALITIES.keys())}"
                }
            
            old_personality = _current_personality
            _current_personality = personality
            
            logger.info(f"Voice personality changed: {old_personality} -> {personality}")
            
            return {
                "previous": old_personality,
                "current": _current_personality,
                "voice_config": PERSONALITIES[personality],
                "greeting": f"Switched to {PERSONALITIES[personality]['description']}",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "voice_listen":
            timeout_seconds = params.get("timeout_seconds", 10)
            silence_threshold = params.get("silence_threshold", 0.5)
            
            # This would integrate with actual microphone capture
            # For now, return a status indicating listening mode
            result = _http_post(
                f"{WHISPER_BASE}/listen",
                {
                    "timeout": timeout_seconds,
                    "silence_threshold": silence_threshold
                },
                timeout=timeout_seconds + 5
            )
            
            return {
                "listening": True,
                "timeout_seconds": timeout_seconds,
                "silence_threshold": silence_threshold,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    """Bridge health check for infrastructure monitoring"""
    whisper = _check_service(WHISPER_BASE)
    piper = _check_service(PIPER_BASE)
    oww = _check_service(OPENWAKEWORD_BASE)
    
    healthy_count = sum(1 for s in [whisper, piper, oww] if s["status"] == "up")
    
    return {
        "bridge": "mcp_voice",
        "status": "healthy" if healthy_count == 3 else ("degraded" if healthy_count > 0 else "down"),
        "current_personality": _current_personality,
        "endpoints": {
            "whisper_stt": {"url": WHISPER_BASE, "port": 10300, "status": whisper["status"]},
            "piper_tts": {"url": PIPER_BASE, "port": 10200, "status": piper["status"]},
            "openwakeword": {"url": OPENWAKEWORD_BASE, "port": 10400, "status": oww["status"]}
        },
        "services_up": healthy_count,
        "services_total": 3,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    print("MCP Voice Bridge - Health Check")
    print(json.dumps(health_check(), indent=2))
