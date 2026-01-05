#!/usr/bin/env python3
"""
Rocky Learning - Skill Progression Modeling
Story: RAF-014
Target: Track skill development, suggest next challenges

Models user skill progression in music practice and suggests appropriate challenges.
"""

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
ROXY_DATA = Path.home() / ".roxy" / "data"
SKILLS_DB = ROXY_DATA / "skills.db"


@dataclass
class Skill:
    """A skill being tracked."""
    skill_id: str
    name: str
    category: str  # e.g., "chord", "scale", "technique", "song"
    level: float = 0  # 0-100
    experience: int = 0  # Total XP
    practice_count: int = 0
    last_practiced: Optional[datetime] = None
    mastery_threshold: int = 1000  # XP needed for mastery
    decay_rate: float = 0.01  # Skill decay per day of inactivity


@dataclass
class PracticeRecord:
    """Record of a practice attempt."""
    skill_id: str
    timestamp: datetime
    duration_seconds: float
    accuracy: float  # 0-1
    difficulty: float  # 0-1
    xp_earned: int
    notes: str = ""


@dataclass
class Challenge:
    """A suggested challenge."""
    challenge_id: str
    title: str
    description: str
    required_skills: List[str]
    difficulty: float  # 0-1
    estimated_time_minutes: int
    xp_reward: int


class SkillProgressionModel:
    """
    Models and tracks skill progression.

    Features:
    - XP-based leveling system
    - Skill decay for inactivity
    - Prerequisite tracking
    - Adaptive challenge suggestions
    - Progress analytics
    """

    # Level calculation: level = sqrt(xp / 10)
    # Level 10 = 1000 XP, Level 50 = 25000 XP, Level 100 = 100000 XP

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self.challenges: Dict[str, Challenge] = {}

        ROXY_DATA.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._load_skills()
        self._init_default_challenges()

        print(f"[ROXY.SKILLS] Progression model initialized")
        print(f"[ROXY.SKILLS] Tracking {len(self.skills)} skills")

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(SKILLS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                level REAL DEFAULT 0,
                experience INTEGER DEFAULT 0,
                practice_count INTEGER DEFAULT 0,
                last_practiced TEXT,
                mastery_threshold INTEGER DEFAULT 1000,
                decay_rate REAL DEFAULT 0.01
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT,
                timestamp TEXT,
                duration_seconds REAL,
                accuracy REAL,
                difficulty REAL,
                xp_earned INTEGER,
                notes TEXT,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_prerequisites (
                skill_id TEXT,
                prerequisite_id TEXT,
                PRIMARY KEY (skill_id, prerequisite_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_skill
            ON practice_records(skill_id)
        """)

        conn.commit()
        conn.close()

    def _load_skills(self):
        """Load skills from database."""
        conn = sqlite3.connect(SKILLS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM skills")
        for row in cursor.fetchall():
            last_practiced = None
            if row["last_practiced"]:
                last_practiced = datetime.fromisoformat(row["last_practiced"])

            skill = Skill(
                skill_id=row["skill_id"],
                name=row["name"],
                category=row["category"],
                level=row["level"],
                experience=row["experience"],
                practice_count=row["practice_count"],
                last_practiced=last_practiced,
                mastery_threshold=row["mastery_threshold"],
                decay_rate=row["decay_rate"],
            )
            self.skills[skill.skill_id] = skill

        conn.close()

        # Initialize default skills if empty
        if not self.skills:
            self._init_default_skills()

    def _init_default_skills(self):
        """Initialize default music skills."""
        default_skills = [
            # Chords
            ("chord_c_major", "C Major Chord", "chord"),
            ("chord_g_major", "G Major Chord", "chord"),
            ("chord_d_major", "D Major Chord", "chord"),
            ("chord_a_minor", "A Minor Chord", "chord"),
            ("chord_e_minor", "E Minor Chord", "chord"),
            ("chord_f_major", "F Major Chord", "chord"),
            ("chord_barre", "Barre Chords", "chord"),

            # Scales
            ("scale_c_major", "C Major Scale", "scale"),
            ("scale_g_major", "G Major Scale", "scale"),
            ("scale_a_minor", "A Minor Pentatonic", "scale"),
            ("scale_blues", "Blues Scale", "scale"),

            # Techniques
            ("technique_strumming", "Basic Strumming", "technique"),
            ("technique_fingerpicking", "Fingerpicking", "technique"),
            ("technique_hammer_on", "Hammer-ons", "technique"),
            ("technique_pull_off", "Pull-offs", "technique"),
            ("technique_bending", "String Bending", "technique"),

            # Theory
            ("theory_reading", "Music Reading", "theory"),
            ("theory_rhythm", "Rhythm Understanding", "theory"),
            ("theory_intervals", "Interval Recognition", "theory"),
        ]

        for skill_id, name, category in default_skills:
            self.add_skill(skill_id, name, category)

    def _init_default_challenges(self):
        """Initialize default challenges."""
        self.challenges = {
            "beginner_chords": Challenge(
                challenge_id="beginner_chords",
                title="First Chords",
                description="Master the basic open chords: C, G, D",
                required_skills=["chord_c_major", "chord_g_major", "chord_d_major"],
                difficulty=0.2,
                estimated_time_minutes=30,
                xp_reward=100,
            ),
            "minor_chords": Challenge(
                challenge_id="minor_chords",
                title="Minor Mood",
                description="Learn the emotional minor chords: Am, Em",
                required_skills=["chord_a_minor", "chord_e_minor"],
                difficulty=0.25,
                estimated_time_minutes=20,
                xp_reward=75,
            ),
            "chord_transitions": Challenge(
                challenge_id="chord_transitions",
                title="Smooth Transitions",
                description="Practice switching between C-G-D-Em cleanly",
                required_skills=["chord_c_major", "chord_g_major", "chord_d_major", "chord_e_minor"],
                difficulty=0.4,
                estimated_time_minutes=45,
                xp_reward=150,
            ),
            "first_song": Challenge(
                challenge_id="first_song",
                title="Your First Song",
                description="Play a complete song using 4 chords",
                required_skills=["chord_c_major", "chord_g_major", "chord_a_minor", "chord_e_minor", "technique_strumming"],
                difficulty=0.5,
                estimated_time_minutes=60,
                xp_reward=250,
            ),
            "pentatonic_master": Challenge(
                challenge_id="pentatonic_master",
                title="Pentatonic Explorer",
                description="Learn the A minor pentatonic scale",
                required_skills=["scale_a_minor"],
                difficulty=0.35,
                estimated_time_minutes=40,
                xp_reward=125,
            ),
        }

    def add_skill(self, skill_id: str, name: str, category: str,
                  mastery_threshold: int = 1000) -> Skill:
        """Add a new skill to track."""
        skill = Skill(
            skill_id=skill_id,
            name=name,
            category=category,
            mastery_threshold=mastery_threshold,
        )
        self.skills[skill_id] = skill
        self._save_skill(skill)
        return skill

    def _save_skill(self, skill: Skill):
        """Save skill to database."""
        conn = sqlite3.connect(SKILLS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO skills
            (skill_id, name, category, level, experience, practice_count,
             last_practiced, mastery_threshold, decay_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill.skill_id,
            skill.name,
            skill.category,
            skill.level,
            skill.experience,
            skill.practice_count,
            skill.last_practiced.isoformat() if skill.last_practiced else None,
            skill.mastery_threshold,
            skill.decay_rate,
        ))

        conn.commit()
        conn.close()

    def record_practice(self, skill_id: str, duration_seconds: float,
                       accuracy: float, difficulty: float = 0.5,
                       notes: str = "") -> Optional[PracticeRecord]:
        """Record a practice session for a skill."""
        if skill_id not in self.skills:
            print(f"[ROXY.SKILLS] Unknown skill: {skill_id}")
            return None

        skill = self.skills[skill_id]

        # Calculate XP earned
        # Base XP = duration * accuracy * difficulty multiplier
        difficulty_mult = 0.5 + difficulty  # 0.5x to 1.5x
        base_xp = int((duration_seconds / 60) * 10)  # 10 XP per minute base
        xp_earned = int(base_xp * accuracy * difficulty_mult)

        # Bonus for consistency
        if skill.last_practiced:
            days_since = (datetime.now() - skill.last_practiced).days
            if days_since <= 1:
                xp_earned = int(xp_earned * 1.2)  # 20% streak bonus

        # Update skill
        skill.experience += xp_earned
        skill.practice_count += 1
        skill.last_practiced = datetime.now()
        skill.level = self._calculate_level(skill.experience)

        self._save_skill(skill)

        # Create record
        record = PracticeRecord(
            skill_id=skill_id,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            accuracy=accuracy,
            difficulty=difficulty,
            xp_earned=xp_earned,
            notes=notes,
        )
        self._save_practice_record(record)

        print(f"[ROXY.SKILLS] {skill.name}: +{xp_earned} XP (Level {skill.level:.1f})")
        return record

    def _save_practice_record(self, record: PracticeRecord):
        """Save practice record to database."""
        conn = sqlite3.connect(SKILLS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO practice_records
            (skill_id, timestamp, duration_seconds, accuracy, difficulty, xp_earned, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.skill_id,
            record.timestamp.isoformat(),
            record.duration_seconds,
            record.accuracy,
            record.difficulty,
            record.xp_earned,
            record.notes,
        ))

        conn.commit()
        conn.close()

    def _calculate_level(self, xp: int) -> float:
        """Calculate level from XP. Level = sqrt(XP / 10)"""
        return math.sqrt(xp / 10)

    def apply_decay(self):
        """Apply skill decay for inactive skills."""
        now = datetime.now()
        decayed = 0

        for skill in self.skills.values():
            if skill.last_practiced:
                days_inactive = (now - skill.last_practiced).days
                if days_inactive > 7:  # Start decay after 1 week
                    decay_amount = int(skill.experience * skill.decay_rate * (days_inactive - 7))
                    if decay_amount > 0:
                        skill.experience = max(0, skill.experience - decay_amount)
                        skill.level = self._calculate_level(skill.experience)
                        decayed += 1

        if decayed > 0:
            print(f"[ROXY.SKILLS] Applied decay to {decayed} inactive skills")

    def get_suggested_challenges(self, count: int = 3) -> List[Challenge]:
        """Get challenges appropriate for current skill level."""
        suggestions = []

        for challenge in self.challenges.values():
            # Check if prerequisites are met (at least level 5)
            prereq_met = all(
                self.skills.get(skill_id, Skill("", "", "")).level >= 5
                for skill_id in challenge.required_skills
            )

            # Calculate challenge appropriateness
            avg_skill_level = sum(
                self.skills.get(skill_id, Skill("", "", "")).level
                for skill_id in challenge.required_skills
            ) / max(1, len(challenge.required_skills))

            # Ideal challenge is slightly above current level
            ideal_difficulty = (avg_skill_level / 100) + 0.1
            difficulty_match = 1 - abs(challenge.difficulty - ideal_difficulty)

            suggestions.append((challenge, prereq_met, difficulty_match))

        # Sort by appropriateness
        suggestions.sort(key=lambda x: (x[1], x[2]), reverse=True)

        return [s[0] for s in suggestions[:count]]

    def get_skill_summary(self) -> Dict:
        """Get summary of all skills."""
        categories = {}
        for skill in self.skills.values():
            if skill.category not in categories:
                categories[skill.category] = []
            categories[skill.category].append({
                "id": skill.skill_id,
                "name": skill.name,
                "level": skill.level,
                "xp": skill.experience,
                "practice_count": skill.practice_count,
            })

        total_xp = sum(s.experience for s in self.skills.values())
        avg_level = sum(s.level for s in self.skills.values()) / max(1, len(self.skills))

        return {
            "total_skills": len(self.skills),
            "total_xp": total_xp,
            "average_level": avg_level,
            "categories": categories,
        }

    def get_practice_history(self, skill_id: Optional[str] = None,
                            days: int = 30) -> List[Dict]:
        """Get practice history."""
        conn = sqlite3.connect(SKILLS_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        if skill_id:
            cursor.execute("""
                SELECT * FROM practice_records
                WHERE skill_id = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (skill_id, cutoff))
        else:
            cursor.execute("""
                SELECT * FROM practice_records
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            """, (cutoff,))

        records = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return records

    def get_weekly_summary(self) -> Dict:
        """Get weekly practice summary."""
        records = self.get_practice_history(days=7)

        total_time = sum(r["duration_seconds"] for r in records)
        total_xp = sum(r["xp_earned"] for r in records)
        skills_practiced = len(set(r["skill_id"] for r in records))
        avg_accuracy = sum(r["accuracy"] for r in records) / max(1, len(records))

        return {
            "practice_sessions": len(records),
            "total_time_minutes": total_time / 60,
            "total_xp": total_xp,
            "skills_practiced": skills_practiced,
            "average_accuracy": avg_accuracy,
        }


def demo():
    """Demo the skill progression system."""
    model = SkillProgressionModel()

    print("\n[ROXY.SKILLS] Recording some practice...")

    # Simulate practice sessions
    model.record_practice("chord_c_major", 300, 0.8)
    model.record_practice("chord_g_major", 300, 0.75)
    model.record_practice("chord_d_major", 240, 0.7)
    model.record_practice("technique_strumming", 600, 0.85, 0.3)

    # Get summary
    summary = model.get_skill_summary()
    print(f"\n[ROXY.SKILLS] Summary:")
    print(f"  Total Skills: {summary['total_skills']}")
    print(f"  Total XP: {summary['total_xp']}")
    print(f"  Average Level: {summary['average_level']:.1f}")

    # Get suggestions
    print(f"\n[ROXY.SKILLS] Suggested Challenges:")
    for challenge in model.get_suggested_challenges():
        print(f"  - {challenge.title} (difficulty: {challenge.difficulty:.0%})")
        print(f"    {challenge.description}")
        print(f"    Reward: {challenge.xp_reward} XP")

    # Weekly summary
    weekly = model.get_weekly_summary()
    print(f"\n[ROXY.SKILLS] This Week:")
    print(f"  Sessions: {weekly['practice_sessions']}")
    print(f"  Time: {weekly['total_time_minutes']:.0f} minutes")
    print(f"  XP Earned: {weekly['total_xp']}")


if __name__ == "__main__":
    demo()
