#!/usr/bin/env python3
"""
ROXY Content Pipeline - Thumbnail Generator
Auto-generates thumbnails from video files using FFmpeg
LUNA-044: Build Thumbnail Generation Pipeline
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """Generate thumbnails from video files"""
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg'):
        self.ffmpeg = ffmpeg_path
    
    def extract_frame(
        self,
        video_path: str,
        output_path: str,
        timestamp: float = None,
        width: int = 1280,
        height: int = 720
    ) -> bool:
        """
        Extract a single frame as thumbnail.
        
        Args:
            video_path: Path to input video
            output_path: Path to save thumbnail
            timestamp: Time in seconds (default: 10% into video)
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            True if successful
        """
        try:
            # Get video duration if timestamp not specified
            if timestamp is None:
                duration = self._get_duration(video_path)
                timestamp = duration * 0.1  # 10% into video
            
            # Extract frame
            cmd = [
                self.ffmpeg,
                '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f'FFmpeg error: {result.stderr}')
                return False
            
            logger.info(f'Thumbnail extracted: {output_path}')
            return True
            
        except Exception as e:
            logger.error(f'Error extracting thumbnail: {e}')
            return False
    
    def generate_multiple(
        self,
        video_path: str,
        output_dir: str,
        count: int = 3,
        width: int = 1280,
        height: int = 720
    ) -> List[str]:
        """
        Generate multiple thumbnails at different timestamps.
        
        Args:
            video_path: Path to input video
            output_dir: Directory to save thumbnails
            count: Number of thumbnails to generate
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            List of generated thumbnail paths
        """
        duration = self._get_duration(video_path)
        if duration is None:
            return []
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_name = Path(video_path).stem
        thumbnails = []
        
        # Generate thumbnails at evenly spaced intervals
        for i in range(count):
            timestamp = duration * (i + 1) / (count + 1)
            output_path = output_dir / f'{video_name}_thumb_{i+1}.jpg'
            
            if self.extract_frame(video_path, str(output_path), timestamp, width, height):
                thumbnails.append(str(output_path))
        
        return thumbnails
    
    def _get_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds."""
        try:
            cmd = [
                self.ffmpeg,
                '-i', video_path,
                '-hide_banner',
                '-f', 'null',
                '-'
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse duration from stderr
            for line in result.stderr.split('\n'):
                if 'Duration:' in line:
                    time_str = line.split('Duration:')[1].split(',')[0].strip()
                    parts = time_str.split(':')
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
            
            return None
            
        except Exception as e:
            logger.error(f'Error getting duration: {e}')
            return None


def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = None,
    width: int = 1280,
    height: int = 720
) -> bool:
    """Convenience function for single thumbnail generation."""
    generator = ThumbnailGenerator()
    return generator.extract_frame(video_path, output_path, timestamp, width, height)


if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate thumbnails from video')
    parser.add_argument('video', help='Input video file')
    parser.add_argument('output', help='Output thumbnail path or directory')
    parser.add_argument('--timestamp', type=float, help='Timestamp in seconds (default: 10% into video)')
    parser.add_argument('--count', type=int, default=1, help='Number of thumbnails (if output is directory)')
    parser.add_argument('--width', type=int, default=1280, help='Thumbnail width')
    parser.add_argument('--height', type=int, default=720, help='Thumbnail height')
    
    args = parser.parse_args()
    
    generator = ThumbnailGenerator()
    
    output_path = Path(args.output)
    if output_path.is_dir() or args.count > 1:
        # Generate multiple
        thumbnails = generator.generate_multiple(
            args.video,
            str(output_path),
            args.count,
            args.width,
            args.height
        )
        print(f'Generated {len(thumbnails)} thumbnails:')
        for thumb in thumbnails:
            print(f'  {thumb}')
    else:
        # Generate single
        success = generator.extract_frame(
            args.video,
            args.output,
            args.timestamp,
            args.width,
            args.height
        )
        sys.exit(0 if success else 1)












