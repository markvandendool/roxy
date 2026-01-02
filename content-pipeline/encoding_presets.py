#!/usr/bin/env python3
"""Platform-specific FFmpeg encoding presets - LUNA-S6"""

import subprocess
import os

def _check_amf_available():
    """Check if AMF encoder is available"""
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=2)
        return 'amf' in result.stdout.lower()
    except:
        return False

def _check_vaapi_available():
    """Check if VAAPI encoder is available"""
    try:
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=2)
        return 'h264_vaapi' in result.stdout.lower() and os.path.exists('/dev/dri/renderD128')
    except:
        return False

AMF_AVAILABLE = _check_amf_available()
VAAPI_AVAILABLE = _check_vaapi_available()

PRESETS = {
    "generic": {
        "description": "Generic high-quality encoding",
        "video": "-c:v libx264 -crf 23 -preset medium",
        "audio": "-c:a aac -b:a 192k",
        "format": "mp4",
        "resolution": None
    },
    "generic_gpu": {
        "description": "Generic high-quality encoding (GPU-accelerated)",
        "video": "-c:v h264_amf -quality quality -rc cqp -qp_i 23 -qp_p 23 -qp_b 23" if AMF_AVAILABLE else "-c:v libx264 -crf 23 -preset medium",
        "audio": "-c:a aac -b:a 192k",
        "format": "mp4",
        "resolution": None
    },
    "generic_vaapi": {
        "description": "Generic high-quality encoding (VAAPI hardware-accelerated)",
        "video": "-hwaccel vaapi -hwaccel_device /dev/dri/renderD128 -c:v h264_vaapi -b:v 10M" if VAAPI_AVAILABLE else "-c:v libx264 -crf 23 -preset medium",
        "audio": "-c:a aac -b:a 192k",
        "format": "mp4",
        "resolution": None
    },
    "tiktok": {
        "description": "TikTok optimized (9:16, 2-4.5 Mbps)",
        "video": "-c:v libx264 -b:v 4000k -maxrate 4500k -bufsize 9000k -vf scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "audio": "-c:a aac -b:a 128k",
        "format": "mp4",
        "resolution": "1080x1920"
    },
    "youtube_shorts": {
        "description": "YouTube Shorts optimized (9:16, 8-15 Mbps)",
        "video": "-c:v libx264 -b:v 12000k -maxrate 15000k -bufsize 24000k -vf scale=1080:1920",
        "audio": "-c:a aac -b:a 192k -ar 48000",
        "format": "mp4",
        "resolution": "1080x1920"
    },
    "instagram_reels": {
        "description": "Instagram Reels optimized (9:16, 3.5-4.5 Mbps)",
        "video": "-c:v libx264 -b:v 4000k -maxrate 4500k -bufsize 9000k -vf scale=1080:1920",
        "audio": "-c:a aac -b:a 128k",
        "format": "mp4",
        "resolution": "1080x1920"
    }
}

def get_ffmpeg_command(input_path: str, output_path: str, preset: str = "generic", use_gpu: bool = None) -> str:
    """
    Get FFmpeg command for encoding
    
    Args:
        input_path: Input video file
        output_path: Output video file
        preset: Preset name
        use_gpu: Force GPU usage (None = auto-detect)
    """
    # Auto-detect GPU preference
    if use_gpu is None:
        use_gpu = os.getenv('ROXY_GPU_ENABLED', 'true').lower() == 'true'
    
    # Use GPU preset if available and requested
    if use_gpu and preset == "generic" and "generic_gpu" in PRESETS:
        preset = "generic_gpu"
    
    p = PRESETS.get(preset, PRESETS["generic"])
    return f"ffmpeg -i {input_path} {p['video']} {p['audio']} {output_path}"

if __name__ == "__main__":
    print("Available encoding presets:")
    for name, preset in PRESETS.items():
        print(f"  {name}: {preset['description']}")
