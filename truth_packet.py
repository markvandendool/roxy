#!/usr/bin/env python3
"""
TruthPacket Generator - Single source of ground truth for ROXY's reality awareness.

CHIEF DIRECTIVE: ROXY must be grounded in reality. This module generates a structured
JSON packet from REAL system calls - no hallucination, no inference, no RAG.

The TruthPacket ALWAYS wins over any reference material or RAG context.
"""

import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

ROXY_DIR = Path.home() / ".roxy"
STATE_DIR = ROXY_DIR / "state"
TRUTH_PACKET_FILE = STATE_DIR / "truth_packet.json"


def get_git_info(repo_path: Path = ROXY_DIR) -> Dict[str, Any]:
    """Get git repository state via real git commands."""
    git_info = {
        "repo_root": str(repo_path),
        "branch": "unknown",
        "head_sha": "unknown",
        "head_sha_short": "unknown",
        "dirty": None,
        "last_commit_subject": "",
        "last_commit_date": "",
        "error": None
    }

    try:
        # Branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2, cwd=repo_path
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()

        # Full SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=2, cwd=repo_path
        )
        if result.returncode == 0:
            git_info["head_sha"] = result.stdout.strip()
            git_info["head_sha_short"] = git_info["head_sha"][:7]

        # Dirty status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=2, cwd=repo_path
        )
        if result.returncode == 0:
            git_info["dirty"] = bool(result.stdout.strip())

        # Last commit subject
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True, text=True, timeout=2, cwd=repo_path
        )
        if result.returncode == 0:
            git_info["last_commit_subject"] = result.stdout.strip()[:100]

        # Last commit date
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True, text=True, timeout=2, cwd=repo_path
        )
        if result.returncode == 0:
            git_info["last_commit_date"] = result.stdout.strip()

    except subprocess.TimeoutExpired:
        git_info["error"] = "git commands timed out"
    except FileNotFoundError:
        git_info["error"] = "git not found"
    except Exception as e:
        git_info["error"] = str(e)[:100]

    return git_info


def get_pool_info() -> Dict[str, Any]:
    """Get Ollama pool configuration and reachability."""
    pools = {
        "w5700x": {"url": None, "reachable": None, "port": None},
        "6900xt": {"url": None, "reachable": None, "port": None},
        "default": {"url": None, "reachable": None, "port": None}
    }

    # Read from environment or config
    w5700x_url = os.getenv("OLLAMA_W5700X_URL", "http://127.0.0.1:11434")
    fast_url = os.getenv("OLLAMA_6900XT_URL", "http://127.0.0.1:11435")
    default_url = os.getenv("OLLAMA_HOST", fast_url)

    pools["w5700x"]["url"] = w5700x_url
    pools["w5700x"]["port"] = 11434
    pools["6900xt"]["url"] = fast_url
    pools["6900xt"]["port"] = 11435
    pools["default"]["url"] = default_url

    # Quick reachability check (non-blocking, best effort)
    import urllib.request
    for pool_name, pool_data in pools.items():
        if pool_data["url"]:
            try:
                req = urllib.request.Request(f"{pool_data['url']}/api/version", method="GET")
                with urllib.request.urlopen(req, timeout=1) as resp:
                    pool_data["reachable"] = resp.status == 200
            except Exception:
                pool_data["reachable"] = False

    return pools


def get_service_ports() -> Dict[str, int]:
    """Get known service ports."""
    return {
        "roxy_core": 8766,
        "prometheus": 9091,
        "ollama_w5700x": 11434,
        "ollama_6900xt": 11435
    }


def get_roxy_version() -> str:
    """Get ROXY version from VERSION file or git tag."""
    version_file = ROXY_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Try git describe
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True, text=True, timeout=2, cwd=ROXY_DIR
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return "unknown"


def generate_truth_packet(
    include_pools: bool = True,
    include_git: bool = True,
    active_model: Optional[str] = None,
    active_pool: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a complete TruthPacket from real system state.

    This is the SINGLE SOURCE OF TRUTH for ROXY's reality awareness.
    When this conflicts with RAG/reference material, THIS WINS.
    """
    now = datetime.now()
    now_utc = datetime.now(timezone.utc)

    packet = {
        # Time - THE AUTHORITATIVE SOURCE
        "now_iso": now.isoformat(),
        "now_utc_iso": now_utc.isoformat(),
        "now_human": now.strftime("%A, %B %d, %Y at %H:%M:%S"),
        "now_date": now.strftime("%Y-%m-%d"),
        "now_time": now.strftime("%H:%M:%S"),
        "now_weekday": now.strftime("%A"),
        "now_month": now.strftime("%B"),
        "now_year": now.year,
        "now_day": now.day,
        "tz": str(now.astimezone().tzinfo),
        "tz_offset": now.strftime("%z"),
        "unix_timestamp": int(time.time()),

        # System
        "hostname": socket.gethostname(),
        "user": os.getenv("USER", os.getenv("USERNAME", "unknown")),
        "roxy_dir": str(ROXY_DIR),
        "roxy_version": get_roxy_version(),
        "pid": os.getpid(),

        # Service ports
        "service_ports": get_service_ports(),

        # Active model/pool (if known)
        "active_model": active_model or "auto",
        "active_pool": active_pool or "auto",

        # Generation metadata
        "_generated_at": now.isoformat(),
        "_packet_version": "1.0.0"
    }

    # Git info (optional but usually wanted)
    if include_git:
        packet["git"] = get_git_info()

    # Pool info (optional, includes network checks)
    if include_pools:
        packet["pools"] = get_pool_info()

    return packet


def save_truth_packet(packet: Optional[Dict[str, Any]] = None) -> Path:
    """Generate and save TruthPacket to state file for inspection."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if packet is None:
        packet = generate_truth_packet()

    with open(TRUTH_PACKET_FILE, 'w') as f:
        json.dump(packet, f, indent=2, default=str)

    return TRUTH_PACKET_FILE


def load_truth_packet() -> Optional[Dict[str, Any]]:
    """Load last saved TruthPacket from state file."""
    if TRUTH_PACKET_FILE.exists():
        try:
            with open(TRUTH_PACKET_FILE) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def format_truth_for_prompt(packet: Dict[str, Any]) -> str:
    """
    Format TruthPacket for inclusion in LLM prompt.

    This is injected BEFORE any RAG context and marked as AUTHORITATIVE.
    """
    git = packet.get("git", {})

    return f"""=== TRUTH PACKET (AUTHORITATIVE - OVERRIDES ALL OTHER SOURCES) ===
Current Date/Time: {packet.get('now_human', 'unknown')}
Timezone: {packet.get('tz', 'unknown')} ({packet.get('tz_offset', '')})
ISO Timestamp: {packet.get('now_iso', 'unknown')}

System: {packet.get('hostname', 'unknown')} (user: {packet.get('user', 'unknown')})
ROXY Version: {packet.get('roxy_version', 'unknown')}
ROXY Directory: {packet.get('roxy_dir', 'unknown')}

Git Repository:
  Branch: {git.get('branch', 'unknown')}
  Commit: {git.get('head_sha_short', 'unknown')} ({git.get('last_commit_subject', '')[:50]})
  Status: {'dirty (uncommitted changes)' if git.get('dirty') else 'clean'}

Active Model: {packet.get('active_model', 'auto')}
Active Pool: {packet.get('active_pool', 'auto')}

RULE: If ANY information below (reference material, RAG context, historical docs)
conflicts with the TRUTH PACKET above, the TRUTH PACKET is CORRECT.
=== END TRUTH PACKET ==="""


def load_identity() -> str:
    """
    Load ROXY's identity document from ROXY_IDENTITY.md.

    This is the CANONICAL source of ROXY's personality and behavior rules.
    The system prompt should import this rather than hardcoding identity.

    Returns:
        str: Identity document contents, or fallback if file not found
    """
    identity_file = ROXY_DIR / "ROXY_IDENTITY.md"

    if identity_file.exists():
        try:
            content = identity_file.read_text()
            # Extract just the content, skip markdown header
            return content
        except Exception as e:
            pass

    # Fallback identity if file is missing
    return """You are ROXY, an advanced AI assistant created by Mark for MindSong operations.
You are warm, witty, and efficient - like JARVIS. You focus on operations, business systems,
and coding. You are proactive and anticipatory. You never hallucinate facts and always
defer to the Truth Packet for current time/date and system state."""


def get_system_prompt_header() -> str:
    """
    Get the complete system prompt header including identity and hard rules.

    This is the FIRST section of any prompt to ROXY.
    """
    identity = load_identity()

    return f"""{identity}

## Active Session Rules

The following rules are MANDATORY for this session:

1. **TRUTH PACKET IS LAW**: The Truth Packet below contains REAL data from system calls.
   It is AUTHORITATIVE. If ANY other source conflicts, the Truth Packet wins.

2. **DATES IN REFERENCE MATERIAL ARE HISTORICAL**: Reference material may mention dates
   from when it was indexed. These are NOT the current date. Use Truth Packet for current time.

3. **ACKNOWLEDGE UNCERTAINTY**: If you don't know something, say "I'm not sure" rather
   than guessing. It's better to be honest than to hallucinate."""


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        path = save_truth_packet()
        print(f"TruthPacket saved to: {path}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--identity":
        print(load_identity())
    elif len(sys.argv) > 1 and sys.argv[1] == "--header":
        print(get_system_prompt_header())
    else:
        packet = generate_truth_packet()
        print(json.dumps(packet, indent=2, default=str))
