#!/usr/bin/env python3
"""
ROXY Daily Briefing Generator
Generates 7 AM business briefing for MindSong

Part of LUNA-000 CITADEL
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"

# Placeholder data sources - will be replaced with real integrations
DATA_SOURCES = {
    "stripe": {
        "mrr": 12500,
        "growth_percent": 8.5,
        "new_subs": 12,
        "churned": 2
    },
    "students": {
        "active": 156,
        "at_risk": 8,
        "completed_this_week": 23,
        "stuck_points": ["chord inversions", "voice leading", "ear training intervals"]
    },
    "content": {
        "clips_ready": 14,
        "scheduled_posts": 21,
        "top_performer": {"title": "Voice Leading Secrets", "views": 45000},
        "engagement_rate": 4.2
    },
    "product": {
        "open_prs": 3,
        "merged_today": 5,
        "blockers": [],
        "next_release": "v0.4.0"
    },
    "calendar": {
        "meetings_today": 2,
        "focus_blocks": 4,
        "first_meeting": "10:00 AM - Team sync"
    }
}

BRIEFING_PROMPT = """You are ROXY generating a morning briefing for Mark.

Current data:
- MRR: ${mrr:,} ({growth}% growth)
- Active Students: {students} ({at_risk} at-risk)
- Content: {clips} clips ready, {posts} scheduled
- Product: {prs} open PRs, next release {release}
- Calendar: {meetings} meetings, first at {first_meeting}

Generate a concise, warm, 30-second spoken briefing. Lead with the most important news.
Format: conversational, like JARVIS would deliver it. No bullet points, just natural speech.
End with "What would you like to focus on first?"
"""

def get_briefing_data():
    """Gather data from all sources"""
    # In production, this would call real APIs
    return DATA_SOURCES

def generate_briefing():
    """Generate briefing using LLM"""
    data = get_briefing_data()

    prompt = BRIEFING_PROMPT.format(
        mrr=data["stripe"]["mrr"],
        growth=data["stripe"]["growth_percent"],
        students=data["students"]["active"],
        at_risk=data["students"]["at_risk"],
        clips=data["content"]["clips_ready"],
        posts=data["content"]["scheduled_posts"],
        prs=data["product"]["open_prs"],
        release=data["product"]["next_release"],
        meetings=data["calendar"]["meetings_today"],
        first_meeting=data["calendar"]["first_meeting"]
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 300}
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()

    except Exception as e:
        print(f"[ERROR] LLM failed: {e}")

    return None

def speak_briefing(text):
    """Speak briefing using Piper TTS"""
    piper_model = Path.home() / ".roxy" / "piper-voices" / "en_US-lessac-medium.onnx"

    try:
        process = subprocess.Popen(
            ["piper", "--model", str(piper_model), "--output_file", "/tmp/briefing.wav"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(input=text.encode(), timeout=60)

        # Play audio
        subprocess.run(["aplay", "/tmp/briefing.wav"], capture_output=True, timeout=120)

    except Exception as e:
        print(f"[ERROR] TTS failed: {e}")

def save_briefing(text):
    """Save briefing to log"""
    log_dir = Path.home() / ".roxy" / "briefings"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"briefing-{datetime.now().strftime('%Y%m%d')}.txt"
    with open(log_file, "w") as f:
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(text)

    print(f"[BRIEFING] Saved to {log_file}")

def main():
    print(f"\n{'='*60}")
    print(f"  ROXY Daily Briefing - {datetime.now().strftime('%A, %B %d, %Y')}")
    print(f"{'='*60}\n")

    # Generate briefing
    print("[ROXY] Generating briefing...")
    briefing = generate_briefing()

    if briefing:
        print(f"\n{briefing}\n")
        save_briefing(briefing)

        # Speak if --speak flag provided
        if "--speak" in sys.argv:
            print("[ROXY] Speaking briefing...")
            speak_briefing(briefing)
    else:
        print("[ERROR] Could not generate briefing")

if __name__ == "__main__":
    main()
