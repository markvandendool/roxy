#!/usr/bin/env python3
"""
Query Detection Module - Dependency-free query classifiers

Provides:
- is_time_date_query(): Detect time/date queries that should skip RAG
- is_repo_query(): Detect repository/git queries that should use TruthPacket

This module is dependency-free (only re) to avoid circular imports.
Used by: streaming.py, roxy_commands.py

Created: 2026-01-11 (extracted from streaming.py to avoid circular imports)
"""

import re

# Time/date query patterns (Directive #3: skip RAG for time queries)
TIME_DATE_PATTERNS = [
    # Direct time questions
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:time|date|day|month|year)\b",
    r"\bwhat\s+time\s+is\s+it\b",
    r"\bwhat\s+day\s+(?:is\s+)?(?:it|today)\b",
    r"\bwhat(?:'s|\s+is)\s+today(?:'s)?\s+date\b",
    r"\btoday(?:'s)?\s+date\b",
    r"\bcurrent\s+(?:time|date|day|timestamp)\b",
    # Time-relative questions
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:weekday|week\s+day)\b",
    r"\bis\s+it\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bwhat\s+(?:month|year)\s+(?:is\s+)?(?:it|this)\b",
    # Time now patterns
    r"\bright\s+now\b.*\b(?:time|date)\b",
    r"\b(?:time|date)\b.*\bright\s+now\b",
    # Tell me the time
    r"\btell\s+me\s+(?:the\s+)?(?:current\s+)?(?:time|date)\b",
    # Timezone/UTC queries
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?timezone\b",
    r"\btimezone\s+(?:are\s+)?(?:you\s+)?(?:using|in)\b",
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:utc|gmt)\s+offset\b",
    r"\butc\s+offset\b",
    # Unix timestamp / epoch
    r"\bunix\s+timestamp\b",
    r"\bepoch\s+(?:time|timestamp|seconds)\b",
    r"\bseconds\s+since\s+epoch\b",
    # ISO-8601 format requests
    r"\biso[-\s]?8601\b",
    r"\bgive\s+(?:me\s+)?(?:the\s+)?.*\bdate\b",
    # UTC conversion requests
    r"\bconvert\s+(?:the\s+)?(?:current\s+)?(?:local\s+)?time\s+to\s+utc\b",
    r"\b(?:current|local)\s+time\s+(?:to|in)\s+utc\b",
    r"\bshow\s+(?:me\s+)?(?:both\s+)?(?:local\s+and\s+)?utc\b",
    # Simple single-word queries
    r"^(?:time|date)$",
    r"^\s*(?:the\s+)?time\s*$",
    r"^\s*(?:the\s+)?date\s*$",
]

_TIME_DATE_REGEX = re.compile("|".join(TIME_DATE_PATTERNS), re.IGNORECASE)


def is_time_date_query(query: str) -> bool:
    """
    Detect if query is asking about current time/date.

    These queries should SKIP RAG entirely (Directive #3) because:
    1. RAG context may contain historical dates that confuse the model
    2. Time/date answers come solely from TruthPacket
    3. No indexed content is relevant for "what time is it"

    Returns:
        True if query is about time/date and should skip RAG
    """
    return bool(_TIME_DATE_REGEX.search(query))


# Repo/git query patterns that should use TruthPacket + git (Directive #5)
REPO_PATTERNS = [
    r"\bwhat\s+(?:is\s+)?(?:the\s+)?(?:current\s+)?(?:branch|commit|sha|head)\b",
    r"\bwhich\s+branch\b",
    r"\bgit\s+(?:status|branch|log|diff)\b",
    r"\bare\s+(?:there\s+)?(?:any\s+)?(?:uncommitted|unstaged|modified)\s+(?:changes|files)\b",
    r"\bwhat\s+(?:was\s+)?(?:the\s+)?last\s+commit\b",
    r"\bis\s+(?:the\s+)?(?:repo|repository|working\s+tree)\s+(?:clean|dirty)\b",
    r"\bwhat\s+(?:commit|sha)\s+(?:are\s+)?(?:we\s+)?on\b",
    # Working tree status
    r"\bworking\s+tree\s+(?:clean|dirty|status)\b",
    # Remote/origin queries
    r"\bremote\s+(?:origin\s+)?url\b",
    r"\borigin\s+url\b",
    r"\bgit\s+remote\b",
    # Commit history queries
    r"\blast\s+\d+\s+commits?\b",
    r"\bshow\s+(?:the\s+)?(?:last\s+)?\d+\s+commits?\b",
    r"\bcommits?\s+(?:that\s+)?touched\b",
    r"\bcommit\s+date\b",
    r"\bhead\s+commit\s+date\b",
    r"\bauthor\s+date\b",
]

_REPO_REGEX = re.compile("|".join(REPO_PATTERNS), re.IGNORECASE)


def is_repo_query(query: str) -> bool:
    """
    Detect if query is asking about repository state (Directive #5).

    These queries should use TruthPacket.git and/or direct git commands.

    Returns:
        True if query is about repo/git state
    """
    return bool(_REPO_REGEX.search(query))


if __name__ == "__main__":
    # Test cases
    test_queries = [
        ("what time is it", True, False),
        ("what is today's date", True, False),
        ("current time", True, False),
        ("time", True, False),
        ("date", True, False),
        ("what branch are we on", False, True),
        ("git status", False, True),
        ("how do I configure ollama", False, False),
        ("explain the codebase", False, False),
    ]

    print("Query Detection Test")
    print("=" * 60)

    for query, expect_time, expect_repo in test_queries:
        is_time = is_time_date_query(query)
        is_repo = is_repo_query(query)
        time_ok = is_time == expect_time
        repo_ok = is_repo == expect_repo

        status = "PASS" if (time_ok and repo_ok) else "FAIL"
        print(f"{status}: '{query}'")
        print(f"  time={is_time} (expect {expect_time}), repo={is_repo} (expect {expect_repo})")
