#!/usr/bin/env python3
"""
ROXY Content Pipeline - WhisperX Transcription Service (LUNA-S6)

Features:
- WhisperX with speaker diarization
- Word-level timestamps
- Fallback to faster-whisper if WhisperX fails

Usage:
    python whisperx_transcriber.py <audio_file> [output_dir] [--hf-token TOKEN]
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try WhisperX first, fallback to faster-whisper
WHISPERX_AVAILABLE = False
try:
    import whisperx
    import torch
    WHISPERX_AVAILABLE = True
    logger.info('WhisperX available')
except ImportError:
    logger.warning('WhisperX not available, will use faster-whisper fallback')

# Configuration
MODEL_SIZE = 'large-v3'
DEVICE = 'cuda' if WHISPERX_AVAILABLE and torch.cuda.is_available() else 'cpu'
COMPUTE_TYPE = 'float16' if DEVICE == 'cuda' else 'float32'


class WhisperXTranscriber:
    """WhisperX transcriber with speaker diarization."""
    
    def __init__(self, model_size: str = MODEL_SIZE, hf_token: Optional[str] = None):
        self.model_size = model_size
        self.hf_token = hf_token or os.environ.get('HF_TOKEN')
        self.model = None
        self.diarize_model = None
        
        if not WHISPERX_AVAILABLE:
            raise RuntimeError('WhisperX not installed. Run: pip install whisperx')
        
        logger.info(f'Loading WhisperX model: {model_size} on {DEVICE}...')
        self.model = whisperx.load_model(model_size, DEVICE, compute_type=COMPUTE_TYPE)
        logger.info('WhisperX model loaded')
        
        if self.hf_token:
            logger.info('Loading diarization pipeline...')
            self.diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=self.hf_token,
                device=DEVICE
            )
            logger.info('Diarization pipeline loaded')
        else:
            logger.warning('No HF_TOKEN - speaker diarization disabled')
    
    def transcribe(self, audio_path: str, language: str = 'en') -> Dict:
        """
        Transcribe with WhisperX + optional diarization.
        
        Returns:
            {
                'text': full transcript,
                'segments': [{start, end, text, speaker, words}],
                'speakers': [list of unique speakers],
                'language': detected language,
                'duration': audio duration
            }
        """
        logger.info(f'Transcribing with WhisperX: {audio_path}')
        
        # Load audio
        audio = whisperx.load_audio(audio_path)
        
        # Transcribe
        result = self.model.transcribe(audio, batch_size=16, language=language)
        
        # Align whisper output
        logger.info('Aligning transcript...')
        model_a, metadata = whisperx.load_align_model(
            language_code=result['language'],
            device=DEVICE
        )
        result = whisperx.align(
            result['segments'],
            model_a,
            metadata,
            audio,
            DEVICE,
            return_char_alignments=False
        )
        
        # Speaker diarization (if available)
        speakers = []
        if self.diarize_model:
            logger.info('Running speaker diarization...')
            diarize_segments = self.diarize_model(audio_path)
            result = whisperx.assign_word_speakers(diarize_segments, result)
            
            # Extract unique speakers
            for seg in result['segments']:
                if 'speaker' in seg and seg['speaker'] not in speakers:
                    speakers.append(seg['speaker'])
        
        # Build output
        output = {
            'text': '',
            'segments': [],
            'speakers': speakers,
            'language': result.get('language', language),
            'duration': len(audio) / 16000  # Assuming 16kHz sample rate
        }
        
        full_text = []
        for seg in result['segments']:
            seg_data = {
                'id': len(output['segments']),
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'].strip(),
                'speaker': seg.get('speaker', 'SPEAKER_00'),
                'words': []
            }
            
            if 'words' in seg:
                for word in seg['words']:
                    seg_data['words'].append({
                        'word': word.get('word', ''),
                        'start': word.get('start', 0),
                        'end': word.get('end', 0),
                        'score': word.get('score', 1.0),
                        'speaker': word.get('speaker', seg_data['speaker'])
                    })
            
            output['segments'].append(seg_data)
            full_text.append(seg['text'].strip())
        
        output['text'] = ' '.join(full_text)
        logger.info(f'Transcription complete: {len(output["segments"])} segments, {len(speakers)} speakers')
        
        return output
    
    def to_srt(self, result: Dict, include_speaker: bool = True) -> str:
        """Convert to SRT with optional speaker labels."""
        srt_lines = []
        for i, seg in enumerate(result['segments'], 1):
            start = self._format_timestamp(seg['start'], srt=True)
            end = self._format_timestamp(seg['end'], srt=True)
            text = seg['text']
            if include_speaker and seg.get('speaker'):
                text = f"[{seg['speaker']}] {text}"
            srt_lines.extend([str(i), f'{start} --> {end}', text, ''])
        return '\n'.join(srt_lines)
    
    def _format_timestamp(self, seconds: float, srt: bool = True) -> str:
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        ms = int((td.total_seconds() % 1) * 1000)
        sep = ',' if srt else '.'
        return f'{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}'
    
    def save_results(self, result: Dict, output_dir: str, base_name: str) -> Dict:
        """Save transcription in multiple formats."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # JSON (full data with diarization)
        json_path = output_path / f'{base_name}_whisperx.json'
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)
        files['json'] = str(json_path)
        
        # SRT with speakers
        srt_path = output_path / f'{base_name}_whisperx.srt'
        with open(srt_path, 'w') as f:
            f.write(self.to_srt(result, include_speaker=True))
        files['srt'] = str(srt_path)
        
        # Plain text
        txt_path = output_path / f'{base_name}_whisperx.txt'
        with open(txt_path, 'w') as f:
            f.write(result['text'])
        files['txt'] = str(txt_path)
        
        logger.info(f'Saved WhisperX results to {output_dir}')
        return files


def transcribe_with_fallback(audio_path: str, output_dir: str = None, 
                             language: str = 'en', hf_token: str = None) -> Dict:
    """
    Transcribe using WhisperX, fallback to faster-whisper if unavailable.
    """
    if output_dir is None:
        output_dir = os.path.dirname(audio_path) or '.'
    
    base_name = Path(audio_path).stem
    
    # Try WhisperX first
    if WHISPERX_AVAILABLE:
        try:
            transcriber = WhisperXTranscriber(hf_token=hf_token)
            result = transcriber.transcribe(audio_path, language)
            files = transcriber.save_results(result, output_dir, base_name)
            return {'engine': 'whisperx', 'transcript': result, 'files': files}
        except Exception as e:
            logger.warning(f'WhisperX failed: {e}, falling back to faster-whisper')
    
    # Fallback to faster-whisper
    logger.info('Using faster-whisper fallback...')
    from transcriber import transcribe_file
    result = transcribe_file(audio_path, output_dir, language)
    return {'engine': 'faster-whisper', **result}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python whisperx_transcriber.py <audio_file> [output_dir] [--hf-token TOKEN]')
        print('')
        print('Environment variables:')
        print('  HF_TOKEN - HuggingFace token for speaker diarization')
        sys.exit(1)
    
    audio_file = sys.argv[1]
    output_dir = None
    hf_token = None
    
    # Parse args
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == '--hf-token' and i + 1 < len(args):
            hf_token = args[i + 1]
        elif not arg.startswith('--'):
            output_dir = arg
    
    result = transcribe_with_fallback(audio_file, output_dir, hf_token=hf_token)
    print(f'\nTranscription complete! (Engine: {result["engine"]})')
    print(f'Files: {json.dumps(result["files"], indent=2)}')
    
    if 'speakers' in result.get('transcript', {}):
        print(f'Speakers detected: {result["transcript"]["speakers"]}')
