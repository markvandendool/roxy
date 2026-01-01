#!/usr/bin/env python3
"""Platform-specific FFmpeg encoding presets - LUNA-S6"""

PRESETS = {
    "generic": {
        "description": "Generic high-quality encoding",
        "video": "-c:v libx264 -crf 23 -preset medium",
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

def get_ffmpeg_command(input_path: str, output_path: str, preset: str = "generic") -> str:
    p = PRESETS.get(preset, PRESETS["generic"])
    return f"ffmpeg -i {input_path} {p['video']} {p['audio']} {output_path}"

if __name__ == "__main__":
    print("Available encoding presets:")
    for name, preset in PRESETS.items():
        print(f"  {name}: {preset['description']}")
