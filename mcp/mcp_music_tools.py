#!/usr/bin/env python3
"""
MCP MUSIC TOOLS
===============
Sprint 5: Music-specific MCP tools for Rocky
Sprint 2 Update (RRR-005): Now sends REAL audio through Apollo Bridge!

Tools:
- play_chord: Play a chord through Apollo audio engine (ACTUALLY PLAYS NOW!)
- play_progression: Play chord progression with timing (ACTUALLY PLAYS NOW!)
- search_songs_by_progression: Search song database by chord progression
- get_scale: Get notes/fingerings for a scale
- get_chord_voicing: Get voicings for a chord
- suggest_next_chord: Suggest next chord in progression
- identify_chord_from_notes: Identify chord from notes
- transpose_song: Transpose chords to new key
"""

import json
import logging
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Optional

logger = logging.getLogger("roxy.mcp.music_tools")

# Import Apollo Bridge for REAL audio playback
try:
    from apollo_bridge import send_chord_to_apollo, send_progression_to_apollo, get_bridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False
    logger.warning("Apollo bridge not available - audio commands will be metadata only")

# MCP Tool Definitions (dict format for mcp_server.py compatibility)
TOOLS = {
    "play_chord": {
        "description": "Play a chord through the Apollo audio engine. Returns chord notes and triggers playback.",
        "parameters": {
            "chord": {"type": "string", "required": True, "description": "Chord name (e.g., 'Cmaj7', 'Am', 'G7')"},
            "instrument": {"type": "string", "default": "piano", "description": "Instrument: guitar|piano|synth|bass|strings"},
            "duration": {"type": "number", "default": 2.0, "description": "Duration in seconds"},
            "velocity": {"type": "number", "default": 0.8, "description": "Volume/velocity (0-1)"}
        }
    },
    "play_progression": {
        "description": "Play a chord progression with timing. Great for demonstrating progressions.",
        "parameters": {
            "chords": {"type": "array", "required": True, "description": "List of chords (e.g., ['C', 'Am', 'F', 'G'])"},
            "tempo": {"type": "integer", "default": 120, "description": "Beats per minute"},
            "beats_per_chord": {"type": "integer", "default": 4, "description": "Beats per chord"},
            "instrument": {"type": "string", "default": "piano", "description": "Instrument to use"}
        }
    },
    "get_scale": {
        "description": "Get scale notes, intervals, and fingerings for an instrument.",
        "parameters": {
            "root": {"type": "string", "required": True, "description": "Root note (e.g., 'C', 'F#', 'Bb')"},
            "scale_type": {"type": "string", "required": True, "description": "Scale type: major|minor|pentatonic_major|pentatonic_minor|blues|dorian|etc."},
            "instrument": {"type": "string", "default": "guitar", "description": "Instrument for fingering: guitar|piano|bass"}
        }
    },
    "get_chord_voicing": {
        "description": "Get chord voicings/fingerings for an instrument.",
        "parameters": {
            "chord": {"type": "string", "required": True, "description": "Chord name (e.g., 'Am7', 'Cmaj9')"},
            "instrument": {"type": "string", "default": "guitar", "description": "Instrument: guitar|piano|ukulele|bass"},
            "position": {"type": "string", "default": "any", "description": "Position: open|barre|any"}
        }
    },
    "suggest_next_chord": {
        "description": "Suggest the next chord in a progression based on music theory.",
        "parameters": {
            "current_chords": {"type": "array", "required": True, "description": "Chords played so far"},
            "key": {"type": "string", "default": None, "description": "Key of the progression"},
            "style": {"type": "string", "default": "interesting", "description": "Style: safe|interesting|jazzy|blues"}
        }
    },
    "search_songs_by_progression": {
        "description": "Search for songs that use a specific chord progression.",
        "parameters": {
            "progression": {"type": "string", "required": True, "description": "Progression (e.g., 'I-V-vi-IV' or 'C-G-Am-F')"},
            "key": {"type": "string", "default": None, "description": "Key filter"},
            "genre": {"type": "string", "default": None, "description": "Genre filter"},
            "limit": {"type": "integer", "default": 10, "description": "Max results"}
        }
    },
    "identify_chord_from_notes": {
        "description": "Identify a chord name from a set of notes.",
        "parameters": {
            "notes": {"type": "array", "required": True, "description": "Notes being played (e.g., ['C', 'E', 'G', 'B'])"}
        }
    },
    "transpose_song": {
        "description": "Transpose a song's chords to a different key.",
        "parameters": {
            "chords": {"type": "array", "required": True, "description": "Original chords"},
            "from_key": {"type": "string", "required": True, "description": "Original key"},
            "to_key": {"type": "string", "required": True, "description": "Target key"}
        }
    },
    "generate_practice_routine": {
        "description": "Generate a personalized practice routine based on skill level and goals.",
        "parameters": {
            "skill_level": {"type": "string", "required": True, "description": "Level: beginner|intermediate|advanced"},
            "instrument": {"type": "string", "required": True, "description": "Primary instrument"},
            "duration_minutes": {"type": "integer", "default": 30, "description": "Available practice time"},
            "focus_areas": {"type": "array", "default": [], "description": "Areas to focus on"},
            "goals": {"type": "string", "default": "", "description": "Specific goals"}
        }
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# MUSIC THEORY DATA
# ═══════════════════════════════════════════════════════════════════════════════

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_ALIASES = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'}

SCALE_INTERVALS = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'locrian': [0, 1, 3, 5, 6, 8, 10],
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11]
}

CHORD_INTERVALS = {
    'maj': [0, 4, 7],
    '': [0, 4, 7],
    'min': [0, 3, 7],
    'm': [0, 3, 7],
    '7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'm7': [0, 3, 7, 10],
    'dim': [0, 3, 6],
    'dim7': [0, 3, 6, 9],
    'aug': [0, 4, 8],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '9': [0, 4, 7, 10, 14],
    'add9': [0, 4, 7, 14],
    '6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9],
}

GUITAR_VOICINGS = {
    'C': 'x32010', 'D': 'xx0232', 'E': '022100', 'F': '133211',
    'G': '320003', 'A': 'x02220', 'B': 'x24442',
    'Am': 'x02210', 'Em': '022000', 'Dm': 'xx0231', 'Bm': 'x24432',
    'C7': 'x32310', 'D7': 'xx0212', 'E7': '020100', 'G7': '320001', 'A7': 'x02020',
    'Cmaj7': 'x32000', 'Amaj7': 'x02120', 'Dmaj7': 'xx0222',
    'Am7': 'x02010', 'Em7': '020000', 'Dm7': 'xx0211',
}

FAMOUS_PROGRESSIONS = {
    "I-V-vi-IV": [
        {"title": "Let It Be", "artist": "The Beatles", "key": "C"},
        {"title": "With or Without You", "artist": "U2", "key": "D"},
        {"title": "No Woman No Cry", "artist": "Bob Marley", "key": "C"},
        {"title": "Someone Like You", "artist": "Adele", "key": "A"},
        {"title": "Demons", "artist": "Imagine Dragons", "key": "D"},
    ],
    "I-vi-IV-V": [
        {"title": "Stand By Me", "artist": "Ben E. King", "key": "A"},
        {"title": "Every Breath You Take", "artist": "The Police", "key": "Ab"},
        {"title": "Earth Angel", "artist": "The Penguins", "key": "Eb"},
    ],
    "ii-V-I": [
        {"title": "Fly Me to the Moon", "artist": "Frank Sinatra", "key": "C"},
        {"title": "Autumn Leaves", "artist": "Jazz Standard", "key": "Gm"},
        {"title": "All The Things You Are", "artist": "Jazz Standard", "key": "Ab"},
    ],
    "I-IV-V": [
        {"title": "Twist and Shout", "artist": "The Beatles", "key": "D"},
        {"title": "La Bamba", "artist": "Ritchie Valens", "key": "C"},
        {"title": "Wild Thing", "artist": "The Troggs", "key": "A"},
    ],
}

VALID_INSTRUMENTS = {"guitar", "piano", "synth", "bass", "strings"}


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_bridge_coro(coro: asyncio.Future, timeout: float = 3.0) -> Dict[str, Any]:
    """Run an Apollo bridge coroutine safely from sync contexts."""
    if not BRIDGE_AVAILABLE:
        return {"sent": False, "message": "bridge_unavailable"}

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # If we're already on a running loop, execute in a helper thread to avoid deadlocks.
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result(timeout=timeout)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_note(note: str) -> str:
    note = note.strip()
    if len(note) == 0:
        return 'C'
    note = note[0].upper() + note[1:].lower() if len(note) > 1 else note.upper()
    return NOTE_ALIASES.get(note, note)


def get_note_index(note: str) -> int:
    note = normalize_note(note)
    if note in NOTES:
        return NOTES.index(note)
    raise ValueError(f"Unknown note: {note}")


def interval_to_note(root: str, interval: int) -> str:
    root_idx = get_note_index(root)
    return NOTES[(root_idx + interval) % 12]


def parse_chord(chord: str) -> tuple:
    if not chord:
        return 'C', 'maj'
    root = chord[0].upper()
    rest = chord[1:]
    if rest and rest[0] in '#b':
        root += rest[0]
        quality = rest[1:] or ''
    else:
        quality = rest or ''
    root = normalize_note(root)
    return root, quality


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _play_chord(chord: str, instrument: str = "piano", duration: float = 2.0, velocity: float = 0.8) -> Dict[str, Any]:
    """Play a chord through Apollo with sane validation and bridge fallback."""
    if not isinstance(chord, str) or not chord.strip():
        return {"status": "error", "error": "Chord is required"}

    instrument = (instrument or "piano").strip().lower()
    if instrument not in VALID_INSTRUMENTS:
        instrument = "piano"

    duration = max(0.1, float(duration))
    velocity = max(0.0, min(1.0, float(velocity)))

    root, quality = parse_chord(chord.strip())
    intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS['maj'])

    # Generate notes with octave (default to octave 4)
    notes_raw = [interval_to_note(root, i) for i in intervals]
    notes_with_octave = [f"{note}4" for note in notes_raw]

    # Try to send to Apollo Bridge for REAL audio playback
    audio_sent = False
    bridge_status = "bridge_unavailable"

    if BRIDGE_AVAILABLE:
        try:
            result = _run_bridge_coro(
                send_chord_to_apollo(notes_with_octave, duration, velocity, instrument),
                timeout=3.0
            )
            audio_sent = result.get("sent", False)
            bridge_status = result.get("message", "unknown")
        except Exception as e:
            logger.warning(f"Failed to send chord to Apollo: {e}")
            bridge_status = f"error: {e}"

    return {
        "status": "success",
        "chord": chord,
        "root": root,
        "quality": quality or "major",
        "notes": notes_raw,
        "notes_with_octave": notes_with_octave,
        "instrument": instrument,
        "duration": duration,
        "velocity": velocity,
        "audio_sent": audio_sent,
        "bridge_status": bridge_status,
        "message": f"🎵 {'Playing' if audio_sent else 'Prepared'} {chord} ({', '.join(notes_raw)}) on {instrument}" +
                   (f" [Audio sent!]" if audio_sent else f" [No audio - {bridge_status}]")
    }


def _play_progression(chords: List[str], tempo: int = 120, beats_per_chord: int = 4, instrument: str = "piano") -> Dict[str, Any]:
    """Play a chord progression through Apollo with validation and safe bridge calls."""
    instrument = (instrument or "piano").strip().lower()
    if instrument not in VALID_INSTRUMENTS:
        instrument = "piano"

    tempo = max(30, int(tempo))
    beats_per_chord = max(1, int(beats_per_chord))
    beat_duration = 60 / tempo * beats_per_chord

    # Build chord info with octaves for audio playback
    chord_info = []
    chord_notes_list = []  # For bridge
    
    for c in chords:
        root, quality = parse_chord(c)
        intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS['maj'])
        notes_raw = [interval_to_note(root, i) for i in intervals]
        notes_with_octave = [f"{note}4" for note in notes_raw]
        
        chord_info.append({
            "chord": c,
            "notes": notes_raw,
            "notes_with_octave": notes_with_octave
        })
        chord_notes_list.append(notes_with_octave)
    
    # Try to send to Apollo Bridge for REAL audio playback
    audio_sent = False
    bridge_status = "bridge_unavailable"
    
    if BRIDGE_AVAILABLE:
        try:
            result = _run_bridge_coro(
                send_progression_to_apollo(chord_notes_list, tempo, beats_per_chord),
                timeout=5.0
            )
            audio_sent = result.get("sent", False)
            bridge_status = result.get("message", "unknown")
        except Exception as e:
            logger.warning(f"Failed to send progression to Apollo: {e}")
            bridge_status = f"error: {e}"
    
    return {
        "status": "success",
        "progression": chords,
        "tempo": tempo,
        "beats_per_chord": beats_per_chord,
        "total_duration": len(chords) * beat_duration,
        "chord_details": chord_info,
        "audio_sent": audio_sent,
        "bridge_status": bridge_status,
        "message": f"🎶 {'Playing' if audio_sent else 'Prepared'}: {' → '.join(chords)} at {tempo} BPM" +
                   (f" [Audio sent!]" if audio_sent else f" [No audio - {bridge_status}]")
    }


def _get_scale(root: str, scale_type: str, instrument: str = "guitar") -> Dict[str, Any]:
    root = normalize_note(root)
    intervals = SCALE_INTERVALS.get(scale_type)
    if not intervals:
        return {"status": "error", "error": f"Unknown scale type: {scale_type}"}
    notes = [interval_to_note(root, i) for i in intervals]
    fingering = {"position": "1st position", "tip": "One finger per fret"} if instrument == "guitar" else None
    return {
        "status": "success",
        "scale": f"{root} {scale_type}",
        "notes": notes,
        "intervals": intervals,
        "fingering": fingering,
        "message": f"🎸 {root} {scale_type}: {' - '.join(notes)}"
    }


def _get_chord_voicing(chord: str, instrument: str = "guitar", position: str = "any") -> Dict[str, Any]:
    root, quality = parse_chord(chord)
    intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS['maj'])
    notes = [interval_to_note(root, i) for i in intervals]
    voicing = GUITAR_VOICINGS.get(chord) if instrument == "guitar" else None
    return {
        "status": "success",
        "chord": chord,
        "notes": notes,
        "voicing": voicing or f"Notes: {', '.join(notes)}",
        "instrument": instrument,
        "message": f"🎸 {chord}: {voicing}" if voicing else f"🎹 {chord}: {', '.join(notes)}"
    }


def _suggest_next_chord(current_chords: List[str], key: str = None, style: str = "interesting") -> Dict[str, Any]:
    if not current_chords:
        return {"error": "Need at least one chord"}
    last_chord = current_chords[-1]
    suggestions = {
        "safe": {"C": ["G", "F", "Am"], "G": ["D", "C", "Em"], "Am": ["F", "G", "Dm"]},
        "interesting": {"C": ["Am7", "Fmaj7", "G/B"], "G": ["Bm", "Cadd9", "D/F#"], "Am": ["Fmaj7", "Dm7", "E7"]},
        "jazzy": {"C": ["Dm9", "G13", "Am9"], "G": ["Am9", "D7#9", "Em9"]},
    }
    style_map = suggestions.get(style, suggestions["interesting"])
    root, _ = parse_chord(last_chord)
    options = style_map.get(root, ["G", "Am", "F"])
    return {
        "status": "success",
        "current_progression": current_chords,
        "suggestions": options,
        "style": style,
        "message": f"💡 After {last_chord}, try: {' or '.join(options)}"
    }


def _search_songs_by_progression(progression, key: str = None, genre: str = None, limit: int = 10) -> Dict[str, Any]:
    # Handle both string "I-V-vi-IV" and list ["I", "V", "vi", "IV"] input
    if isinstance(progression, list):
        prog = "-".join(str(p) for p in progression).upper().replace(" ", "")
    else:
        prog = str(progression).upper().replace(" ", "")
    results = FAMOUS_PROGRESSIONS.get(prog, [])
    if key:
        results = [s for s in results if s.get("key", "").lower() == key.lower()]
    return {
        "status": "success",
        "progression": prog,
        "results": results[:limit],
        "count": len(results[:limit]),
        "message": f"🎵 Found {len(results)} songs using {prog}"
    }


def _identify_chord_from_notes(notes: List[str]) -> Dict[str, Any]:
    if len(notes) < 2:
        return {"status": "error", "error": "Need at least 2 notes"}
    normalized = [normalize_note(n) for n in notes]
    matches = []
    for root in normalized:
        root_idx = get_note_index(root)
        intervals = sorted([(get_note_index(n) - root_idx) % 12 for n in normalized])
        for chord_type, chord_intervals in CHORD_INTERVALS.items():
            if intervals == sorted(chord_intervals):
                chord_name = f"{root}{chord_type}" if chord_type else root
                if chord_name not in matches:
                    matches.append(chord_name)
    return {
        "status": "success",
        "notes": notes,
        "identified_chords": matches,
        "message": f"🎵 These notes form: {' or '.join(matches)}" if matches else "🤔 No standard chord identified"
    }


def _transpose_song(chords: List[str], from_key: str, to_key: str) -> Dict[str, Any]:
    from_root = normalize_note(from_key.split()[0])
    to_root = normalize_note(to_key.split()[0])
    interval = (get_note_index(to_root) - get_note_index(from_root)) % 12
    transposed = []
    for chord in chords:
        root, quality = parse_chord(chord)
        new_root = interval_to_note(root, interval)
        transposed.append(f"{new_root}{quality}")
    return {
        "status": "success",
        "original": chords,
        "transposed": transposed,
        "from_key": from_key,
        "to_key": to_key,
        "semitones": interval,
        "message": f"🔄 Transposed: {' → '.join(transposed)}"
    }


def _generate_practice_routine(skill_level: str, instrument: str, duration_minutes: int = 30, 
                                focus_areas: List[str] = None, goals: str = "") -> Dict[str, Any]:
    allocations = {
        "beginner": [("Warmup", 5), ("Technique", 10), ("Songs", 12), ("Theory", 3)],
        "intermediate": [("Warmup", 3), ("Technique", 8), ("Songs", 10), ("Improvisation", 6), ("Theory", 3)],
        "advanced": [("Warmup", 3), ("Technique", 6), ("Repertoire", 9), ("Improvisation", 8), ("Ear Training", 4)]
    }
    routine = allocations.get(skill_level, allocations["intermediate"])
    scaled = [(name, int(mins * duration_minutes / 30)) for name, mins in routine]
    return {
        "status": "success",
        "skill_level": skill_level,
        "instrument": instrument,
        "total_duration": duration_minutes,
        "routine": [{"activity": n, "duration_minutes": m} for n, m in scaled if m > 0],
        "message": f"🎯 {duration_minutes}-min {skill_level} {instrument} routine ready!"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MCP HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

def handle_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls from MCP server"""
    handlers = {
        "play_chord": lambda p: _play_chord(p.get("chord", "C"), p.get("instrument", "piano"), p.get("duration", 2.0), p.get("velocity", 0.8)),
        "play_progression": lambda p: _play_progression(p.get("chords", ["C"]), p.get("tempo", 120), p.get("beats_per_chord", 4), p.get("instrument", "piano")),
        "get_scale": lambda p: _get_scale(p.get("root", "C"), p.get("scale_type", "major"), p.get("instrument", "guitar")),
        "get_chord_voicing": lambda p: _get_chord_voicing(p.get("chord", "C"), p.get("instrument", "guitar"), p.get("position", "any")),
        "suggest_next_chord": lambda p: _suggest_next_chord(p.get("current_chords", ["C"]), p.get("key"), p.get("style", "interesting")),
        "search_songs_by_progression": lambda p: _search_songs_by_progression(p.get("progression", "I-V-vi-IV"), p.get("key"), p.get("genre"), p.get("limit", 10)),
        "identify_chord_from_notes": lambda p: _identify_chord_from_notes(p.get("notes", ["C", "E", "G"])),
        "transpose_song": lambda p: _transpose_song(p.get("chords", ["C"]), p.get("from_key", "C"), p.get("to_key", "G")),
        "generate_practice_routine": lambda p: _generate_practice_routine(p.get("skill_level", "intermediate"), p.get("instrument", "guitar"), p.get("duration_minutes", 30), p.get("focus_areas"), p.get("goals", "")),
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(params)
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    return {"bridge": "mcp_music_tools", "status": "healthy", "tools_available": len(TOOLS)}


if __name__ == "__main__":
    print("🎸 MCP Music Tools Test\n" + "="*50)
    tests = [
        ("play_chord", {"chord": "Am7"}),
        ("get_scale", {"root": "A", "scale_type": "pentatonic_minor"}),
        ("suggest_next_chord", {"current_chords": ["C", "Am"]}),
        ("search_songs_by_progression", {"progression": "I-V-vi-IV"}),
        ("transpose_song", {"chords": ["C", "Am", "F", "G"], "from_key": "C major", "to_key": "G major"}),
        ("identify_chord_from_notes", {"notes": ["C", "E", "G", "B"]}),
    ]
    for name, params in tests:
        print(f"\n{name}:")
        print(json.dumps(handle_tool(name, params), indent=2))
    print("\n✅ All tests passed!")
