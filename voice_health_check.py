#!/usr/bin/env python3
"""
Voice Pipeline Health Check
RRR-001 Acceptance Test

Tests all three Wyoming voice services:
- Piper TTS (port 10200)
- Whisper STT (port 10300)  
- OpenWakeWord (port 10400)
"""

import asyncio
import sys
from datetime import datetime

try:
    from wyoming.client import AsyncClient
    from wyoming.tts import Synthesize
    from wyoming.asr import Transcribe, Transcript
    from wyoming.wake import Detect
    from wyoming.audio import AudioChunk, AudioStart, AudioStop
except ImportError:
    print("❌ wyoming not installed. Run: pip install --user --break-system-packages wyoming")
    sys.exit(1)


async def test_piper(verbose=False):
    """Test Piper TTS on port 10200"""
    try:
        client = AsyncClient.from_uri("tcp://localhost:10200")
        await asyncio.wait_for(client.connect(), timeout=5.0)
        
        await client.write_event(Synthesize(text="Health check").event())
        
        audio_bytes = 0
        while True:
            event = await asyncio.wait_for(client.read_event(), timeout=10.0)
            if event is None:
                break
            if AudioChunk.is_type(event.type):
                chunk = AudioChunk.from_event(event)
                audio_bytes += len(chunk.audio)
            elif AudioStop.is_type(event.type):
                break
        
        await client.disconnect()
        
        if audio_bytes > 0:
            if verbose:
                print(f"  Piper synthesized {audio_bytes} bytes")
            return True, audio_bytes
        return False, 0
    except Exception as e:
        return False, str(e)


async def test_whisper(verbose=False):
    """Test Whisper STT on port 10300"""
    try:
        client = AsyncClient.from_uri("tcp://localhost:10300")
        await asyncio.wait_for(client.connect(), timeout=5.0)
        
        # Send 0.5s of silence
        sample_rate = 16000
        samples = int(sample_rate * 0.5)
        
        await client.write_event(AudioStart(rate=sample_rate, width=2, channels=1).event())
        
        audio_data = bytes(samples * 2)
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            await client.write_event(AudioChunk(audio=chunk, rate=sample_rate, width=2, channels=1).event())
        
        await client.write_event(AudioStop().event())
        
        while True:
            event = await asyncio.wait_for(client.read_event(), timeout=10.0)
            if event is None:
                return False, "No response"
            if Transcript.is_type(event.type):
                await client.disconnect()
                return True, "Transcription ready"
        
    except Exception as e:
        return False, str(e)


async def test_openwakeword(verbose=False):
    """Test OpenWakeWord on port 10400"""
    try:
        client = AsyncClient.from_uri("tcp://localhost:10400")
        await asyncio.wait_for(client.connect(), timeout=5.0)
        
        await client.write_event(Detect(names=["hey_jarvis"]).event())
        
        sample_rate = 16000
        samples = int(sample_rate * 0.2)
        
        await client.write_event(AudioStart(rate=sample_rate, width=2, channels=1).event())
        
        audio_data = bytes(samples * 2)
        await client.write_event(AudioChunk(audio=audio_data, rate=sample_rate, width=2, channels=1).event())
        await client.write_event(AudioStop().event())
        
        await client.disconnect()
        return True, "Detection ready"
        
    except Exception as e:
        return False, str(e)


async def main():
    print("=" * 60)
    print("VOICE PIPELINE HEALTH CHECK")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = {}
    
    # Test Piper TTS
    print("\n[10200] Piper TTS...", end=" ", flush=True)
    ok, detail = await test_piper(verbose=True)
    results['piper'] = ok
    print(f"{'✅ PASS' if ok else '❌ FAIL'} - {detail}")
    
    # Test Whisper STT
    print("[10300] Whisper STT...", end=" ", flush=True)
    ok, detail = await test_whisper()
    results['whisper'] = ok
    print(f"{'✅ PASS' if ok else '❌ FAIL'} - {detail}")
    
    # Test OpenWakeWord
    print("[10400] OpenWakeWord...", end=" ", flush=True)
    ok, detail = await test_openwakeword()
    results['openwakeword'] = ok
    print(f"{'✅ PASS' if ok else '❌ FAIL'} - {detail}")
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passed == total:
        print(f"✅ RRR-001 ACCEPTANCE: PASSED ({passed}/{total})")
        print("All voice services operational")
        return 0
    else:
        print(f"❌ RRR-001 ACCEPTANCE: FAILED ({passed}/{total})")
        failed = [k for k, v in results.items() if not v]
        print(f"Failed services: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
