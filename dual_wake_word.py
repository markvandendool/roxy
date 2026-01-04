#!/usr/bin/env python3
"""
DUAL WAKE WORD SYSTEM - FIXED FOR WYOMING PROTOCOL
===================================================
Sprint 5, Story RRR-002: "Hey Rocky" / "Hey Roxy" persona switching

Architecture:
- Listen for both wake words via OpenWakeWord (port 10400) using Wyoming protocol
- Route to appropriate persona based on wake word detected
- Music queries → Rocky (music teacher)
- Dev/system queries → ROXY (dev assistant)

FIXED: Uses Wyoming protocol instead of HTTP REST API
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import aiohttp

# Wyoming protocol imports
try:
    from wyoming.client import AsyncClient
    from wyoming.wake import Detect, Detection
    from wyoming.audio import AudioChunk, AudioStart, AudioStop
    from wyoming.asr import Transcribe, Transcript
    from wyoming.tts import Synthesize
    WYOMING_AVAILABLE = True
except ImportError:
    WYOMING_AVAILABLE = False
    print("⚠️  Wyoming not installed. Run: pip install --user --break-system-packages wyoming")

logger = logging.getLogger(__name__)


class Persona(Enum):
    """Available assistant personas"""
    ROCKY = "rocky"
    ROXY = "roxy"


@dataclass
class WakeWordConfig:
    """Configuration for a wake word trigger"""
    phrase: str
    persona: Persona
    voice_id: str
    greeting: str
    system_prompt: str
    wyoming_model: str  # Wyoming model name for detection


# WAKE WORD CONFIGURATIONS
# Note: OpenWakeWord has limited built-in wake words
# We map "hey_jarvis" → Rocky and "alexa" → ROXY as proxies
WAKE_WORDS = {
    "hey_jarvis": WakeWordConfig(
        phrase="hey jarvis",  # Proxy for "Hey Rocky"
        persona=Persona.ROCKY,
        voice_id="en_US-hfc_male-medium",  # Male voice for Rocky
        greeting="Hey! Rocky here - ready to rock some music! 🎸",
        wyoming_model="hey_jarvis",
        system_prompt="""You are Rocky, an enthusiastic music teacher AI.
You specialize in:
- Guitar, piano, drums, and bass instruction
- Music theory (chords, scales, progressions, rhythm)
- Song analysis and recommendation
- Practice routines and technique tips

Personality: Encouraging, fun, uses music metaphors.
Style: Casual but knowledgeable. Keep responses concise."""
    ),
    
    "hey_mycroft": WakeWordConfig(
        phrase="hey mycroft",  # Proxy for "Hey Roxy"
        persona=Persona.ROXY,
        voice_id="en_US-hfc_female-medium",  # Female voice for ROXY
        greeting="ROXY online. How can I assist? ⚡",
        wyoming_model="hey_mycroft",
        system_prompt="""You are ROXY, a highly capable dev assistant AI.
You specialize in:
- Software development and debugging
- System administration and DevOps
- Code review and architecture
- Task automation and scripting

Personality: Efficient, precise, helpful.
Style: Technical but accessible. Direct responses."""
    )
}


class DualWakeWordListener:
    """
    Listens for dual wake words using Wyoming protocol and routes to personas.
    
    Usage:
        listener = DualWakeWordListener()
        await listener.start()
    """
    
    def __init__(
        self,
        wake_word_port: int = 10400,
        whisper_port: int = 10300,
        piper_port: int = 10200,
        roxy_port: int = 8766
    ):
        self.wake_word_port = wake_word_port
        self.whisper_port = whisper_port
        self.piper_port = piper_port
        self.roxy_port = roxy_port
        
        self.current_persona: Optional[Persona] = None
        self.on_persona_change: Optional[Callable[[Persona], None]] = None
        self._running = False
        
        # Wyoming clients
        self._wake_client: Optional[AsyncClient] = None
        self._whisper_client: Optional[AsyncClient] = None
        self._piper_client: Optional[AsyncClient] = None
        
    async def start(self):
        """Start listening for wake words using Wyoming protocol"""
        if not WYOMING_AVAILABLE:
            logger.error("Wyoming not available. Cannot start.")
            return
            
        logger.info("🎤 Starting dual wake word listener (Wyoming protocol)...")
        logger.info(f"  Wake words: {list(WAKE_WORDS.keys())}")
        self._running = True
        
        try:
            # Connect to OpenWakeWord
            self._wake_client = AsyncClient.from_uri(f"tcp://localhost:{self.wake_word_port}")
            await self._wake_client.connect()
            logger.info(f"✅ Connected to OpenWakeWord on port {self.wake_word_port}")
            
            # Tell it which wake words to detect
            wake_models = [config.wyoming_model for config in WAKE_WORDS.values()]
            await self._wake_client.write_event(Detect(names=wake_models).event())
            
            # Start audio capture and detection loop
            async with aiohttp.ClientSession() as session:
                await self._detection_loop(session)
                
        except Exception as e:
            logger.error(f"Failed to start: {e}")
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop listening and cleanup"""
        self._running = False
        
        if self._wake_client:
            try:
                await self._wake_client.disconnect()
            except:
                pass
        if self._whisper_client:
            try:
                await self._whisper_client.disconnect()
            except:
                pass
        if self._piper_client:
            try:
                await self._piper_client.disconnect()
            except:
                pass
                
        logger.info("🛑 Dual wake word listener stopped")
        
    async def _detection_loop(self, session: aiohttp.ClientSession):
        """Main loop - stream audio to wake word detector and handle detections"""
        import pyaudio
        
        # Audio settings for OpenWakeWord
        RATE = 16000
        CHUNK = 1280  # 80ms of audio at 16kHz
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        
        pa = pyaudio.PyAudio()
        
        try:
            stream = pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            logger.info("🎙️ Microphone active - listening for wake words...")
            
            # Send audio start
            await self._wake_client.write_event(
                AudioStart(rate=RATE, width=2, channels=CHANNELS).event()
            )
            
            while self._running:
                # Read audio from microphone
                audio_data = stream.read(CHUNK, exception_on_overflow=False)
                
                # Send to wake word detector
                await self._wake_client.write_event(
                    AudioChunk(audio=audio_data, rate=RATE, width=2, channels=CHANNELS).event()
                )
                
                # Check for detection (non-blocking)
                try:
                    event = await asyncio.wait_for(
                        self._wake_client.read_event(),
                        timeout=0.01
                    )
                    
                    if event and Detection.is_type(event.type):
                        detection = Detection.from_event(event)
                        logger.info(f"🔔 Wake word detected: {detection.name}")
                        
                        if detection.name in WAKE_WORDS:
                            await self._handle_wake_word(session, detection.name)
                            
                except asyncio.TimeoutError:
                    pass  # No detection yet, keep listening
                    
        except Exception as e:
            logger.error(f"Audio capture error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
    async def _handle_wake_word(
        self, 
        session: aiohttp.ClientSession,
        wake_word: str
    ):
        """Handle a detected wake word"""
        config = WAKE_WORDS[wake_word]
        
        logger.info(f"🎙️ Wake word '{wake_word}' → {config.persona.value}")
        
        # Switch persona
        old_persona = self.current_persona
        self.current_persona = config.persona
        
        if self.on_persona_change:
            self.on_persona_change(config.persona)
            
        # Speak greeting
        await self._speak(session, config.greeting, config.voice_id)
        
        # Listen for query
        query = await self._listen(session)
        if not query:
            await self._speak(session, "I didn't catch that. Try again?", config.voice_id)
            return
            
        logger.info(f"📝 Query: {query}")
        
        # Get response from ROXY with persona system prompt
        response = await self._query_roxy(session, query, config.system_prompt)
        if response:
            await self._speak(session, response, config.voice_id)
        else:
            await self._speak(session, "Sorry, I couldn't process that.", config.voice_id)
            
    async def _speak(
        self, 
        session: aiohttp.ClientSession, 
        text: str, 
        voice_id: str
    ):
        """Synthesize and play speech using Piper TTS via Wyoming"""
        try:
            piper = AsyncClient.from_uri(f"tcp://localhost:{self.piper_port}")
            await piper.connect()
            
            # Request synthesis
            await piper.write_event(
                Synthesize(text=text, voice={"name": voice_id}).event()
            )
            
            # Collect audio chunks
            audio_data = bytearray()
            sample_rate = 22050  # Piper default
            
            while True:
                event = await asyncio.wait_for(piper.read_event(), timeout=30)
                if event is None:
                    break
                if AudioStart.is_type(event.type):
                    start = AudioStart.from_event(event)
                    sample_rate = start.rate
                elif AudioChunk.is_type(event.type):
                    chunk = AudioChunk.from_event(event)
                    audio_data.extend(chunk.audio)
                elif AudioStop.is_type(event.type):
                    break
                    
            await piper.disconnect()
            
            # Play audio
            if audio_data:
                await self._play_audio(bytes(audio_data), sample_rate)
                
        except Exception as e:
            logger.error(f"Speech error: {e}")
            
    async def _play_audio(self, audio_data: bytes, sample_rate: int):
        """Play audio through speakers"""
        import pyaudio
        
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            output=True
        )
        
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
        pa.terminate()
            
    async def _listen(self, session: aiohttp.ClientSession) -> Optional[str]:
        """Listen for speech and transcribe using Whisper via Wyoming"""
        import pyaudio
        
        try:
            whisper = AsyncClient.from_uri(f"tcp://localhost:{self.whisper_port}")
            await whisper.connect()
            
            # Audio settings
            RATE = 16000
            CHUNK = 1024
            RECORD_SECONDS = 5  # Max recording time
            
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            logger.info("🎤 Listening for query...")
            
            # Send audio to Whisper
            await whisper.write_event(AudioStart(rate=RATE, width=2, channels=1).event())
            
            frames = []
            for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
                audio = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(audio)
                await whisper.write_event(
                    AudioChunk(audio=audio, rate=RATE, width=2, channels=1).event()
                )
                
            await whisper.write_event(AudioStop().event())
            
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
            # Get transcript
            while True:
                event = await asyncio.wait_for(whisper.read_event(), timeout=30)
                if event is None:
                    break
                if Transcript.is_type(event.type):
                    transcript = Transcript.from_event(event)
                    await whisper.disconnect()
                    return transcript.text.strip()
                    
            await whisper.disconnect()
            
        except Exception as e:
            logger.error(f"Listen error: {e}")
            
        return None
            
    async def _query_roxy(
        self, 
        session: aiohttp.ClientSession,
        query: str,
        system_prompt: str
    ) -> Optional[str]:
        """Query ROXY with persona-specific system prompt"""
        try:
            url = f"http://localhost:{self.roxy_port}/chat"
            payload = {
                "message": query,
                "system_prompt": system_prompt,
                "persona": self.current_persona.value if self.current_persona else "roxy"
            }
            
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
        except Exception as e:
            logger.error(f"ROXY query error: {e}")
        return None


async def test_mode():
    """Test mode - verify Wyoming connections without microphone"""
    print("\n🧪 DUAL WAKE WORD - TEST MODE")
    print("=" * 50)
    
    if not WYOMING_AVAILABLE:
        print("❌ Wyoming not installed")
        return 1
        
    # Test OpenWakeWord connection
    print("\n[10400] OpenWakeWord...", end=" ", flush=True)
    try:
        client = AsyncClient.from_uri("tcp://localhost:10400")
        await client.connect()
        await client.write_event(Detect(names=["hey_jarvis", "hey_mycroft"]).event())
        await client.disconnect()
        print("✅ Connected, detection enabled")
    except Exception as e:
        print(f"❌ {e}")
        return 1
        
    # Test Whisper connection
    print("[10300] Whisper STT...", end=" ", flush=True)
    try:
        client = AsyncClient.from_uri("tcp://localhost:10300")
        await client.connect()
        await client.disconnect()
        print("✅ Connected")
    except Exception as e:
        print(f"❌ {e}")
        return 1
        
    # Test Piper connection
    print("[10200] Piper TTS...", end=" ", flush=True)
    try:
        client = AsyncClient.from_uri("tcp://localhost:10200")
        await client.connect()
        await client.disconnect()
        print("✅ Connected")
    except Exception as e:
        print(f"❌ {e}")
        return 1
        
    print("\n✅ All Wyoming services ready")
    print("\nConfigured wake words:")
    for key, config in WAKE_WORDS.items():
        print(f"  '{config.phrase}' → {config.persona.value}")
        
    return 0


# CLI entry point
async def main():
    """Run dual wake word listener as standalone service"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Check for test mode
    if "--test" in sys.argv:
        return await test_mode()
    
    listener = DualWakeWordListener()
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           🎸 DUAL WAKE WORD LISTENER - ACTIVE 🎧                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   Say "Hey Jarvis" for Rocky (music teaching)                    ║
║   Say "Hey Mycroft" for ROXY (dev assistance)                    ║
║                                                                  ║
║   (Custom wake words can be trained with OpenWakeWord)           ║
║                                                                  ║
║   Services (Wyoming Protocol):                                   ║
║   • OpenWakeWord: tcp://localhost:10400                          ║
║   • Whisper STT:  tcp://localhost:10300                          ║
║   • Piper TTS:    tcp://localhost:10200                          ║
║   • ROXY Core:    http://localhost:8766                          ║
║                                                                  ║
║   Press Ctrl+C to stop                                           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        await listener.start()
    except KeyboardInterrupt:
        await listener.stop()
        print("\n👋 Dual wake word listener stopped")
        
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
