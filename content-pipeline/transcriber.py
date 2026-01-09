#!/usr/bin/env python3
"""
ROXY Content Pipeline - Transcription Service
Uses faster-whisper for high-quality transcription with timestamps
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import timedelta
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model configuration
MODEL_SIZE = 'large-v3'  # Options: tiny, base, small, medium, large-v2, large-v3

def _detect_device():
    """Detect and return optimal device and compute type
    
    By default, uses CPU for Whisper to optimize GPU resources.
    This allows LLM and TTS to use GPU while Whisper uses the powerful CPU.
    Set ROXY_WHISPER_DEVICE=cuda to override and use GPU.
    """
    device = 'cpu'
    compute_type = 'float32'
    
    # Check for explicit CPU override (for GPU optimization)
    # This allows Whisper to use CPU while keeping LLM/TTS on GPU
    force_cpu = os.getenv('ROXY_WHISPER_DEVICE', '').lower() == 'cpu'
    force_gpu = os.getenv('ROXY_WHISPER_DEVICE', '').lower() == 'cuda'
    
    if force_cpu:
        logger.info('Using CPU for Whisper (optimized for GPU resource management)')
        return device, compute_type
    
    # Check for GPU availability
    try:
        import torch
        if torch.cuda.is_available():
            if force_gpu:
                device = 'cuda'
                compute_type = 'float16'
                logger.info(f'GPU forced via ROXY_WHISPER_DEVICE=cuda')
            else:
                # Default to CPU for better GPU resource management
                device = 'cpu'
                compute_type = 'float32'
                logger.info('Using CPU for Whisper (GPU available but reserved for LLM/TTS)')
        else:
            logger.info('No GPU available, using CPU')
    except ImportError:
        logger.warning('PyTorch not available, using CPU')
    except Exception as e:
        logger.warning(f'Error detecting GPU: {e}, using CPU')
    
    # Legacy: Check environment variable override (only if not forcing CPU)
    if not force_cpu and os.getenv('ROXY_GPU_ENABLED', 'true').lower() == 'true' and device == 'cpu':
        try:
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
                compute_type = 'float16'
        except:
            pass
    
    return device, compute_type

DEVICE, COMPUTE_TYPE = _detect_device()

class Transcriber:
    def __init__(self, model_size: str = MODEL_SIZE, device: str = None, compute_type: str = None):
        """
        Initialize transcriber
        
        Args:
            model_size: Whisper model size
            device: Override device (cuda/cpu), None for auto-detect
            compute_type: Override compute type, None for auto-detect
        """
        use_device = device or DEVICE
        use_compute_type = compute_type or COMPUTE_TYPE
        
        logger.info(f'Loading Whisper model: {model_size} on {use_device} (compute_type: {use_compute_type})...')
        self.model = WhisperModel(
            model_size,
            device=use_device,
            compute_type=use_compute_type
        )
        logger.info(f'Model loaded on {use_device}')
    
    def transcribe(self, audio_path: str, language: str = 'en') -> Dict:
        """
        Transcribe audio file and return structured result.
        
        Returns:
            {
                'text': full transcript,
                'segments': [{start, end, text, words: [{start, end, word}]}],
                'language': detected language,
                'duration': audio duration
            }
        """
        logger.info(f'Transcribing: {audio_path}')
        
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400
            )
        )
        
        result = {
            'text': '',
            'segments': [],
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': info.duration
        }
        
        full_text = []
        for segment in segments:
            seg_data = {
                'id': len(result['segments']),
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip(),
                'words': []
            }
            
            if segment.words:
                for word in segment.words:
                    seg_data['words'].append({
                        'word': word.word,
                        'start': word.start,
                        'end': word.end,
                        'probability': word.probability
                    })
            
            result['segments'].append(seg_data)
            full_text.append(segment.text.strip())
        
        result['text'] = ' '.join(full_text)
        logger.info(f'Transcription complete: {len(result["segments"])} segments, {info.duration:.1f}s')
        
        return result
    
    def to_srt(self, result: Dict) -> str:
        """Convert transcription result to SRT format."""
        srt_lines = []
        
        for i, seg in enumerate(result['segments'], 1):
            start = self._format_timestamp(seg['start'], srt=True)
            end = self._format_timestamp(seg['end'], srt=True)
            srt_lines.append(f'{i}')
            srt_lines.append(f'{start} --> {end}')
            srt_lines.append(seg['text'])
            srt_lines.append('')
        
        return '\n'.join(srt_lines)
    
    def to_vtt(self, result: Dict) -> str:
        """Convert transcription result to WebVTT format."""
        vtt_lines = ['WEBVTT', '']
        
        for seg in result['segments']:
            start = self._format_timestamp(seg['start'], srt=False)
            end = self._format_timestamp(seg['end'], srt=False)
            vtt_lines.append(f'{start} --> {end}')
            vtt_lines.append(seg['text'])
            vtt_lines.append('')
        
        return '\n'.join(vtt_lines)
    
    def _format_timestamp(self, seconds: float, srt: bool = True) -> str:
        """Format seconds to timestamp string."""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        ms = int((td.total_seconds() % 1) * 1000)
        
        if srt:
            return f'{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}'
        else:
            return f'{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}'
    
    def save_results(self, result: Dict, output_dir: str, base_name: str):
        """Save transcription in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # JSON (full data)
        json_path = output_path / f'{base_name}.json'
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f'Saved: {json_path}')
        
        # SRT
        srt_path = output_path / f'{base_name}.srt'
        with open(srt_path, 'w') as f:
            f.write(self.to_srt(result))
        logger.info(f'Saved: {srt_path}')
        
        # VTT
        vtt_path = output_path / f'{base_name}.vtt'
        with open(vtt_path, 'w') as f:
            f.write(self.to_vtt(result))
        logger.info(f'Saved: {vtt_path}')
        
        # Plain text
        txt_path = output_path / f'{base_name}.txt'
        with open(txt_path, 'w') as f:
            f.write(result['text'])
        logger.info(f'Saved: {txt_path}')
        
        return {
            'json': str(json_path),
            'srt': str(srt_path),
            'vtt': str(vtt_path),
            'txt': str(txt_path)
        }


def transcribe_file(audio_path: str, output_dir: str = None, language: str = 'en') -> Dict:
    """
    Convenience function to transcribe a file and save all outputs.
    """
    transcriber = Transcriber()
    result = transcriber.transcribe(audio_path, language)
    
    if output_dir is None:
        output_dir = os.path.dirname(audio_path)
    
    base_name = Path(audio_path).stem
    files = transcriber.save_results(result, output_dir, base_name)
    
    return {
        'transcript': result,
        'files': files
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: python transcriber.py <audio_file> [output_dir]')
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = transcribe_file(audio_file, output_dir)
    print(f'\nTranscription complete!')
    print(f'Files saved: {json.dumps(result["files"], indent=2)}')
    print(f'\nPreview (first 500 chars):\n{result["transcript"]["text"][:500]}...')
