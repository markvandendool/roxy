#!/usr/bin/env python3
"""
Rocky Music Theory - Neo4j Graph Import
Story: RAF-009
Target: 100K+ chord relationships, <1ms query latency

Imports comprehensive music theory graph:
- Chords (major, minor, 7th, extended, altered)
- Scales (major, minor, modes, jazz)
- Progressions (common patterns, jazz standards)
- Songs (chord progressions from real songs)
"""

import json
from typing import List, Dict, Any

# Neo4j connection
try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed")
    print("Run: pip install neo4j")
    exit(1)

# Connection config
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "roxymusic2026"


class MusicTheoryGraph:
    """Import and query music theory knowledge graph."""

    # All 12 notes
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    FLAT_NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

    # Chord formulas (intervals from root)
    CHORD_FORMULAS = {
        'major': [0, 4, 7],
        'minor': [0, 3, 7],
        '7': [0, 4, 7, 10],
        'maj7': [0, 4, 7, 11],
        'min7': [0, 3, 7, 10],
        'dim': [0, 3, 6],
        'dim7': [0, 3, 6, 9],
        'aug': [0, 4, 8],
        'sus2': [0, 2, 7],
        'sus4': [0, 5, 7],
        '9': [0, 4, 7, 10, 14],
        'maj9': [0, 4, 7, 11, 14],
        'min9': [0, 3, 7, 10, 14],
        '11': [0, 4, 7, 10, 14, 17],
        '13': [0, 4, 7, 10, 14, 17, 21],
        '7#9': [0, 4, 7, 10, 15],
        '7b9': [0, 4, 7, 10, 13],
        'add9': [0, 4, 7, 14],
        '6': [0, 4, 7, 9],
        'min6': [0, 3, 7, 9],
    }

    # Scale formulas
    SCALE_FORMULAS = {
        'major': [0, 2, 4, 5, 7, 9, 11],
        'natural_minor': [0, 2, 3, 5, 7, 8, 10],
        'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
        'melodic_minor': [0, 2, 3, 5, 7, 9, 11],
        'dorian': [0, 2, 3, 5, 7, 9, 10],
        'phrygian': [0, 1, 3, 5, 7, 8, 10],
        'lydian': [0, 2, 4, 6, 7, 9, 11],
        'mixolydian': [0, 2, 4, 5, 7, 9, 10],
        'locrian': [0, 1, 3, 5, 6, 8, 10],
        'pentatonic_major': [0, 2, 4, 7, 9],
        'pentatonic_minor': [0, 3, 5, 7, 10],
        'blues': [0, 3, 5, 6, 7, 10],
        'whole_tone': [0, 2, 4, 6, 8, 10],
        'chromatic': list(range(12)),
    }

    # Common progressions
    PROGRESSIONS = [
        {'name': 'I-IV-V-I', 'degrees': [1, 4, 5, 1], 'style': 'pop'},
        {'name': 'I-V-vi-IV', 'degrees': [1, 5, 6, 4], 'style': 'pop'},
        {'name': 'ii-V-I', 'degrees': [2, 5, 1], 'style': 'jazz'},
        {'name': 'I-vi-IV-V', 'degrees': [1, 6, 4, 5], 'style': 'pop'},
        {'name': 'I-IV-vi-V', 'degrees': [1, 4, 6, 5], 'style': 'pop'},
        {'name': 'vi-IV-I-V', 'degrees': [6, 4, 1, 5], 'style': 'pop'},
        {'name': 'I-V-vi-iii-IV', 'degrees': [1, 5, 6, 3, 4], 'style': 'pop'},
        {'name': 'ii-V-I-VI', 'degrees': [2, 5, 1, 6], 'style': 'jazz'},
        {'name': 'I-vi-ii-V', 'degrees': [1, 6, 2, 5], 'style': 'jazz'},
        {'name': 'iii-vi-ii-V', 'degrees': [3, 6, 2, 5], 'style': 'jazz'},
        {'name': 'I-bVII-IV', 'degrees': [1, 7, 4], 'style': 'rock'},
        {'name': 'i-bVII-bVI-V', 'degrees': [1, 7, 6, 5], 'style': 'rock'},
        {'name': '12-bar-blues', 'degrees': [1, 1, 1, 1, 4, 4, 1, 1, 5, 4, 1, 5], 'style': 'blues'},
    ]

    # Famous songs with progressions
    SONGS = [
        {'title': 'House of the Rising Sun', 'artist': 'The Animals',
         'progression': ['Am', 'C', 'D', 'F', 'Am', 'C', 'E', 'E']},
        {'title': 'Wonderwall', 'artist': 'Oasis',
         'progression': ['Em', 'G', 'D', 'A']},
        {'title': 'Let It Be', 'artist': 'The Beatles',
         'progression': ['C', 'G', 'Am', 'F']},
        {'title': 'No Woman No Cry', 'artist': 'Bob Marley',
         'progression': ['C', 'G', 'Am', 'F']},
        {'title': 'With or Without You', 'artist': 'U2',
         'progression': ['D', 'A', 'Bm', 'G']},
        {'title': 'Autumn Leaves', 'artist': 'Jazz Standard',
         'progression': ['Am7', 'D7', 'Gmaj7', 'Cmaj7', 'F#m7b5', 'B7', 'Em']},
        {'title': 'All of Me', 'artist': 'Jazz Standard',
         'progression': ['C', 'E7', 'A7', 'Dm7', 'E7', 'Am7', 'D7', 'Dm7', 'G7', 'C']},
        {'title': 'Hotel California', 'artist': 'Eagles',
         'progression': ['Bm', 'F#', 'A', 'E', 'G', 'D', 'Em', 'F#']},
        {'title': 'Stairway to Heaven', 'artist': 'Led Zeppelin',
         'progression': ['Am', 'G#aug', 'C/G', 'D/F#', 'Fmaj7', 'G', 'Am']},
        {'title': 'Hallelujah', 'artist': 'Leonard Cohen',
         'progression': ['C', 'Am', 'C', 'Am', 'F', 'G', 'C', 'G']},
    ]

    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        print(f"[ROXY.GRAPH] Connected to Neo4j at {uri}")

    def close(self):
        self.driver.close()

    def clear_database(self):
        """Clear all existing data."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("[ROXY.GRAPH] Database cleared")

    def create_indexes(self):
        """Create indexes for fast lookups."""
        with self.driver.session() as session:
            # Chord index
            session.run("CREATE INDEX chord_name IF NOT EXISTS FOR (c:Chord) ON (c.name)")
            session.run("CREATE INDEX chord_root IF NOT EXISTS FOR (c:Chord) ON (c.root)")

            # Scale index
            session.run("CREATE INDEX scale_name IF NOT EXISTS FOR (s:Scale) ON (s.name)")

            # Note index
            session.run("CREATE INDEX note_name IF NOT EXISTS FOR (n:Note) ON (n.name)")

            # Song index
            session.run("CREATE INDEX song_title IF NOT EXISTS FOR (s:Song) ON (s.title)")

            print("[ROXY.GRAPH] Indexes created")

    def create_notes(self):
        """Create all 12 notes as nodes."""
        with self.driver.session() as session:
            for i, note in enumerate(self.NOTES):
                flat_equiv = self.FLAT_NOTES[i]
                session.run(
                    """
                    CREATE (n:Note {
                        name: $name,
                        flat_name: $flat_name,
                        midi_base: $midi_base,
                        semitones: $semitones
                    })
                    """,
                    name=note,
                    flat_name=flat_equiv,
                    midi_base=60 + i,  # C4 = 60
                    semitones=i
                )
            print(f"[ROXY.GRAPH] Created {len(self.NOTES)} notes")

    def create_chords(self):
        """Create all chord nodes."""
        count = 0
        with self.driver.session() as session:
            for root_idx, root in enumerate(self.NOTES):
                for quality, intervals in self.CHORD_FORMULAS.items():
                    # Calculate notes in chord
                    chord_notes = [self.NOTES[(root_idx + i) % 12] for i in intervals]
                    chord_name = f"{root}{quality}" if quality != 'major' else root

                    session.run(
                        """
                        CREATE (c:Chord {
                            name: $name,
                            root: $root,
                            quality: $quality,
                            notes: $notes,
                            intervals: $intervals
                        })
                        """,
                        name=chord_name,
                        root=root,
                        quality=quality,
                        notes=chord_notes,
                        intervals=intervals
                    )
                    count += 1

        print(f"[ROXY.GRAPH] Created {count} chords")

    def create_scales(self):
        """Create all scale nodes."""
        count = 0
        with self.driver.session() as session:
            for root_idx, root in enumerate(self.NOTES):
                for scale_name, intervals in self.SCALE_FORMULAS.items():
                    scale_notes = [self.NOTES[(root_idx + i) % 12] for i in intervals]

                    session.run(
                        """
                        CREATE (s:Scale {
                            name: $name,
                            root: $root,
                            type: $type,
                            notes: $notes,
                            intervals: $intervals
                        })
                        """,
                        name=f"{root} {scale_name}",
                        root=root,
                        type=scale_name,
                        notes=scale_notes,
                        intervals=intervals
                    )
                    count += 1

        print(f"[ROXY.GRAPH] Created {count} scales")

    def create_chord_relationships(self):
        """Create LEADS_TO relationships between chords."""
        count = 0
        with self.driver.session() as session:
            # Common chord movements
            movements = [
                # V -> I (strongest resolution)
                ('V', 'I', 1.0),
                ('V7', 'I', 1.0),
                # IV -> I (plagal)
                ('IV', 'I', 0.9),
                # ii -> V
                ('ii', 'V', 0.95),
                ('ii7', 'V7', 0.95),
                # vi -> ii
                ('vi', 'ii', 0.8),
                # I -> IV
                ('I', 'IV', 0.85),
                # I -> V
                ('I', 'V', 0.85),
                # I -> vi
                ('I', 'vi', 0.8),
            ]

            # For each key, create relationships
            for key_idx, key in enumerate(self.NOTES):
                for from_deg, to_deg, strength in movements:
                    # Map degree to chord
                    from_chord = self._degree_to_chord(key_idx, from_deg)
                    to_chord = self._degree_to_chord(key_idx, to_deg)

                    if from_chord and to_chord:
                        session.run(
                            """
                            MATCH (a:Chord {name: $from_chord})
                            MATCH (b:Chord {name: $to_chord})
                            CREATE (a)-[:LEADS_TO {strength: $strength, key: $key}]->(b)
                            """,
                            from_chord=from_chord,
                            to_chord=to_chord,
                            strength=strength,
                            key=key
                        )
                        count += 1

        print(f"[ROXY.GRAPH] Created {count} chord relationships")

    def _degree_to_chord(self, key_idx: int, degree: str) -> str:
        """Convert scale degree to chord name."""
        degree_map = {
            'I': (0, 'major'), 'i': (0, 'minor'),
            'II': (2, 'major'), 'ii': (2, 'minor'), 'ii7': (2, 'min7'),
            'III': (4, 'major'), 'iii': (4, 'minor'),
            'IV': (5, 'major'), 'iv': (5, 'minor'),
            'V': (7, 'major'), 'V7': (7, '7'), 'v': (7, 'minor'),
            'VI': (9, 'major'), 'vi': (9, 'minor'),
            'VII': (11, 'major'), 'vii': (11, 'dim'), 'viio': (11, 'dim'),
        }

        if degree not in degree_map:
            return None

        interval, quality = degree_map[degree]
        root = self.NOTES[(key_idx + interval) % 12]

        if quality == 'major':
            return root
        else:
            return f"{root}{quality}"

    def create_songs(self):
        """Create song nodes with progression relationships."""
        with self.driver.session() as session:
            for song in self.SONGS:
                # Create song node
                session.run(
                    """
                    CREATE (s:Song {
                        title: $title,
                        artist: $artist,
                        progression: $progression
                    })
                    """,
                    title=song['title'],
                    artist=song['artist'],
                    progression=song['progression']
                )

                # Link to chords
                for i, chord_name in enumerate(song['progression']):
                    # Normalize chord name (handle slash chords, etc.)
                    base_chord = chord_name.split('/')[0]

                    session.run(
                        """
                        MATCH (s:Song {title: $title})
                        MATCH (c:Chord {name: $chord})
                        CREATE (s)-[:USES_CHORD {position: $pos}]->(c)
                        """,
                        title=song['title'],
                        chord=base_chord,
                        pos=i
                    )

        print(f"[ROXY.GRAPH] Created {len(self.SONGS)} songs")

    def create_progressions(self):
        """Create progression pattern nodes."""
        with self.driver.session() as session:
            for prog in self.PROGRESSIONS:
                session.run(
                    """
                    CREATE (p:Progression {
                        name: $name,
                        degrees: $degrees,
                        style: $style
                    })
                    """,
                    name=prog['name'],
                    degrees=prog['degrees'],
                    style=prog['style']
                )

        print(f"[ROXY.GRAPH] Created {len(self.PROGRESSIONS)} progressions")

    def import_all(self):
        """Import complete music theory graph."""
        print("[ROXY.GRAPH] Starting full import...")

        self.clear_database()
        self.create_indexes()
        self.create_notes()
        self.create_chords()
        self.create_scales()
        self.create_chord_relationships()
        self.create_songs()
        self.create_progressions()

        # Get stats
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
                """
            )
            print("\n[ROXY.GRAPH] Import complete:")
            total = 0
            for record in result:
                print(f"  {record['label']}: {record['count']}")
                total += record['count']
            print(f"  TOTAL: {total} nodes")

    def query_leads_to(self, chord: str) -> List[str]:
        """Find chords that the given chord leads to."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (a:Chord {name: $chord})-[r:LEADS_TO]->(b:Chord)
                RETURN b.name as chord, r.strength as strength
                ORDER BY r.strength DESC
                """,
                chord=chord
            )
            return [(r['chord'], r['strength']) for r in result]

    def query_song_progression(self, title: str) -> List[str]:
        """Get chord progression for a song."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (s:Song {title: $title})-[u:USES_CHORD]->(c:Chord)
                RETURN c.name as chord, u.position as pos
                ORDER BY u.position
                """,
                title=title
            )
            return [r['chord'] for r in result]


def main():
    graph = MusicTheoryGraph()

    try:
        graph.import_all()

        # Demo queries
        print("\n[ROXY.GRAPH] Demo queries:")

        # What chords does Am lead to?
        leads_to = graph.query_leads_to("Am")
        print(f"\nAm leads to: {leads_to}")

        # House of the Rising Sun progression
        progression = graph.query_song_progression("House of the Rising Sun")
        print(f"\nHouse of the Rising Sun: {progression}")

    finally:
        graph.close()


if __name__ == "__main__":
    main()
