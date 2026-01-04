#!/usr/bin/env python3
"""
Voice Integration Bridge - Realtime Voice → MCP Router
Part of ROCKY-ROXY-ROCKIN-V1: Sprint 2 - UI Integration

Story: RRR-009

Connects the voice stack (Whisper, Piper, OpenWakeWord) to the
Unified Command Center via MCP tools.

Flow:
1. OpenWakeWord detects "Hey Rocky" or "Hey ROXY"
2. Whisper transcribes the command
3. Command routed to appropriate MCP tool
4. Response synthesized via Piper
"""

import asyncio
import json
import aiohttp
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice_integration")

# Service endpoints
WHISPER_URL = "http://127.0.0.1:10300"
PIPER_URL = "http://127.0.0.1:10200"
WAKE_WORD_URL = "http://127.0.0.1:10400"
MCP_URL = "http://127.0.0.1:8766"

class PersonaMode(Enum):
    ROXY = "engineering"  # Dev assistant
    ROCKY = "business"    # Music teacher

@dataclass
class VoiceConfig:
    """Voice configuration for each persona"""
    persona: PersonaMode
    voice_id: str
    wake_words: list[str]
    greeting: str
    
PERSONA_CONFIGS = {
    PersonaMode.ROXY: VoiceConfig(
        persona=PersonaMode.ROXY,
        voice_id="en_US-lessac-medium",
        wake_words=["hey roxy", "okay roxy", "yo roxy"],
        greeting="ROXY online. Ready to assist with development."
    ),
    PersonaMode.ROCKY: VoiceConfig(
        persona=PersonaMode.ROCKY,
        voice_id="en_US-amy-medium",
        wake_words=["hey rocky", "okay rocky", "yo rocky"],
        greeting="Hey there! Rocky here, your music buddy."
    )
}

# Dual wake-word map for simultaneous detection
ALL_WAKE_WORDS = {
    "hey roxy": PersonaMode.ROXY,
    "okay roxy": PersonaMode.ROXY,
    "yo roxy": PersonaMode.ROXY,
    "hey rocky": PersonaMode.ROCKY,
    "okay rocky": PersonaMode.ROCKY,
    "yo rocky": PersonaMode.ROCKY,
}

ENABLE_AUTO_PERSONA_ROUTING = True

class VoiceIntegration:
    """
    Main voice integration class that bridges:
    - Wake word detection → Command listening
    - STT (Whisper) → Command parsing
    - Command routing → MCP tools
    - Response → TTS (Piper)
    """
    
    def __init__(self, initial_mode: PersonaMode = PersonaMode.ROXY):
        self.mode = initial_mode
        self.config = PERSONA_CONFIGS[initial_mode]
        self.is_listening = False
        self.is_processing = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._command_handlers: Dict[str, Callable] = {}
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
            
    @property
    def session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = aiohttp.ClientSession()
        return self._session
    
    # ─────────────────────────────────────────────────────────────
    # Mode Management
    # ─────────────────────────────────────────────────────────────
    
    def set_mode(self, mode: PersonaMode):
        """Switch between ROXY and Rocky personas"""
        self.mode = mode
        self.config = PERSONA_CONFIGS[mode]
        logger.info(f"[VoiceIntegration] Switched to {mode.name} mode")
        
    def toggle_mode(self) -> PersonaMode:
        """Toggle between modes"""
        new_mode = PersonaMode.ROCKY if self.mode == PersonaMode.ROXY else PersonaMode.ROXY
        self.set_mode(new_mode)
        return new_mode
    
    # ─────────────────────────────────────────────────────────────
    # Service Health Checks
    # ─────────────────────────────────────────────────────────────
    
    async def check_services(self) -> Dict[str, bool]:
        """Check health of all voice services"""
        status = {
            "whisper": False,
            "piper": False,
            "wake_word": False,
            "mcp": False
        }
        
        checks = [
            ("whisper", f"{WHISPER_URL}/health"),
            ("piper", f"{PIPER_URL}/health"),
            ("wake_word", f"{WAKE_WORD_URL}/health"),
            ("mcp", f"{MCP_URL}/health"),
        ]
        
        for service, url in checks:
            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    status[service] = resp.status == 200
            except Exception:
                status[service] = False
                
        return status
    
    # ─────────────────────────────────────────────────────────────
    # Speech-to-Text (Whisper)
    # ─────────────────────────────────────────────────────────────
    
    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using Whisper via MCP bridge"""
        try:
            # Try MCP bridge first
            form = aiohttp.FormData()
            form.add_field('audio', audio_data, filename='recording.wav', content_type='audio/wav')
            
            async with self.session.post(
                f"{MCP_URL}/mcp/voice/transcribe",
                data=form,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("text", "")
                    
            # Fallback to direct Whisper
            async with self.session.post(
                f"{WHISPER_URL}/transcribe",
                data=form,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("text", "")
                    
        except Exception as e:
            logger.error(f"[VoiceIntegration] Transcription failed: {e}")
            
        return None
    
    # ─────────────────────────────────────────────────────────────
    # Text-to-Speech (Piper)
    # ─────────────────────────────────────────────────────────────
    
    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
        """Synthesize text to speech using Piper via MCP bridge"""
        try:
            voice = voice_id or self.config.voice_id
            
            # Try MCP bridge first
            async with self.session.post(
                f"{MCP_URL}/mcp/voice/synthesize",
                json={"text": text, "voice_id": voice},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                    
            # Fallback to direct Piper
            async with self.session.post(
                f"{PIPER_URL}/synthesize",
                json={"text": text, "voice": voice},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.read()
                    
        except Exception as e:
            logger.error(f"[VoiceIntegration] Synthesis failed: {e}")
            
        return None
    
    async def speak(self, text: str):
        """Convenience method: synthesize and play audio"""
        audio = await self.synthesize(text)
        if audio:
            # In a real implementation, this would play the audio
            logger.info(f"[VoiceIntegration] Speaking: {text[:50]}...")
            return True
        return False
    
    # ─────────────────────────────────────────────────────────────
    # Wake Word Detection
    # ─────────────────────────────────────────────────────────────
    
    async def start_wake_word_detection(self, callback: Callable[[str], None]):
        """Start listening for wake words (both personas)."""
        try:
            async with self.session.post(
                f"{MCP_URL}/mcp/voice/wake_word",
                json={
                    "wake_words": list(ALL_WAKE_WORDS.keys()),
                    "action": "start",
                    "callback_url": None
                }
            ) as resp:
                if resp.status == 200:
                    logger.info("[VoiceIntegration] Wake word detection started for Rocky + ROXY")
                    return True
        except Exception as e:
            logger.error(f"[VoiceIntegration] Wake word start failed: {e}")
        return False
    
    async def stop_wake_word_detection(self):
        """Stop wake word detection"""
        try:
            await self.session.post(
                f"{MCP_URL}/mcp/voice/wake_word",
                json={"action": "stop"}
            )
        except Exception:
            pass

    def handle_wake_word(self, phrase: str) -> str:
        """Resolve persona from wake phrase and switch mode."""
        persona = self._resolve_persona_from_wake_word(phrase)
        if persona and persona != self.mode:
            self.set_mode(persona)
        return self.config.greeting

    def _resolve_persona_from_wake_word(self, phrase: str) -> Optional[PersonaMode]:
        normalized = (phrase or "").strip().lower()
        return ALL_WAKE_WORDS.get(normalized, self.mode)
    
    # ─────────────────────────────────────────────────────────────
    # Command Routing via MCP
    # ─────────────────────────────────────────────────────────────
    
    async def route_command(self, command: str) -> Optional[str]:
        """
        Route a voice command to the appropriate MCP tool.
        
        Uses natural language understanding to determine:
        1. Which MCP bridge (orchestrator, rocky, n8n, voice)
        2. Which tool within that bridge
        3. What parameters to extract
        """
        try:
            # Determine the best tool based on command content
            tool_route = await self._analyze_command(command)
            
            if not tool_route:
                return self._get_fallback_response(command)
            
            # Execute the tool
            result = await self._execute_tool(
                tool_route["bridge"],
                tool_route["tool"],
                tool_route.get("params", {})
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[VoiceIntegration] Command routing failed: {e}")
            return "Sorry, I encountered an error processing that command."
    
    async def _analyze_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Analyze command to determine routing"""
        cmd_lower = command.lower()

        is_music = any(kw in cmd_lower for kw in ["chord", "scale", "song", "practice", "music", "play", "learn", "guitar", "piano"])
        is_dev = any(kw in cmd_lower for kw in ["task", "status", "citadel", "dispatch", "friday", "workflow", "automation", "backup", "deploy", "sync"])

        if ENABLE_AUTO_PERSONA_ROUTING:
            if is_music and self.mode != PersonaMode.ROCKY:
                self.set_mode(PersonaMode.ROCKY)
            elif is_dev and self.mode != PersonaMode.ROXY:
                self.set_mode(PersonaMode.ROXY)
        
        # Rocky (music) commands
        if is_music:
            if "explain" in cmd_lower or "what is" in cmd_lower:
                return {"bridge": "rocky", "tool": "rocky_explain_concept", "params": {"query": command}}
            if "exercise" in cmd_lower or "practice" in cmd_lower:
                return {"bridge": "rocky", "tool": "rocky_suggest_exercise", "params": {"skill": command}}
            return {"bridge": "rocky", "tool": "rocky_quick_answer", "params": {"question": command}}
        
        # Orchestrator commands
        if any(kw in cmd_lower for kw in ["task", "status", "citadel", "dispatch", "friday"]):
            if "create" in cmd_lower or "new" in cmd_lower:
                return {"bridge": "orchestrator", "tool": "orchestrator_create_task", "params": {"description": command}}
            if "status" in cmd_lower:
                return {"bridge": "orchestrator", "tool": "orchestrator_get_status", "params": {}}
            return {"bridge": "orchestrator", "tool": "orchestrator_list_tasks", "params": {}}
        
        # n8n workflow commands
        if any(kw in cmd_lower for kw in ["workflow", "automation", "backup", "deploy", "sync"]):
            if "backup" in cmd_lower:
                return {"bridge": "n8n", "tool": "backup_system", "params": {}}
            if "deploy" in cmd_lower:
                return {"bridge": "n8n", "tool": "deploy_to_friday", "params": {}}
            return {"bridge": "n8n", "tool": "n8n_list_workflows", "params": {}}
        
        # Mode switching
        if any(kw in cmd_lower for kw in ["switch mode", "change mode", "toggle mode"]):
            return {"bridge": "system", "tool": "toggle_mode", "params": {}}
        
        # Default to quick answer
        return {"bridge": "rocky", "tool": "rocky_quick_answer", "params": {"question": command}}
    
    async def _execute_tool(self, bridge: str, tool: str, params: Dict) -> str:
        """Execute an MCP tool and return the response"""
        try:
            # Handle system commands locally
            if bridge == "system":
                if tool == "toggle_mode":
                    new_mode = self.toggle_mode()
                    return f"Switched to {new_mode.name} mode. {self.config.greeting}"
            
            # Execute via MCP
            async with self.session.post(
                f"{MCP_URL}/mcp/{bridge}/{tool}",
                json=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get("response", result.get("message", str(result)))
                else:
                    return f"Tool {tool} returned status {resp.status}"
                    
        except Exception as e:
            logger.error(f"[VoiceIntegration] Tool execution failed: {e}")
            return "I couldn't complete that request."
    
    def _get_fallback_response(self, command: str) -> str:
        """Generate a fallback response when no tool matches"""
        if self.mode == PersonaMode.ROCKY:
            return f"Hmm, I'm not sure about '{command}'. Could you rephrase that? I'm best with music questions!"
        else:
            return f"I didn't understand '{command}'. Try asking about tasks, workflows, or system status."
    
    # ─────────────────────────────────────────────────────────────
    # Main Voice Loop
    # ─────────────────────────────────────────────────────────────
    
    async def run_voice_loop(self):
        """
        Main voice interaction loop:
        1. Wait for wake word
        2. Transcribe command
        3. Route to MCP
        4. Speak response
        """
        logger.info(f"[VoiceIntegration] Starting voice loop in {self.mode.name} mode")
        await self.speak(self.config.greeting)
        
        while True:
            try:
                # In a real implementation, this would:
                # 1. Use OpenWakeWord to detect wake phrase
                # 2. Record audio after wake word
                # 3. Transcribe with Whisper
                # 4. Process and respond
                
                # For now, just maintain the loop
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                logger.info("[VoiceIntegration] Voice loop cancelled")
                break
            except Exception as e:
                logger.error(f"[VoiceIntegration] Voice loop error: {e}")
                await asyncio.sleep(1)

# ─────────────────────────────────────────────────────────────
# CLI Interface
# ─────────────────────────────────────────────────────────────

async def main():
    """Test the voice integration"""
    async with VoiceIntegration() as voice:
        # Check services
        status = await voice.check_services()
        print(f"\n🎤 Voice Stack Status:")
        for service, healthy in status.items():
            icon = "✅" if healthy else "❌"
            print(f"  {icon} {service}")
        
        # Test command routing
        print(f"\n📡 Testing Command Routing ({voice.mode.name} mode):")
        test_commands = [
            "What is a major scale?",
            "Create a new task for code review",
            "List my workflows",
            "Switch mode",
            "How do I play a C chord?"
        ]
        
        for cmd in test_commands:
            response = await voice.route_command(cmd)
            print(f"\n  Command: '{cmd}'")
            print(f"  Response: {response[:100]}...")
        
        print(f"\n✅ Voice Integration Test Complete")

if __name__ == "__main__":
    asyncio.run(main())
