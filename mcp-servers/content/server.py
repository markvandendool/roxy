#!/usr/bin/env python3
"""
ROXY Content Pipeline MCP Server
Exposes content creation tools to Claude
"""
import os
import sys
import json
import subprocess
import logging
from pathlib import Path

ROXY_ROOT = Path(os.environ.get('ROXY_ROOT', str(Path.home() / '.roxy')))
CONTENT_ROOT = ROXY_ROOT / 'content-pipeline'
sys.path.insert(0, str(CONTENT_ROOT))

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-content')

INPUT_DIR = str(CONTENT_ROOT / 'input')
OUTPUT_DIR = str(CONTENT_ROOT / 'output')
WORK_DIR = str(CONTENT_ROOT / 'work')

@mcp.tool()
async def content_status() -> str:
    """Get content pipeline status and recent activity."""
    status = {
        'input_dir': INPUT_DIR,
        'output_dir': OUTPUT_DIR,
        'pending_videos': [],
        'processed_videos': [],
        'recent_clips': []
    }
    
    # Check input
    if os.path.exists(INPUT_DIR):
        status['pending_videos'] = os.listdir(INPUT_DIR)
    
    # Check output
    if os.path.exists(OUTPUT_DIR):
        status['processed_videos'] = os.listdir(OUTPUT_DIR)
    
    # Get recent clips
    for video_dir in status['processed_videos'][:5]:
        clips_dir = Path(OUTPUT_DIR) / video_dir / 'clips'
        if clips_dir.exists():
            for aspect in ['landscape', 'vertical']:
                aspect_dir = clips_dir / aspect
                if aspect_dir.exists():
                    clips = list(aspect_dir.glob('*.mp4'))[:3]
                    status['recent_clips'].extend([str(c) for c in clips])
    
    return json.dumps(status, indent=2)


@mcp.tool()
async def transcribe_video(video_path: str, output_dir: str = None) -> str:
    """
    Transcribe a video file using Whisper.
    
    Args:
        video_path: Path to video file
        output_dir: Optional output directory (defaults to same as video)
    """
    from transcriber import transcribe_file
    
    try:
        result = transcribe_file(video_path, output_dir)
        return json.dumps({
            'status': 'success',
            'files': result['files'],
            'duration': result['transcript'].get('duration'),
            'preview': result['transcript'].get('text', '')[:500]
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@mcp.tool()
async def detect_viral_moments(transcript_json: str, max_clips: int = 10) -> str:
    """
    Analyze transcript and identify viral moments using LLM.
    
    Args:
        transcript_json: Path to transcript JSON file
        max_clips: Maximum number of clips to suggest
    """
    from viral_detector import detect_viral_moments
    
    try:
        output_path = transcript_json.replace('.json', '_clips.json')
        moments = detect_viral_moments(transcript_json, output_path, max_clips)
        
        return json.dumps({
            'status': 'success',
            'clips_found': len(moments),
            'output_file': output_path,
            'top_moments': [{
                'title': m.title,
                'score': m.viral_score,
                'duration': f'{m.end_time - m.start_time:.0f}s',
                'hook': m.hook
            } for m in moments[:5]]
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@mcp.tool()
async def extract_clips(
    video_path: str,
    clips_json: str,
    output_dir: str,
    vertical: bool = False
) -> str:
    """
    Extract video clips based on viral moment timestamps.
    
    Args:
        video_path: Source video file
        clips_json: JSON file with clip timestamps
        output_dir: Output directory for clips
        vertical: If True, output 9:16 vertical clips
    """
    from clip_extractor import extract_clips as do_extract
    
    try:
        clips = do_extract(video_path, clips_json, output_dir, vertical)
        return json.dumps({
            'status': 'success',
            'clips_extracted': len(clips),
            'output_dir': output_dir,
            'clips': clips
        }, indent=2)
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


@mcp.tool()
async def queue_video(video_path: str) -> str:
    """
    Queue a video for processing by copying to input directory.
    
    Args:
        video_path: Path to video file to process
    """
    import shutil
    
    try:
        os.makedirs(INPUT_DIR, exist_ok=True)
        dest = os.path.join(INPUT_DIR, os.path.basename(video_path))
        shutil.copy2(video_path, dest)
        return f'Video queued for processing: {dest}'
    except Exception as e:
        return f'Error: {str(e)}'


@mcp.tool()
async def run_full_pipeline(video_path: str) -> str:
    """
    Run complete pipeline on a video: transcribe -> detect -> extract.
    
    Args:
        video_path: Path to video file
    """
    import time
    from pathlib import Path
    
    name = Path(video_path).stem
    work_dir = f'{WORK_DIR}/{name}'
    out_dir = f'{OUTPUT_DIR}/{name}'
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    
    results = {'video': video_path, 'steps': []}
    
    # Step 1: Transcribe
    from transcriber import transcribe_file
    try:
        t_result = transcribe_file(video_path, work_dir)
        results['steps'].append({'step': 'transcribe', 'status': 'success'})
        transcript_json = t_result['files']['json']
    except Exception as e:
        return json.dumps({'error': f'Transcription failed: {e}'})
    
    # Step 2: Viral detection
    from viral_detector import detect_viral_moments as detect
    try:
        clips_json = transcript_json.replace('.json', '_clips.json')
        moments = detect(transcript_json, clips_json, 10)
        results['steps'].append({'step': 'viral_detect', 'status': 'success', 'clips': len(moments)})
    except Exception as e:
        return json.dumps({'error': f'Viral detection failed: {e}'})
    
    # Step 3: Extract clips
    from clip_extractor import extract_clips as do_extract
    try:
        landscape = do_extract(video_path, clips_json, f'{out_dir}/clips/landscape', False)
        vertical = do_extract(video_path, clips_json, f'{out_dir}/clips/vertical', True)
        results['steps'].append({
            'step': 'extract',
            'status': 'success',
            'landscape': len(landscape),
            'vertical': len(vertical)
        })
    except Exception as e:
        return json.dumps({'error': f'Clip extraction failed: {e}'})
    
    results['output_dir'] = out_dir
    results['status'] = 'complete'
    
    return json.dumps(results, indent=2)


if __name__ == '__main__':
    mcp.run()
