#!/usr/bin/env python3
"""
MCP MUSIC SMOKE TEST
Sequential sanity checks for Apollo bridge + music tools.

Usage:
  python mcp_music_smoke.py

What it does:
  1) Prints Apollo bridge health.
  2) Calls play_chord (Cmaj7) and prints status/audio_sent.
  3) Calls play_progression (ii-V-I) and prints status/audio_sent.

Run this while the browser Apollo client is connected to the bridge
(ws://localhost:8788) to verify end-to-end sound.
"""

import json
from typing import Dict, Any

from apollo_bridge import health_check as bridge_health
from mcp_music_tools import handle_tool


def pretty(label: str, payload: Dict[str, Any]) -> None:
    print(f"\n== {label} ==")
    print(json.dumps(payload, indent=2))


def main() -> None:
    pretty("Bridge health", bridge_health())

    chord_result = handle_tool(
        "play_chord",
        {
            "chord": "Cmaj7",
            "instrument": "piano",
            "duration": 1.5,
            "velocity": 0.85,
        },
    )
    pretty("play_chord Cmaj7", chord_result)

    progression_result = handle_tool(
        "play_progression",
        {
            "chords": ["Dm7", "G7", "Cmaj7"],
            "tempo": 110,
            "beats_per_chord": 4,
            "instrument": "piano",
        },
    )
    pretty("play_progression ii-V-I", progression_result)

    print("\nDone. If audio_sent is false, check that Apollo bridge and browser client are connected.")


if __name__ == "__main__":
    main()
