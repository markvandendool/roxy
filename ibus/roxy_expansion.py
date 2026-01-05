#!/usr/bin/env python3
"""
Rocky System - iBus Text Expansion Engine
Story: RAF-011
Target: /rx → ROXY commands via iBus input method

Expands short triggers into full commands or invokes ROXY actions.
"""

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Dict, Optional, List
from dataclasses import dataclass
import threading

try:
    from dbus_next.aio import MessageBus
    from dbus_next import BusType, Variant
except ImportError:
    print("ERROR: dbus-next not installed")
    print("Run: pip install dbus-next")
    exit(1)

# Configuration
ROXY_CONFIG = Path.home() / ".roxy" / "config"
EXPANSIONS_FILE = ROXY_CONFIG / "expansions.json"
SHM_PATH = "/dev/shm/roxy_brain"


@dataclass
class Expansion:
    """Text expansion definition."""
    trigger: str
    replacement: str
    action: Optional[str] = None  # Optional shell command or roxy action
    description: str = ""


class RoxyExpansionEngine:
    """
    iBus-integrated text expansion for ROXY.

    Monitors keyboard input and expands triggers like:
    - /rx → Opens ROXY command palette
    - /rxh → ROXY help
    - /rxs → ROXY status
    - Custom user expansions
    """

    DEFAULT_EXPANSIONS = [
        Expansion("/rx", "", "roxy:activate", "Activate ROXY"),
        Expansion("/rxh", "", "roxy:help", "ROXY Help"),
        Expansion("/rxs", "", "roxy:status", "ROXY Status"),
        Expansion("/rxp", "", "roxy:practice", "Start Practice Session"),
        Expansion("/rxl", "", "roxy:learn", "Show Learning Progress"),
        Expansion("@@now", "", "insert:datetime", "Insert current date/time"),
        Expansion("@@date", "", "insert:date", "Insert current date"),
        Expansion("@@sig", "- Mark (via ROXY)", None, "Insert signature"),
        Expansion("@@shrug", r"¯\_(ツ)_/¯", None, "Shrug emoticon"),
    ]

    def __init__(self):
        self.expansions: Dict[str, Expansion] = {}
        self.running = False
        self.bus: Optional[MessageBus] = None
        self.callbacks: Dict[str, Callable] = {}

        # Load expansions
        self._load_expansions()

        print(f"[ROXY.IBUS] Expansion engine initialized")
        print(f"[ROXY.IBUS] Loaded {len(self.expansions)} expansions")

    def _load_expansions(self):
        """Load expansions from config or use defaults."""
        ROXY_CONFIG.mkdir(parents=True, exist_ok=True)

        # Start with defaults
        for exp in self.DEFAULT_EXPANSIONS:
            self.expansions[exp.trigger] = exp

        # Load custom expansions
        if EXPANSIONS_FILE.exists():
            try:
                with open(EXPANSIONS_FILE) as f:
                    custom = json.load(f)
                for item in custom:
                    exp = Expansion(**item)
                    self.expansions[exp.trigger] = exp
                print(f"[ROXY.IBUS] Loaded {len(custom)} custom expansions")
            except Exception as e:
                print(f"[ROXY.IBUS] Error loading expansions: {e}")
        else:
            # Create default config
            self._save_expansions()

    def _save_expansions(self):
        """Save current expansions to config."""
        custom = [
            {
                "trigger": e.trigger,
                "replacement": e.replacement,
                "action": e.action,
                "description": e.description,
            }
            for e in self.expansions.values()
            if e not in self.DEFAULT_EXPANSIONS
        ]

        with open(EXPANSIONS_FILE, "w") as f:
            json.dump(custom, f, indent=2)

    def add_expansion(self, trigger: str, replacement: str,
                     action: Optional[str] = None, description: str = ""):
        """Add a new expansion."""
        exp = Expansion(trigger, replacement, action, description)
        self.expansions[trigger] = exp
        self._save_expansions()
        print(f"[ROXY.IBUS] Added expansion: {trigger}")

    def remove_expansion(self, trigger: str) -> bool:
        """Remove an expansion."""
        if trigger in self.expansions:
            del self.expansions[trigger]
            self._save_expansions()
            print(f"[ROXY.IBUS] Removed expansion: {trigger}")
            return True
        return False

    def register_action(self, action_name: str, callback: Callable):
        """Register a callback for an action."""
        self.callbacks[action_name] = callback
        print(f"[ROXY.IBUS] Registered action: {action_name}")

    def process_input(self, text: str) -> Optional[str]:
        """
        Process input text and return expansion if matched.

        Returns None if no expansion matched.
        """
        for trigger, expansion in self.expansions.items():
            if text.endswith(trigger):
                # Found a match
                print(f"[ROXY.IBUS] Triggered: {trigger}")

                # Execute action if present
                if expansion.action:
                    self._execute_action(expansion.action)
                    # Return empty to delete trigger
                    return ""

                # Return replacement
                return expansion.replacement

        return None

    def _execute_action(self, action: str):
        """Execute an expansion action."""
        print(f"[ROXY.IBUS] Executing action: {action}")

        if action.startswith("roxy:"):
            roxy_cmd = action.split(":")[1]
            self._send_roxy_command(roxy_cmd)

        elif action.startswith("insert:"):
            insert_type = action.split(":")[1]
            self._handle_insert(insert_type)

        elif action.startswith("shell:"):
            shell_cmd = action.split(":", 1)[1]
            subprocess.Popen(shell_cmd, shell=True)

        elif action in self.callbacks:
            self.callbacks[action]()

    def _send_roxy_command(self, cmd: str):
        """Send command to ROXY via shared memory."""
        if not os.path.exists(SHM_PATH):
            print(f"[ROXY.IBUS] ROXY brain not running")
            return

        # Import shm module
        import sys
        sys.path.insert(0, str(Path.home() / ".roxy" / "ipc"))
        try:
            from shm_brain import RoxyShmBrain
            brain = RoxyShmBrain(create=False)
            brain.write_json(brain.MSG_COMMAND, {"cmd": cmd})
            brain.cleanup()
            print(f"[ROXY.IBUS] Sent to ROXY: {cmd}")
        except Exception as e:
            print(f"[ROXY.IBUS] Failed to send command: {e}")

    def _handle_insert(self, insert_type: str):
        """Handle insert actions."""
        from datetime import datetime

        if insert_type == "datetime":
            text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif insert_type == "date":
            text = datetime.now().strftime("%Y-%m-%d")
        elif insert_type == "time":
            text = datetime.now().strftime("%H:%M:%S")
        else:
            return

        # Use xdotool to type the text
        subprocess.run(["xdotool", "type", "--clearmodifiers", text])

    async def connect_ibus(self):
        """Connect to iBus daemon."""
        try:
            # Connect to iBus bus
            ibus_address = os.environ.get("IBUS_ADDRESS")
            if not ibus_address:
                # Try to get from ibus daemon
                result = subprocess.run(
                    ["ibus", "address"],
                    capture_output=True,
                    text=True
                )
                ibus_address = result.stdout.strip()

            if ibus_address:
                print(f"[ROXY.IBUS] Connecting to iBus: {ibus_address}")
                # Note: Full iBus integration requires custom input method
                # This is a simplified approach using monitoring

            self.bus = await MessageBus(bus_type=BusType.SESSION).connect()
            print(f"[ROXY.IBUS] Connected to session bus")

        except Exception as e:
            print(f"[ROXY.IBUS] iBus connection failed: {e}")

    async def start_monitor(self):
        """Start input monitoring (fallback mode)."""
        self.running = True
        print("[ROXY.IBUS] Starting input monitor (fallback mode)")
        print("[ROXY.IBUS] Use /rx commands in terminal for expansion")

        # In fallback mode, we watch stdin or use evdev
        # Full iBus integration requires a custom input method engine

        while self.running:
            await asyncio.sleep(0.1)

    def stop(self):
        """Stop the expansion engine."""
        self.running = False
        if self.bus:
            self.bus.disconnect()


class TerminalExpander:
    """
    Terminal-based expansion for shell integration.

    Works with bash/zsh via readline or as a wrapper.
    """

    def __init__(self, engine: RoxyExpansionEngine):
        self.engine = engine
        self.buffer = ""

    def process_char(self, char: str) -> Optional[str]:
        """Process a character and return expansion if triggered."""
        self.buffer += char

        # Check for expansion triggers (usually end with space or enter)
        if char in [" ", "\n", "\t"]:
            # Check the word before the trigger
            word = self.buffer.rstrip()
            expansion = self.engine.process_input(word)

            if expansion is not None:
                self.buffer = ""
                return expansion + char

            self.buffer = ""

        # Keep buffer manageable
        if len(self.buffer) > 100:
            self.buffer = self.buffer[-50:]

        return None

    def get_completions(self, prefix: str) -> List[str]:
        """Get expansion completions for a prefix."""
        return [
            exp.trigger
            for exp in self.engine.expansions.values()
            if exp.trigger.startswith(prefix)
        ]


def create_bash_integration():
    """Generate bash integration script."""
    script = '''
# ROXY Text Expansion - Bash Integration
# Add to ~/.bashrc: source ~/.roxy/ibus/bash_expansion.sh

_roxy_expand() {
    local word="${READLINE_LINE##* }"
    local result

    case "$word" in
        /rx)
            # Activate ROXY
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:activate
            READLINE_LINE="${READLINE_LINE%$word}"
            ;;
        /rxh)
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:help
            READLINE_LINE="${READLINE_LINE%$word}"
            ;;
        /rxs)
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:status
            READLINE_LINE="${READLINE_LINE%$word}"
            ;;
        @@now)
            result=$(date "+%Y-%m-%d %H:%M:%S")
            READLINE_LINE="${READLINE_LINE%$word}$result"
            READLINE_POINT=${#READLINE_LINE}
            ;;
        @@date)
            result=$(date "+%Y-%m-%d")
            READLINE_LINE="${READLINE_LINE%$word}$result"
            READLINE_POINT=${#READLINE_LINE}
            ;;
    esac
}

# Bind to Tab key (after completion)
bind -x '"\C-e": _roxy_expand'
echo "[ROXY] Text expansion loaded. Use Ctrl+E to expand triggers."
'''

    output_path = ROXY_CONFIG.parent / "ibus" / "bash_expansion.sh"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(script)

    print(f"[ROXY.IBUS] Created bash integration: {output_path}")
    return output_path


def create_zsh_integration():
    """Generate zsh integration script."""
    script = '''
# ROXY Text Expansion - Zsh Integration
# Add to ~/.zshrc: source ~/.roxy/ibus/zsh_expansion.zsh

_roxy_expand() {
    local word="${LBUFFER##* }"
    local result

    case "$word" in
        /rx)
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:activate
            LBUFFER="${LBUFFER%$word}"
            ;;
        /rxh)
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:help
            LBUFFER="${LBUFFER%$word}"
            ;;
        /rxs)
            python3 ~/.roxy/ibus/roxy_expansion.py --action roxy:status
            LBUFFER="${LBUFFER%$word}"
            ;;
        @@now)
            result=$(date "+%Y-%m-%d %H:%M:%S")
            LBUFFER="${LBUFFER%$word}$result"
            ;;
        @@date)
            result=$(date "+%Y-%m-%d")
            LBUFFER="${LBUFFER%$word}$result"
            ;;
        *)
            zle expand-or-complete
            return
            ;;
    esac
    zle redisplay
}

zle -N _roxy_expand
bindkey '^E' _roxy_expand
echo "[ROXY] Text expansion loaded. Use Ctrl+E to expand triggers."
'''

    output_path = ROXY_CONFIG.parent / "ibus" / "zsh_expansion.zsh"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(script)

    print(f"[ROXY.IBUS] Created zsh integration: {output_path}")
    return output_path


async def main():
    """Run the expansion engine."""
    import sys

    engine = RoxyExpansionEngine()

    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--action" and len(sys.argv) > 2:
            engine._execute_action(sys.argv[2])
            return
        elif sys.argv[1] == "--install":
            create_bash_integration()
            create_zsh_integration()
            print("\n[ROXY.IBUS] Shell integration installed!")
            print("Add to your shell rc file:")
            print("  Bash: source ~/.roxy/ibus/bash_expansion.sh")
            print("  Zsh:  source ~/.roxy/ibus/zsh_expansion.zsh")
            return
        elif sys.argv[1] == "--list":
            print("\n[ROXY.IBUS] Available expansions:")
            for trigger, exp in engine.expansions.items():
                action = f" -> {exp.action}" if exp.action else ""
                repl = f" -> '{exp.replacement}'" if exp.replacement else ""
                print(f"  {trigger}{action}{repl} ({exp.description})")
            return

    # Run daemon mode
    await engine.connect_ibus()
    await engine.start_monitor()


if __name__ == "__main__":
    asyncio.run(main())
