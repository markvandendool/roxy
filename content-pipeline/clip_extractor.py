#!/usr/bin/env python3
"""
ROXY Content Pipeline - FFmpeg Clip Extraction (LUNA-S6)

Platform-specific encoding presets for:
- TikTok (9:16, 4Mbps)
- YouTube Shorts (9:16, 12Mbps)
- Instagram Reels (9:16, 4Mbps)
- Generic (configurable)

Usage:
    python clip_extractor.py <video> <clips.json> <output_dir> [--platform tiktok|youtube_shorts|instagram_reels|generic]
"""
import os
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional
from encoding_presets import PRESETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClipExtractor:
    """Extract clips with platform-specific encoding."""
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        self.ffmpeg = ffmpeg_path
    
    def get_preset(self, platform: str) -> Dict:
        """Get encoding preset for platform."""
        if platform not in PRESETS:
            logger.warning(f'Unknown platform {platform}, using generic')
            platform = 'generic'
        return PRESETS[platform]
    
    def extract_clip(
        self,
        input_video: str,
        output_path: str,
        start_time: float,
        end_time: float,
        platform: str = 'generic',
        subtitle_file: Optional[str] = None
    ) -> str:
        """
        Extract a single clip with platform-specific encoding.
        
        Args:
            input_video: Source video path
            output_path: Output file path
            start_time: Start time in seconds
            end_time: End time in seconds
            platform: Target platform (tiktok, youtube_shorts, instagram_reels, generic)
            subtitle_file: Optional subtitle file to burn in
        
        Returns:
            Output file path
        """
        preset = self.get_preset(platform)
        duration = end_time - start_time
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg, '-y',
            '-ss', str(start_time),
            '-i', input_video,
            '-t', str(duration)
        ]
        
        # Add video filter for vertical formats
        resolution = preset.get('resolution')
        if resolution and 'x' in resolution:
            width, height = resolution.split('x')
            if int(height) > int(width):  # Vertical format
                # Crop to 9:16 aspect ratio, then scale
                vf = f'crop=ih*9/16:ih,scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
            else:
                vf = f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
            cmd.extend(['-vf', vf])
        
        # Add subtitle burn-in if provided
        if subtitle_file and os.path.exists(subtitle_file):
            cmd.extend(['-vf', f"subtitles='{subtitle_file}'"])
        
        # Add video encoding from preset
        video_opts = preset['video'].split()
        cmd.extend(video_opts)
        
        # Add audio encoding from preset
        audio_opts = preset['audio'].split()
        cmd.extend(audio_opts)
        
        # Output file
        cmd.append(output_path)
        
        logger.info(f'Extracting clip: {start_time:.1f}s - {end_time:.1f}s (platform: {platform})')
        logger.debug(f'FFmpeg command: {" ".join(cmd)}')
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f'FFmpeg failed: {result.stderr}')
        
        # Validate output
        if not os.path.exists(output_path):
            raise RuntimeError(f'Output file not created: {output_path}')
        
        file_size = os.path.getsize(output_path)
        logger.info(f'Clip created: {output_path} ({file_size / 1024 / 1024:.1f} MB)')
        
        return output_path
    
    def batch_extract(
        self,
        input_video: str,
        clips_json: str,
        output_dir: str,
        platform: str = 'generic'
    ) -> List[str]:
        """
        Extract multiple clips from a clips manifest.
        
        Args:
            input_video: Source video path
            clips_json: JSON file with clip definitions
            output_dir: Output directory
            platform: Target platform for all clips
        
        Returns:
            List of extracted clip paths
        """
        with open(clips_json) as f:
            clips = json.load(f)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        extracted = []
        failed = []
        
        for i, clip in enumerate(clips, 1):
            title = clip.get('title', f'clip_{i}')
            # Sanitize title for filename
            safe_title = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in title)[:50]
            safe_title = safe_title.strip().replace(' ', '_')
            
            out_file = f'{output_dir}/{i:02d}_{safe_title}_{platform}.mp4'
            
            try:
                self.extract_clip(
                    input_video,
                    out_file,
                    clip['start_time'],
                    clip['end_time'],
                    platform
                )
                extracted.append(out_file)
            except Exception as e:
                logger.error(f'Clip {i} ({title}) failed: {e}')
                failed.append({'index': i, 'title': title, 'error': str(e)})
        
        logger.info(f'Batch complete: {len(extracted)} extracted, {len(failed)} failed')
        return extracted
    
    def validate_output(self, file_path: str, platform: str) -> Dict:
        """Validate output file meets platform specs."""
        preset = self.get_preset(platform)
        
        # Get video info with ffprobe
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,bit_rate,codec_name',
            '-of', 'json',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {'valid': False, 'error': 'ffprobe failed'}
        
        info = json.loads(result.stdout)
        stream = info.get('streams', [{}])[0]
        
        validation = {
            'valid': True,
            'file': file_path,
            'platform': platform,
            'actual': {
                'width': stream.get('width'),
                'height': stream.get('height'),
                'codec': stream.get('codec_name'),
                'bitrate': stream.get('bit_rate')
            },
            'expected': preset
        }
        
        # Check resolution
        if preset.get('resolution'):
            expected_w, expected_h = preset['resolution'].split('x')
            if stream.get('width') != int(expected_w) or stream.get('height') != int(expected_h):
                validation['valid'] = False
                validation['resolution_mismatch'] = True
        
        return validation


def list_platforms():
    """Print available platforms."""
    print('Available platforms:')
    for name, preset in PRESETS.items():
        print(f'  {name}: {preset["description"]}')
        if preset.get('resolution'):
            print(f'    Resolution: {preset["resolution"]}')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 4:
        print('Usage: clip_extractor.py <video> <clips.json> <output_dir> [--platform PLATFORM]')
        print('')
        list_platforms()
        sys.exit(1)
    
    video = sys.argv[1]
    clips_json = sys.argv[2]
    output_dir = sys.argv[3]
    
    # Parse platform argument
    platform = 'generic'
    for i, arg in enumerate(sys.argv):
        if arg == '--platform' and i + 1 < len(sys.argv):
            platform = sys.argv[i + 1]
    
    extractor = ClipExtractor()
    clips = extractor.batch_extract(video, clips_json, output_dir, platform)
    
    print(f'\nExtracted {len(clips)} clips for platform: {platform}')
    for clip in clips:
        print(f'  - {clip}')
