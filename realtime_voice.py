#!/usr/bin/env python3
"""
ROXY Real-Time Voice System
Ultra-low-latency conversational AI with interruption support

Architecture:
  Voice → VAD → Streaming STT → LLM → Streaming TTS → Speaker
           ↓                           ↓
        Interruption Detection ←───────┘

Target Latency: <500ms end-to-end
"""

import asyncio
import threading
import queue
import time
import json
import wave
import io
import os
import sys
import struct
import numpy as np
from pathlib import Path
from typing import Optional, AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum

# Audio
import pyaudio
import sounddevice as sd

# VAD
import webrtcvad
try:
    from silero_vad import load_silero_vad
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False

# STT
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER = True
except ImportError:
    import whisper
    FASTER_WHISPER = False

# TTS
try:
    import edge_tts
    EDGE_TTS = True
except ImportError:
    EDGE_TTS = False

# For ROXY integration
import requests


class VoiceState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass
class VoiceConfig:
    """Voice system configuration"""
    # Audio settings
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 480  # 30ms at 16kHz
    format: int = pyaudio.paInt16
    
    # VAD settings
    vad_mode: int = 3  # 0-3, higher = more aggressive
    speech_threshold: float = 0.5
    silence_duration: float = 0.8  # Seconds of silence before processing
    
    # STT settings
    whisper_model: str = "tiny"  # tiny, base, small, medium, large
    language: str = "en"
    
    # TTS settings
    tts_voice: str = "en-US-ChristopherNeural"  # Edge TTS voice
    tts_rate: str = "+10%"  # Speak faster
    piper_model: str = None  # Optional local Piper model
    
    # LLM settings
    roxy_url: str = "http://127.0.0.1:8766"
    roxy_token: str = ""
    
    # Behavior
    enable_interruption: bool = True
    start_generating_early: bool = True  # Start LLM before user finishes
    early_trigger_words: int = 5  # Words before early generation


class AudioBuffer:
    """Thread-safe audio buffer with ring buffer behavior"""
    
    def __init__(self, max_seconds: float = 30, sample_rate: int = 16000):
        self.max_samples = int(max_seconds * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.write_pos = 0
        self.lock = threading.Lock()
        
    def write(self, data: np.ndarray):
        """Write audio data to buffer"""
        with self.lock:
            n = len(data)
            if n >= self.max_samples:
                self.buffer[:] = data[-self.max_samples:]
                self.write_pos = 0
            else:
                end_pos = self.write_pos + n
                if end_pos <= self.max_samples:
                    self.buffer[self.write_pos:end_pos] = data
                else:
                    # Wrap around
                    first_part = self.max_samples - self.write_pos
                    self.buffer[self.write_pos:] = data[:first_part]
                    self.buffer[:n - first_part] = data[first_part:]
                self.write_pos = end_pos % self.max_samples
    
    def read_last(self, seconds: float, sample_rate: int = 16000) -> np.ndarray:
        """Read last N seconds of audio"""
        with self.lock:
            n_samples = int(seconds * sample_rate)
            n_samples = min(n_samples, self.max_samples)
            
            if self.write_pos >= n_samples:
                return self.buffer[self.write_pos - n_samples:self.write_pos].copy()
            else:
                # Wrap around read
                return np.concatenate([
                    self.buffer[-(n_samples - self.write_pos):],
                    self.buffer[:self.write_pos]
                ])
    
    def clear(self):
        """Clear buffer"""
        with self.lock:
            self.buffer.fill(0)
            self.write_pos = 0


class VADProcessor:
    """Voice Activity Detection with multiple backends"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        
        # WebRTC VAD (fast, simple)
        self.webrtc_vad = webrtcvad.Vad(config.vad_mode)
        
        # Silero VAD (more accurate, slightly slower)
        self.silero_model = None
        if SILERO_AVAILABLE:
            try:
                self.silero_model = load_silero_vad()
            except Exception as e:
                print(f"⚠️ Silero VAD not available: {e}")
        
        self.is_speech = False
        self.silence_frames = 0
        self.speech_frames = 0
        
    def process_chunk(self, audio_chunk: bytes) -> bool:
        """Process audio chunk, return True if speech detected"""
        
        # WebRTC VAD (fast check)
        try:
            is_speech = self.webrtc_vad.is_speech(audio_chunk, self.config.sample_rate)
        except:
            is_speech = False
        
        # Update state
        if is_speech:
            self.speech_frames += 1
            self.silence_frames = 0
            if self.speech_frames >= 3:  # Debounce
                self.is_speech = True
        else:
            self.silence_frames += 1
            if self.silence_frames >= int(self.config.silence_duration * 1000 / 30):  # Convert to frames
                if self.is_speech:
                    self.speech_frames = 0
                self.is_speech = False
        
        return self.is_speech
    
    def process_numpy(self, audio: np.ndarray) -> float:
        """Process numpy array, return speech probability"""
        
        if self.silero_model is not None:
            try:
                import torch
                tensor = torch.from_numpy(audio).float()
                prob = self.silero_model(tensor, self.config.sample_rate).item()
                return prob
            except:
                pass
        
        # Fallback: energy-based detection
        energy = np.sqrt(np.mean(audio ** 2))
        return min(1.0, energy * 10)  # Rough probability
    
    def reset(self):
        """Reset VAD state"""
        self.is_speech = False
        self.silence_frames = 0
        self.speech_frames = 0


class StreamingSTT:
    """Streaming Speech-to-Text with Whisper"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        
        if FASTER_WHISPER:
            # Faster-whisper (CTranslate2)
            self.model = WhisperModel(
                config.whisper_model,
                device="cuda" if self._has_cuda() else "cpu",
                compute_type="float16" if self._has_cuda() else "int8"
            )
            self.use_faster = True
        else:
            # OpenAI Whisper
            self.model = whisper.load_model(config.whisper_model)
            self.use_faster = False
        
        self.transcript_buffer = ""
        
    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe audio to text"""
        
        start = time.time()
        
        if self.use_faster:
            segments, info = self.model.transcribe(
                audio,
                language=self.config.language,
                beam_size=1,  # Fastest
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            text = " ".join([s.text for s in segments])
        else:
            result = self.model.transcribe(
                audio,
                language=self.config.language,
                fp16=self._has_cuda()
            )
            text = result["text"]
        
        elapsed = time.time() - start
        print(f"📝 STT: {text.strip()} ({elapsed*1000:.0f}ms)")
        
        return text.strip()
    
    def transcribe_streaming(self, audio: np.ndarray) -> str:
        """Transcribe with partial results (for early generation)"""
        
        # For now, just transcribe the chunk
        # Future: implement proper streaming with word timestamps
        return self.transcribe(audio)


class StreamingTTS:
    """Streaming Text-to-Speech with Edge TTS or Piper"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._audio_queue = queue.Queue()
        
        # Check for Piper model
        self.piper_model = config.piper_model
        if self.piper_model and Path(self.piper_model).exists():
            self.use_piper = True
        else:
            self.use_piper = False
            if not EDGE_TTS:
                print("⚠️ No TTS available! Install edge-tts or piper")
    
    async def speak(self, text: str, on_start: Callable = None, on_end: Callable = None):
        """Speak text with streaming audio"""
        
        if not text.strip():
            return
        
        self._stop_event.clear()
        self.is_speaking = True
        
        if on_start:
            on_start()
        
        try:
            if self.use_piper:
                await self._speak_piper(text)
            elif EDGE_TTS:
                await self._speak_edge(text)
            else:
                print(f"🔊 [No TTS] {text}")
        except asyncio.CancelledError:
            print("🔇 TTS cancelled")
        finally:
            self.is_speaking = False
            if on_end:
                on_end()
    
    async def _speak_edge(self, text: str):
        """Speak using Edge TTS"""
        
        communicate = edge_tts.Communicate(
            text,
            self.config.tts_voice,
            rate=self.config.tts_rate
        )
        
        audio_data = b""
        
        async for chunk in communicate.stream():
            if self._stop_event.is_set():
                break
                
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
                
                # Play chunks as they arrive (streaming)
                if len(audio_data) > 4096:
                    await self._play_audio_chunk(audio_data)
                    audio_data = b""
        
        # Play remaining audio
        if audio_data and not self._stop_event.is_set():
            await self._play_audio_chunk(audio_data)
    
    async def _speak_piper(self, text: str):
        """Speak using local Piper TTS"""
        
        import subprocess
        
        process = await asyncio.create_subprocess_exec(
            "piper",
            "-m", self.piper_model,
            "--output-raw",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE
        )
        
        stdout, _ = await process.communicate(input=text.encode())
        
        if not self._stop_event.is_set():
            # Convert raw audio and play
            audio = np.frombuffer(stdout, dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(audio, samplerate=22050)
            sd.wait()
    
    async def _play_audio_chunk(self, data: bytes):
        """Play audio chunk with minimal latency"""
        
        try:
            # Edge TTS outputs MP3, convert to raw
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(data))
            samples = np.array(audio.get_array_of_samples()).astype(np.float32) / 32768.0
            
            sd.play(samples, samplerate=audio.frame_rate, blocking=True)
        except Exception as e:
            print(f"⚠️ Audio playback error: {e}")
    
    def stop(self):
        """Stop current speech"""
        self._stop_event.set()
        sd.stop()
        self.is_speaking = False


class ROXYClient:
    """Client for ROXY LLM integration"""
    
    def __init__(self, config: VoiceConfig):
        self.config = config
        self.session = requests.Session()
        
        # Load token
        if not config.roxy_token:
            token_file = Path.home() / ".roxy" / "secret.token"
            if token_file.exists():
                self.config.roxy_token = token_file.read_text().strip()
        
        self.headers = {
            "X-ROXY-Token": self.config.roxy_token,
            "Content-Type": "application/json"
        }
    
    def query(self, text: str) -> str:
        """Send query to ROXY and get response"""
        
        try:
            response = self.session.post(
                f"{self.config.roxy_url}/run",
                headers=self.headers,
                json={"command": text},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", data.get("result", str(data)))
            else:
                return f"Error: HTTP {response.status_code}"
                
        except Exception as e:
            return f"Error: {e}"
    
    async def query_streaming(self, text: str) -> AsyncIterator[str]:
        """Stream response from ROXY"""
        
        # For now, get full response and yield words
        # Future: implement proper streaming endpoint
        response = self.query(text)
        
        words = response.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.01)  # Small delay between words


class RealtimeVoice:
    """
    Main real-time voice conversation system
    
    Usage:
        voice = RealtimeVoice()
        await voice.start()
    """
    
    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        
        # Components
        self.vad = VADProcessor(self.config)
        self.stt = StreamingSTT(self.config)
        self.tts = StreamingTTS(self.config)
        self.roxy = ROXYClient(self.config)
        
        # Audio
        self.audio = pyaudio.PyAudio()
        self.audio_buffer = AudioBuffer(max_seconds=30, sample_rate=self.config.sample_rate)
        
        # State
        self.state = VoiceState.IDLE
        self.is_running = False
        self._speech_start_time = None
        self._last_transcript = ""
        
        # Callbacks
        self.on_state_change: Callable = None
        self.on_transcript: Callable = None
        self.on_response: Callable = None
        
        # Tasks
        self._listen_task = None
        self._generation_task = None
        
    def _set_state(self, state: VoiceState):
        """Update state and trigger callback"""
        old_state = self.state
        self.state = state
        
        if self.on_state_change:
            self.on_state_change(old_state, state)
        
        # Visual feedback
        indicators = {
            VoiceState.IDLE: "⚪",
            VoiceState.LISTENING: "🔴",
            VoiceState.PROCESSING: "🟡",
            VoiceState.SPEAKING: "🟢",
            VoiceState.INTERRUPTED: "🔵"
        }
        print(f"\r{indicators[state]} {state.value.upper():<12}", end="", flush=True)
    
    async def start(self):
        """Start the voice conversation system"""
        
        print("\n" + "="*60)
        print("🎤 ROXY Real-Time Voice Chat")
        print("="*60)
        print("Speak naturally. I'll respond when you pause.")
        print("Interrupt me anytime by speaking.")
        print("Press Ctrl+C to exit.")
        print("="*60 + "\n")
        
        self.is_running = True
        self._set_state(VoiceState.IDLE)
        
        # Start audio input stream
        stream = self.audio.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            frames_per_buffer=self.config.chunk_size,
            stream_callback=self._audio_callback
        )
        
        try:
            stream.start_stream()
            
            # Main processing loop
            while self.is_running:
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            stream.stop_stream()
            stream.close()
            self.audio.terminate()
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio input callback - runs in real-time thread"""
        
        if not self.is_running:
            return (None, pyaudio.paComplete)
        
        # Convert to numpy
        audio_chunk = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Add to buffer
        self.audio_buffer.write(audio_chunk)
        
        # VAD processing
        is_speech = self.vad.process_chunk(in_data)
        
        if is_speech:
            if self.state == VoiceState.IDLE:
                # User started speaking
                self._on_speech_start()
            elif self.state == VoiceState.SPEAKING:
                # User interrupted AI
                self._on_interruption()
                
        elif self.vad.silence_frames >= int(self.config.silence_duration * 1000 / 30):
            if self.state == VoiceState.LISTENING:
                # User stopped speaking
                self._on_speech_end()
        
        return (None, pyaudio.paContinue)
    
    def _on_speech_start(self):
        """Called when user starts speaking"""
        self._speech_start_time = time.time()
        self._set_state(VoiceState.LISTENING)
        self.audio_buffer.clear()
    
    def _on_speech_end(self):
        """Called when user stops speaking"""
        
        if self.state != VoiceState.LISTENING:
            return
        
        self._set_state(VoiceState.PROCESSING)
        
        # Get audio from buffer
        speech_duration = time.time() - self._speech_start_time
        audio = self.audio_buffer.read_last(min(speech_duration + 0.5, 30), self.config.sample_rate)
        
        # Process in background
        asyncio.create_task(self._process_speech(audio))
    
    def _on_interruption(self):
        """Called when user interrupts AI"""
        
        self._set_state(VoiceState.INTERRUPTED)
        
        # Stop TTS
        self.tts.stop()
        
        # Cancel any ongoing generation
        if self._generation_task:
            self._generation_task.cancel()
        
        # Start listening again
        self._speech_start_time = time.time()
        self._set_state(VoiceState.LISTENING)
    
    async def _process_speech(self, audio: np.ndarray):
        """Process captured speech"""
        
        # Transcribe
        transcript = self.stt.transcribe(audio)
        
        if not transcript or len(transcript) < 2:
            self._set_state(VoiceState.IDLE)
            return
        
        self._last_transcript = transcript
        
        if self.on_transcript:
            self.on_transcript(transcript)
        
        print(f"\n👤 You: {transcript}")
        
        # Query ROXY
        response = self.roxy.query(transcript)
        
        if self.on_response:
            self.on_response(response)
        
        print(f"🤖 ROXY: {response}")
        
        # Speak response
        self._set_state(VoiceState.SPEAKING)
        await self.tts.speak(
            response,
            on_end=lambda: self._set_state(VoiceState.IDLE)
        )
    
    def stop(self):
        """Stop the voice system"""
        self.is_running = False
        self.tts.stop()


async def main():
    """Main entry point"""
    
    # Configure
    config = VoiceConfig(
        whisper_model="tiny",  # Fast!
        tts_voice="en-US-ChristopherNeural",
        enable_interruption=True
    )
    
    # Check for Piper model
    piper_model = Path.home() / ".roxy" / "piper-voices" / "en_US-lessac-medium.onnx"
    if piper_model.exists():
        config.piper_model = str(piper_model)
        print(f"✓ Using local Piper TTS: {piper_model.name}")
    
    # Start
    voice = RealtimeVoice(config)
    await voice.start()


if __name__ == "__main__":
    asyncio.run(main())
