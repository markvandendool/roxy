#!/usr/bin/env python3
"""
OPUS CLIP KILLER - Local AI Clip Extraction Pipeline
Extracts viral moments from streams/recordings using Whisper + LLM

Usage:
  python3 clip_extractor.py <video_file> [--output-dir <dir>]

Pipeline:
  1. Whisper transcription with timestamps
  2. LLM viral moment detection (hooks, insights, humor, emotion)
  3. Score engagement potential (1-100)
  4. FFmpeg extraction
  5. Platform optimization (9:16, 1:1, 16:9)

Part of LUNA-000 CITADEL - CONTENT organ
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import requests

WHISPER_MODEL = "base.en"
OLLAMA_URL = "http://127.0.0.1:11435/api/generate"
OLLAMA_MODEL = "llama3:8b"

# Platform aspect ratios
PLATFORMS = {
    "tiktok": {"ratio": "9:16", "max_duration": 60, "width": 1080, "height": 1920},
    "youtube_shorts": {"ratio": "9:16", "max_duration": 60, "width": 1080, "height": 1920},
    "instagram_reels": {"ratio": "9:16", "max_duration": 90, "width": 1080, "height": 1920},
    "twitter": {"ratio": "1:1", "max_duration": 140, "width": 1080, "height": 1080},
    "youtube": {"ratio": "16:9", "max_duration": 600, "width": 1920, "height": 1080}
}

VIRAL_DETECTION_PROMPT = """Analyze this transcript segment and identify potential viral clip moments.

For each potential clip, provide:
1. Start timestamp (in seconds)
2. End timestamp (in seconds)
3. Type: hook/insight/humor/emotion/tutorial/reveal
4. Title (catchy, <60 chars)
5. Engagement score (1-100)
6. Reason why this could go viral

Look for:
- Strong opening hooks ("This changed everything...", "Nobody talks about this...")
- Aha moments and insights
- Humor and relatable moments
- Emotional peaks
- Tutorial gold (clear explanations)
- Surprising reveals

Transcript:
{transcript}

Respond in JSON format:
{{"clips": [
  {{"start": 120, "end": 180, "type": "insight", "title": "...", "score": 85, "reason": "..."}},
  ...
]}}
"""

def run_cmd(cmd, timeout=3600):
    """Run shell command"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def transcribe_video(video_path: Path, output_dir: Path) -> Dict:
    """Transcribe video using Whisper"""
    print(f"[CLIP] Transcribing {video_path.name}...")

    # Extract audio first
    audio_path = output_dir / "audio.wav"
    cmd = f'ffmpeg -y -i "{video_path}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "{audio_path}" 2>/dev/null'
    stdout, stderr, code = run_cmd(cmd, timeout=600)

    if code != 0 or not audio_path.exists():
        print(f"[ERROR] Audio extraction failed: {stderr}")
        return None

    # Run Whisper
    print("[CLIP] Running Whisper transcription...")
    cmd = f'whisper "{audio_path}" --model {WHISPER_MODEL} --output_format json --output_dir "{output_dir}" 2>/dev/null'
    stdout, stderr, code = run_cmd(cmd, timeout=1800)

    # Find JSON output
    json_path = output_dir / "audio.json"
    if not json_path.exists():
        # Try with video name
        json_path = output_dir / f"{audio_path.stem}.json"

    if json_path.exists():
        with open(json_path) as f:
            return json.load(f)

    print(f"[ERROR] Transcription failed: {stderr}")
    return None

def format_transcript_for_llm(whisper_data: Dict) -> str:
    """Format Whisper output for LLM analysis"""
    segments = whisper_data.get("segments", [])
    lines = []

    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        text = seg.get("text", "").strip()
        lines.append(f"[{start:.1f}s-{end:.1f}s] {text}")

    return "\n".join(lines)

def detect_viral_moments(transcript: str) -> List[Dict]:
    """Use LLM to detect viral moments"""
    print("[CLIP] Analyzing for viral moments...")

    prompt = VIRAL_DETECTION_PROMPT.format(transcript=transcript[:8000])

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 2000}
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json().get("response", "")

            # Extract JSON from response
            if "{" in result and "}" in result:
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                json_str = result[json_start:json_end]

                data = json.loads(json_str)
                return data.get("clips", [])

    except Exception as e:
        print(f"[WARN] LLM analysis failed: {e}")

    return []

def extract_clip(video_path: Path, output_path: Path, start: float, end: float,
                 platform: str = "youtube") -> bool:
    """Extract clip with FFmpeg"""
    config = PLATFORMS.get(platform, PLATFORMS["youtube"])

    duration = end - start
    if duration > config["max_duration"]:
        duration = config["max_duration"]
        end = start + duration

    # Build FFmpeg command
    vf_filters = []

    # Scale to target resolution
    if config["ratio"] == "9:16":
        # Portrait - crop center and scale
        vf_filters.append(f"crop=ih*9/16:ih,scale={config['width']}:{config['height']}")
    elif config["ratio"] == "1:1":
        # Square - crop center
        vf_filters.append(f"crop=min(iw\\,ih):min(iw\\,ih),scale={config['width']}:{config['height']}")
    else:
        # Landscape - just scale
        vf_filters.append(f"scale={config['width']}:{config['height']}")

    vf = ",".join(vf_filters) if vf_filters else "null"

    cmd = f'''ffmpeg -y -ss {start} -i "{video_path}" -t {duration} \
        -vf "{vf}" \
        -c:v libx264 -preset fast -crf 23 \
        -c:a aac -b:a 128k \
        "{output_path}" 2>/dev/null'''

    stdout, stderr, code = run_cmd(cmd, timeout=300)

    return code == 0 and output_path.exists()

def process_video(video_path: Path, output_dir: Path, min_score: int = 70) -> List[Dict]:
    """Full pipeline: transcribe → detect → extract"""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Transcribe
    whisper_data = transcribe_video(video_path, output_dir)
    if not whisper_data:
        return []

    # Step 2: Format transcript
    transcript = format_transcript_for_llm(whisper_data)

    # Save transcript
    with open(output_dir / "transcript.txt", "w") as f:
        f.write(transcript)

    # Step 3: Detect viral moments
    clips = detect_viral_moments(transcript)

    # Filter by score
    clips = [c for c in clips if c.get("score", 0) >= min_score]
    clips.sort(key=lambda x: x.get("score", 0), reverse=True)

    print(f"[CLIP] Found {len(clips)} potential clips (score >= {min_score})")

    # Step 4: Extract clips
    extracted = []
    for i, clip in enumerate(clips[:10]):  # Max 10 clips
        print(f"\n[CLIP] Extracting {i+1}/{len(clips)}: {clip.get('title', 'Untitled')}")

        for platform in ["tiktok", "youtube"]:
            safe_title = "".join(c for c in clip.get("title", f"clip_{i}")[:30] if c.isalnum() or c in " -_").strip()
            output_path = output_dir / f"{i+1:02d}_{platform}_{safe_title}.mp4"

            success = extract_clip(
                video_path,
                output_path,
                clip.get("start", 0),
                clip.get("end", 60),
                platform
            )

            if success:
                clip[f"{platform}_path"] = str(output_path)
                print(f"    ✓ {platform}: {output_path.name}")

        extracted.append(clip)

    # Save manifest
    manifest = {
        "source": str(video_path),
        "processed": datetime.now().isoformat(),
        "clips": extracted
    }

    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return extracted

def main():
    if len(sys.argv) < 2:
        print("Usage: clip_extractor.py <video_file> [--output-dir <dir>] [--min-score <N>]")
        print("\nLocal AI-powered clip extraction (Opus Clip killer)")
        print("Extracts viral moments using Whisper + LLM analysis")
        return

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        return

    # Parse arguments
    output_dir = Path.home() / ".roxy" / "clips" / video_path.stem
    min_score = 70

    for i, arg in enumerate(sys.argv):
        if arg == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
        if arg == "--min-score" and i + 1 < len(sys.argv):
            min_score = int(sys.argv[i + 1])

    print(f"\n{'='*60}")
    print(f"  OPUS CLIP KILLER - Local AI Clip Extraction")
    print(f"{'='*60}")
    print(f"Source: {video_path.name}")
    print(f"Output: {output_dir}")
    print(f"Min Score: {min_score}")
    print()

    clips = process_video(video_path, output_dir, min_score)

    print(f"\n{'='*60}")
    print(f"  EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Extracted: {len(clips)} clips")
    print(f"Output: {output_dir}")

    if clips:
        print("\nTop clips:")
        for i, clip in enumerate(clips[:5]):
            print(f"  {i+1}. [{clip.get('score', 0)}] {clip.get('title', 'Untitled')}")

    print()

if __name__ == "__main__":
    main()
