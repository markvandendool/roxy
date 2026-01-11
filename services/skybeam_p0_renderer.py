#!/usr/bin/env python3
"""
SKYBEAM P0 Renderer — Cards + Voice (+ optional bed) -> master.mp4

Hard contract:
- Input: manifest.json in a job dir
- Output: outputs/master.mp4
- Updates manifest stages deterministically
"""

from __future__ import annotations
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

JOBS_DIR = Path.home() / ".roxy" / "content-pipeline" / "jobs"

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _run(cmd: List[str]) -> None:
    # Loud, deterministic execution
    subprocess.run(cmd, check=True)

def load_manifest(job_dir: Path) -> Dict[str, Any]:
    p = job_dir / "manifest.json"
    with p.open("r") as f:
        return json.load(f)

def save_manifest(job_dir: Path, manifest: Dict[str, Any]) -> None:
    p = job_dir / "manifest.json"
    tmp = job_dir / "manifest.json.tmp"
    with tmp.open("w") as f:
        json.dump(manifest, f, indent=2)
    tmp.replace(p)

def set_stage(manifest: Dict[str, Any], stage: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
    stages = manifest.setdefault("stages", {})
    st = stages.setdefault(stage, {})
    st["status"] = status
    st["updated_at"] = _utc_now()
    if extra:
        st.update(extra)
    manifest["updated_at"] = _utc_now()

def ensure_dirs(job_dir: Path) -> Dict[str, Path]:
    paths = {
        "assets": job_dir / "assets",
        "clips": job_dir / "clips",
        "outputs": job_dir / "outputs",
        "work": job_dir / "work",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths

def write_cards_text(job_dir: Path, topic: str) -> Path:
    """
    P0: 5 cards, 6s each = 30s total.
    Later: derive from research/script stage.
    """
    cards = [
        f"{topic}",
        "1) Core idea in one sentence",
        "2) Why it matters",
        "3) Quick example",
        "4) Common mistake",
        "5) Action step",
    ]
    cards_file = job_dir / "work" / "cards.txt"
    cards_file.parent.mkdir(parents=True, exist_ok=True)
    cards_file.write_text("\n".join(cards) + "\n")
    return cards_file

def make_silent_audio(job_dir: Path, duration_s: int) -> Path:
    out = job_dir / "work" / "voice.wav"
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo", "-t", str(duration_s), str(out)])
    return out

def maybe_tts_espeak(job_dir: Path, text: str, duration_floor_s: int) -> Path:
    """
    If espeak-ng exists, generate voice.wav; else fall back to silent audio.
    """
    out = job_dir / "work" / "voice.wav"
    if subprocess.run(["bash", "-lc", "command -v espeak-ng >/dev/null 2>&1"], check=False).returncode != 0:
        return make_silent_audio(job_dir, duration_floor_s)

    txt = job_dir / "work" / "voice.txt"
    txt.write_text(text)
    # espeak-ng -> wav
    _run(["bash", "-lc", f'espeak-ng -s 165 -w "{out}" < "{txt}"'])
    return out

def make_card_video(job_dir: Path, cards: List[str], seconds_per_card: int = 6) -> Path:
    """
    P0 cards-only video: solid background + centered text. No PIL dependency.
    Uses ffmpeg drawtext (needs fonts; usually present).
    """
    out = job_dir / "work" / "cards.mp4"
    total = len(cards) * seconds_per_card

    # Build drawtext filters as timed overlays
    # Each card appears for its slot; newline safe.
    filters = []
    t = 0
    for i, card in enumerate(cards):
        safe = card.replace(":", "\\:").replace("'", "\\'").replace("\n", "\\n")
        start = t
        end = t + seconds_per_card
        filters.append(
            "drawtext="
            "fontcolor=white:fontsize=48:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            f"text='{safe}':"
            f"enable='between(t,{start},{end})'"
        )
        t += seconds_per_card

    vf = ",".join(filters)
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=30",
        "-t", str(total),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out)
    ])
    return out

def mux_master(job_dir: Path, video_mp4: Path, voice_wav: Path) -> Path:
    out = job_dir / "outputs" / "master.mp4"
    _run([
        "ffmpeg", "-y",
        "-i", str(video_mp4),
        "-i", str(voice_wav),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(out)
    ])
    # Proof gate
    _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", str(out)])
    return out

def render_job(job_id: str) -> Path:
    job_dir = JOBS_DIR / job_id
    if not job_dir.exists():
        raise FileNotFoundError(f"job dir missing: {job_dir}")

    manifest = load_manifest(job_dir)
    paths = ensure_dirs(job_dir)

    topic = manifest.get("topic", "").strip() or "Untitled"
    cards_file = write_cards_text(job_dir, topic)
    cards = cards_file.read_text().splitlines()
    duration = len(cards) * 6

    # Stage: production (P0 = generate everything here)
    set_stage(manifest, "production", "running", {"note": "P0 renderer running"})
    save_manifest(job_dir, manifest)

    # Voice (P0)
    voice_text = " ".join(cards)
    voice_wav = maybe_tts_espeak(job_dir, voice_text, duration)

    # Video
    cards_mp4 = make_card_video(job_dir, cards, seconds_per_card=6)

    # Master
    master = mux_master(job_dir, cards_mp4, voice_wav)

    set_stage(manifest, "production", "completed", {"master_mp4": str(master)})
    manifest["status"] = "completed"
    save_manifest(job_dir, manifest)
    return master
