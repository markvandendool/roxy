#!/usr/bin/env python3
"""
Rocky Learning - Session Recording Pipeline
Story: RAF-012
Target: Audio → Pitch Analysis → Timing Analysis → SQLite Storage

Records practice sessions and builds comprehensive playing history.
"""

import asyncio
import json
import os
import sqlite3
import time
import wave
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import threading

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy not installed. Run: pip install numpy")
    exit(1)

# Paths
ROXY_DATA = Path.home() / ".roxy" / "data"
SESSIONS_DB = ROXY_DATA / "sessions.db"
RECORDINGS_DIR = ROXY_DATA / "recordings"


@dataclass
class PitchEvent:
    """Single pitch detection event."""
    timestamp: float
    frequency: float
    midi_note: float
    confidence: float
    note_name: str


@dataclass
class TimingEvent:
    """Timing analysis for a note."""
    note_onset: float
    note_offset: float
    duration_ms: float
    timing_error_ms: float  # vs expected beat
    velocity_estimate: float


@dataclass
class SessionSummary:
    """Summary of a practice session."""
    session_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    notes_played: int
    unique_notes: int
    pitch_accuracy_pct: float
    timing_accuracy_pct: float
    avg_note_duration_ms: float
    chords_detected: int
    most_played_notes: List[str]
    difficulty_score: float


class SessionRecorder:
    """Records and analyzes practice sessions."""

    def __init__(
        self,
        sample_rate: int = 48000,
        channels: int = 1,
        websocket_url: str = "ws://127.0.0.1:8767",
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.websocket_url = websocket_url

        # Session state
        self.session_id: Optional[str] = None
        self.recording = False
        self.session_start: Optional[datetime] = None
        self.audio_buffer: List[np.ndarray] = []
        self.pitch_events: List[PitchEvent] = []
        self.timing_events: List[TimingEvent] = []

        # Setup directories
        ROXY_DATA.mkdir(parents=True, exist_ok=True)
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        print(f"[ROXY.LEARN] Session Recorder initialized")
        print(f"[ROXY.LEARN] Data: {ROXY_DATA}")

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(SESSIONS_DB)
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                duration_seconds REAL,
                notes_played INTEGER,
                unique_notes INTEGER,
                pitch_accuracy_pct REAL,
                timing_accuracy_pct REAL,
                avg_note_duration_ms REAL,
                chords_detected INTEGER,
                difficulty_score REAL,
                audio_file TEXT
            )
        """)

        # Pitch events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pitch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp REAL,
                frequency REAL,
                midi_note REAL,
                confidence REAL,
                note_name TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Timing events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                note_onset REAL,
                note_offset REAL,
                duration_ms REAL,
                timing_error_ms REAL,
                velocity_estimate REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pitch_session
            ON pitch_events(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timing_session
            ON timing_events(session_id)
        """)

        conn.commit()
        conn.close()
        print(f"[ROXY.LEARN] Database ready: {SESSIONS_DB}")

    def start_session(self) -> str:
        """Start a new recording session."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start = datetime.now()
        self.recording = True
        self.audio_buffer = []
        self.pitch_events = []
        self.timing_events = []

        print(f"[ROXY.LEARN] Session started: {self.session_id}")
        return self.session_id

    def stop_session(self) -> Optional[SessionSummary]:
        """Stop recording and analyze session."""
        if not self.recording:
            return None

        self.recording = False
        end_time = datetime.now()
        duration = (end_time - self.session_start).total_seconds()

        # Analyze session
        summary = self._analyze_session(end_time, duration)

        # Save to database
        self._save_session(summary)

        # Save audio if we have data
        if self.audio_buffer:
            audio_file = self._save_audio()
            print(f"[ROXY.LEARN] Audio saved: {audio_file}")

        print(f"[ROXY.LEARN] Session ended: {self.session_id}")
        print(f"[ROXY.LEARN] Duration: {duration:.1f}s, Notes: {summary.notes_played}")

        return summary

    def add_pitch_event(self, event: PitchEvent):
        """Add a pitch detection event to the session."""
        if self.recording:
            self.pitch_events.append(event)

    def add_audio_chunk(self, chunk: np.ndarray):
        """Add audio chunk to buffer."""
        if self.recording:
            self.audio_buffer.append(chunk)

    def _analyze_session(self, end_time: datetime, duration: float) -> SessionSummary:
        """Analyze recorded session data."""
        notes_played = len(self.pitch_events)

        # Get unique notes
        note_names = [e.note_name for e in self.pitch_events]
        unique_notes = len(set(note_names))

        # Most played notes
        note_counts = {}
        for note in note_names:
            note_counts[note] = note_counts.get(note, 0) + 1
        most_played = sorted(note_counts.keys(), key=lambda x: note_counts[x], reverse=True)[:5]

        # Pitch accuracy (% of high confidence detections)
        if self.pitch_events:
            high_conf = sum(1 for e in self.pitch_events if e.confidence > 0.8)
            pitch_accuracy = (high_conf / len(self.pitch_events)) * 100
        else:
            pitch_accuracy = 0

        # Timing analysis
        timing_events = self._analyze_timing()
        self.timing_events = timing_events

        if timing_events:
            avg_duration = sum(e.duration_ms for e in timing_events) / len(timing_events)
            timing_errors = [abs(e.timing_error_ms) for e in timing_events]
            timing_accuracy = max(0, 100 - (sum(timing_errors) / len(timing_errors)))
        else:
            avg_duration = 0
            timing_accuracy = 0

        # Difficulty score (0-100 based on unique notes, duration, accuracy)
        difficulty = min(100, (
            (unique_notes * 5) +
            (min(duration, 300) / 10) +
            (pitch_accuracy / 5) +
            (timing_accuracy / 5)
        ))

        return SessionSummary(
            session_id=self.session_id,
            start_time=self.session_start,
            end_time=end_time,
            duration_seconds=duration,
            notes_played=notes_played,
            unique_notes=unique_notes,
            pitch_accuracy_pct=pitch_accuracy,
            timing_accuracy_pct=timing_accuracy,
            avg_note_duration_ms=avg_duration,
            chords_detected=0,  # TODO: chord detection
            most_played_notes=most_played,
            difficulty_score=difficulty,
        )

    def _analyze_timing(self) -> List[TimingEvent]:
        """Analyze note timing from pitch events."""
        if len(self.pitch_events) < 2:
            return []

        events = []
        current_note = None
        note_start = 0

        for i, event in enumerate(self.pitch_events):
            if current_note is None:
                # Start of note
                current_note = event.note_name
                note_start = event.timestamp
            elif event.note_name != current_note:
                # End of previous note
                duration = (event.timestamp - note_start) * 1000
                events.append(TimingEvent(
                    note_onset=note_start,
                    note_offset=event.timestamp,
                    duration_ms=duration,
                    timing_error_ms=0,  # TODO: beat alignment
                    velocity_estimate=0.7,  # TODO: estimate from amplitude
                ))
                # Start new note
                current_note = event.note_name
                note_start = event.timestamp

        return events

    def _save_session(self, summary: SessionSummary):
        """Save session to database."""
        conn = sqlite3.connect(SESSIONS_DB)
        cursor = conn.cursor()

        # Insert session
        cursor.execute("""
            INSERT INTO sessions (
                session_id, start_time, end_time, duration_seconds,
                notes_played, unique_notes, pitch_accuracy_pct,
                timing_accuracy_pct, avg_note_duration_ms,
                chords_detected, difficulty_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            summary.session_id,
            summary.start_time.isoformat(),
            summary.end_time.isoformat(),
            summary.duration_seconds,
            summary.notes_played,
            summary.unique_notes,
            summary.pitch_accuracy_pct,
            summary.timing_accuracy_pct,
            summary.avg_note_duration_ms,
            summary.chords_detected,
            summary.difficulty_score,
        ))

        # Insert pitch events
        for event in self.pitch_events:
            cursor.execute("""
                INSERT INTO pitch_events (
                    session_id, timestamp, frequency, midi_note,
                    confidence, note_name
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                event.timestamp,
                event.frequency,
                event.midi_note,
                event.confidence,
                event.note_name,
            ))

        # Insert timing events
        for event in self.timing_events:
            cursor.execute("""
                INSERT INTO timing_events (
                    session_id, note_onset, note_offset, duration_ms,
                    timing_error_ms, velocity_estimate
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                event.note_onset,
                event.note_offset,
                event.duration_ms,
                event.timing_error_ms,
                event.velocity_estimate,
            ))

        conn.commit()
        conn.close()

    def _save_audio(self) -> str:
        """Save audio buffer to WAV file."""
        audio_file = RECORDINGS_DIR / f"{self.session_id}.wav"

        audio_data = np.concatenate(self.audio_buffer)
        audio_int16 = (audio_data * 32767).astype(np.int16)

        with wave.open(str(audio_file), 'w') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return str(audio_file)

    def get_session_history(self, limit: int = 10) -> List[dict]:
        """Get recent session history."""
        conn = sqlite3.connect(SESSIONS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM sessions
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,))

        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return sessions

    def get_progress_stats(self) -> dict:
        """Get overall progress statistics."""
        conn = sqlite3.connect(SESSIONS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_time,
                AVG(pitch_accuracy_pct) as avg_pitch_accuracy,
                AVG(timing_accuracy_pct) as avg_timing_accuracy,
                AVG(difficulty_score) as avg_difficulty,
                MAX(difficulty_score) as max_difficulty,
                SUM(notes_played) as total_notes
            FROM sessions
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            "total_sessions": row[0] or 0,
            "total_time_hours": (row[1] or 0) / 3600,
            "avg_pitch_accuracy": row[2] or 0,
            "avg_timing_accuracy": row[3] or 0,
            "avg_difficulty": row[4] or 0,
            "max_difficulty": row[5] or 0,
            "total_notes": row[6] or 0,
        }


async def demo():
    """Demo the session recorder."""
    recorder = SessionRecorder()

    # Start session
    session_id = recorder.start_session()

    # Simulate some pitch events
    import random
    notes = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4']
    freqs = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]

    for i in range(50):
        idx = random.randint(0, len(notes) - 1)
        event = PitchEvent(
            timestamp=time.time(),
            frequency=freqs[idx],
            midi_note=60 + idx,
            confidence=random.uniform(0.7, 1.0),
            note_name=notes[idx],
        )
        recorder.add_pitch_event(event)
        await asyncio.sleep(0.1)

    # Stop and analyze
    summary = recorder.stop_session()
    print(f"\n[ROXY.LEARN] Session Summary:")
    print(f"  Notes played: {summary.notes_played}")
    print(f"  Unique notes: {summary.unique_notes}")
    print(f"  Pitch accuracy: {summary.pitch_accuracy_pct:.1f}%")
    print(f"  Difficulty: {summary.difficulty_score:.1f}")

    # Show history
    print(f"\n[ROXY.LEARN] Session History:")
    for session in recorder.get_session_history(5):
        print(f"  {session['session_id']}: {session['notes_played']} notes, "
              f"{session['difficulty_score']:.1f} difficulty")

    # Show progress
    stats = recorder.get_progress_stats()
    print(f"\n[ROXY.LEARN] Overall Progress:")
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Total time: {stats['total_time_hours']:.1f} hours")
    print(f"  Total notes: {stats['total_notes']}")


if __name__ == "__main__":
    asyncio.run(demo())
