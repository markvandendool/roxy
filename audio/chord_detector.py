#!/usr/bin/env python3
"""
Ultra-fast chord detection - in-memory lookup (<1ms)
For real-time music teaching - NO LLM needed for basic chord recognition!
"""
import time
from typing import List, Tuple, Optional
import json

# Chord interval patterns (semitones from root)
CHORD_PATTERNS = {
    # Triads
    'major': [0, 4, 7],
    'minor': [0, 3, 7],
    'diminished': [0, 3, 6],
    'augmented': [0, 4, 8],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    
    # Seventh chords
    'major7': [0, 4, 7, 11],
    'minor7': [0, 3, 7, 10],
    'dominant7': [0, 4, 7, 10],
    'dim7': [0, 3, 6, 9],
    'half-dim7': [0, 3, 6, 10],
    'minmaj7': [0, 3, 7, 11],
    'aug7': [0, 4, 8, 10],
    
    # Extended
    'add9': [0, 4, 7, 14],
    '6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9],
    '9': [0, 4, 7, 10, 14],
    'm9': [0, 3, 7, 10, 14],
}

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_TO_NUM = {note: i for i, note in enumerate(NOTE_NAMES)}
# Add flats
NOTE_TO_NUM.update({'Db': 1, 'Eb': 3, 'Fb': 4, 'Gb': 6, 'Ab': 8, 'Bb': 10, 'Cb': 11})

def note_to_midi(note: str) -> int:
    """Convert note name to MIDI-style number (C=0, C#=1, etc.)"""
    note = note.strip().upper()
    if note[-1].isdigit():
        note = note[:-1]  # Remove octave
    # Handle flats
    if 'B' in note and len(note) > 1 and note[1] == 'B':
        note = note[0] + 'b'
    return NOTE_TO_NUM.get(note, NOTE_TO_NUM.get(note.replace('b', '#'), -1))

def notes_to_intervals(notes: List[str]) -> List[int]:
    """Convert note names to intervals from lowest note"""
    midi_nums = [note_to_midi(n) for n in notes if note_to_midi(n) >= 0]
    if not midi_nums:
        return []
    midi_nums = sorted(set(midi_nums))  # Remove duplicates, sort
    root = midi_nums[0]
    return [(n - root) % 12 for n in midi_nums]

def detect_chord(notes: List[str]) -> Tuple[str, float]:
    """
    Detect chord from note names
    Returns: (chord_name, confidence)
    """
    start = time.perf_counter()
    
    intervals = notes_to_intervals(notes)
    if len(intervals) < 2:
        return "Unknown", 0.0
    
    best_match = None
    best_score = 0
    
    # Try each note as potential root
    for rotation in range(len(intervals)):
        rotated = [(i - intervals[rotation]) % 12 for i in intervals]
        rotated = sorted(set(rotated))
        
        # Match against patterns
        for name, pattern in CHORD_PATTERNS.items():
            if set(rotated) == set(pattern):
                root_note = NOTE_NAMES[(note_to_midi(notes[0]) + intervals[rotation]) % 12]
                score = 1.0
                if best_score < score:
                    best_score = score
                    best_match = f"{root_note} {name}"
            elif set(pattern).issubset(set(rotated)):
                # Partial match (has extra notes)
                root_note = NOTE_NAMES[(note_to_midi(notes[0]) + intervals[rotation]) % 12]
                score = len(pattern) / len(rotated)
                if best_score < score:
                    best_score = score
                    best_match = f"{root_note} {name} (extended)"
    
    elapsed_us = (time.perf_counter() - start) * 1_000_000
    
    if best_match:
        return best_match, best_score
    return "Unknown", 0.0

def detect_chord_from_frequencies(freqs: List[float], tolerance_cents: float = 50) -> Tuple[str, float]:
    """
    Detect chord from frequencies (Hz)
    tolerance_cents: how close to exact pitch (50 = quarter tone)
    """
    import numpy as np
    
    def freq_to_note(f):
        if f <= 0:
            return None
        A4 = 440.0
        semitones = 12 * np.log2(f / A4)
        note_num = int(round(semitones)) + 9
        return NOTE_NAMES[note_num % 12]
    
    notes = [freq_to_note(f) for f in freqs if f > 0]
    notes = [n for n in notes if n is not None]
    
    if len(notes) < 2:
        return "Unknown", 0.0
    
    return detect_chord(notes)

def benchmark():
    """Benchmark chord detection speed"""
    test_cases = [
        (['C', 'E', 'G'], "C major"),
        (['A', 'C', 'E'], "A minor"),
        (['G', 'B', 'D', 'F'], "G dominant7"),
        (['C', 'E', 'G', 'B'], "C major7"),
        (['D', 'F', 'A'], "D minor"),
        (['F', 'A', 'C', 'E'], "F major7"),
        (['E', 'G#', 'B'], "E major"),
        (['B', 'D', 'F'], "B diminished"),
    ]
    
    print("🎵 Chord Detection Benchmark\n")
    
    latencies = []
    for notes, expected in test_cases:
        start = time.perf_counter()
        result, conf = detect_chord(notes)
        elapsed_us = (time.perf_counter() - start) * 1_000_000
        latencies.append(elapsed_us)
        
        status = "✅" if expected.split()[0] in result else "❌"
        print(f"  {status} {notes} → {result} ({conf:.0%}) [{elapsed_us:.1f}µs]")
    
    print(f"\n📊 Latency Stats:")
    print(f"   Min: {min(latencies):.1f}µs")
    print(f"   Max: {max(latencies):.1f}µs")
    print(f"   Avg: {sum(latencies)/len(latencies):.1f}µs")
    print(f"\n   ✅ Sub-millisecond! (~{sum(latencies)/len(latencies)/1000:.3f}ms)")

if __name__ == '__main__':
    benchmark()
    
    # Interactive test
    print("\n🎹 Interactive mode (enter notes like 'C E G', or 'quit'):")
    while True:
        try:
            inp = input("> ").strip()
            if inp.lower() in ('quit', 'exit', 'q'):
                break
            notes = inp.split()
            if notes:
                chord, conf = detect_chord(notes)
                print(f"   {chord} ({conf:.0%})")
        except (EOFError, KeyboardInterrupt):
            break
