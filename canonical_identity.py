# ROXY Canonical Identity Configuration
# This file defines the ground-truth identity for ROXY

CANONICAL_USER_ID = "mark-roxy-canonical"
CANONICAL_NAME = "Mark"
CANONICAL_ROLE = "CEO of MindSong Studios"
CANONICAL_EMAIL = "mark@mindsongstudios.com"

# Aliases that also refer to the canonical user
USER_ALIASES = [
    "mark",
    "Mark",
    "MARK",
    "mr. mark",
    "mister mark",
]

# Preferred display name
PREFERRED_DISPLAY = "Mark"

# Identity categories and their canonical values
IDENTITY_PROFILE = {
    "name": CANONICAL_NAME,
    "role": CANONICAL_ROLE,
    "title": CANONICAL_ROLE,
    "organization": "MindSong Studios",
    "email": CANONICAL_EMAIL,
}

# Production context
PRODUCTION_PROFILE = {
    "render_queue": "SkyBeam render queue with 5 videos pending",
    "studio": "MindSong Studios",
    "focus": "music production and video creation",
    "tools": ["SkyBeam", "SkyDream", "ShotCaller", "StackKraft", "MimiQ", "MQQC", "Luno", "Rocky AI"],
}
