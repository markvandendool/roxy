#!/usr/bin/env python3
"""
ROXY Wake Word Detector
Uses OpenWakeWord with hey_roxy as interim until custom Hey Roxy is trained
"""
import asyncio
import numpy as np
from openwakeword import Model
import pyaudio
from typing import Callable, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use built-in models - hey_roxy as interim wake word
MODEL_DIR = '/home/mark/.local/lib/python3.12/site-packages/openwakeword/resources/models'
MODELS = [
    f'{MODEL_DIR}/hey_roxy_v0.1.onnx',
]

# Audio config
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # 80ms at 16kHz

class WakeWordDetector:
    def __init__(self, callback: Optional[Callable] = None, threshold: float = 0.5):
        self.callback = callback
        self.threshold = threshold
        self.running = False
        
        logger.info('Loading wake word models...')
        self.model = Model(
            wakeword_model_paths=MODELS,
            enable_speex_noise_suppression=True,
        )
        logger.info(f'Models loaded: {list(self.model.models.keys())}')
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        if not self.running:
            return (None, pyaudio.paComplete)
            
        audio = np.frombuffer(in_data, dtype=np.int16)
        predictions = self.model.predict(audio)
        
        for model_name, score in predictions.items():
            if score > self.threshold:
                logger.info(f'🎤 Wake word detected: {model_name} (score: {score:.3f})')
                if self.callback:
                    asyncio.get_event_loop().call_soon_threadsafe(
                        lambda: asyncio.create_task(self.callback(model_name, score))
                    )
        
        return (in_data, pyaudio.paContinue)
    
    async def listen(self):
        """Start listening for wake word"""
        self.running = True
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                stream_callback=self._audio_callback
            )
            
            logger.info('🎧 Listening for wake word (say "Hey Roxy")...')
            stream.start_stream()
            
            while self.running and stream.is_active():
                await asyncio.sleep(0.1)
                
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
    
    def stop(self):
        self.running = False


async def demo_callback(model: str, score: float):
    print(f'\n🔔 WAKE WORD DETECTED: {model} (confidence: {score:.2%})\n')


async def main():
    detector = WakeWordDetector(callback=demo_callback, threshold=0.5)
    
    print('=' * 50)
    print('ROXY Wake Word Detector')
    print('Say "Hey Roxy" to trigger (interim wake word)')
    print('Press Ctrl+C to stop')
    print('=' * 50)
    
    try:
        await detector.listen()
    except KeyboardInterrupt:
        detector.stop()
        print('\nStopped.')


if __name__ == '__main__':
    asyncio.run(main())
