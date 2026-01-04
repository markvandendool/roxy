#!/usr/bin/env python3
"""
ROXY Persistent Daemon
Extends roxy_assistant_v2.py with always-on capabilities

Features:
- Always-running background service
- Global hotkey support (Ctrl+Space)
- System tray integration
- Auto-indexing of all projects to ChromaDB
- Proactive monitoring and suggestions

Part of LUNA-000 CITADEL -> Making ROXY truly persistent like JARVIS
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime
from threading import Thread, Event
import subprocess

# Import existing ROXY assistant
sys.path.insert(0, str(Path.home() / ".roxy"))
try:
    from roxy_assistant_v2 import RoxyAssistant
    HAS_ASSISTANT = True
except ImportError:
    HAS_ASSISTANT = False
    print("[WARN] roxy_assistant_v2.py not found - voice disabled")

# Global hotkey support
try:
    from pynput import keyboard
    HAS_HOTKEY = True
except ImportError:
    HAS_HOTKEY = False
    print("[WARN] pynput not available - hotkey disabled (install: pip install pynput)")

# Logging setup
LOG_DIR = Path.home() / ".roxy" / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"roxy_daemon_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("roxy-daemon")

class RoxyDaemon:
    """
    Persistent ROXY daemon that runs 24/7
    Extends existing ROXY assistant with always-on capabilities
    """
    
    def __init__(self):
        self.running = Event()
        self.roxy_assistant = None
        self.hotkey_listener = None
        self.monitoring_thread = None
        
        logger.info("=" * 60)
        logger.info("ROXY DAEMON INITIALIZING")
        logger.info("=" * 60)
        
    def start(self):
        """Start the daemon"""
        self.running.set()
        
        # Initialize voice assistant if available
        if HAS_ASSISTANT:
            try:
                logger.info("Initializing voice assistant...")
                self.roxy_assistant = RoxyAssistant()
                logger.info("✓ Voice assistant ready")
            except Exception as e:
                logger.error(f"Failed to initialize voice assistant: {e}")
        
        # Start global hotkey listener
        if HAS_HOTKEY:
            self._start_hotkey_listener()
        
        # Start monitoring thread
        self.monitoring_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("✓ Monitoring thread started")
        
        # Index projects to ChromaDB (background)
        Thread(target=self._index_projects, daemon=True).start()
        
        logger.info("=" * 60)
        logger.info("ROXY DAEMON RUNNING - Press Ctrl+C to stop")
        logger.info("Hotkey: Ctrl+Space")
        logger.info("Voice: 'Hey Roxy'")
        logger.info("=" * 60)
        
        # Keep main thread alive
        try:
            while self.running.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received")
            self.stop()
    
    def stop(self):
        """Graceful shutdown"""
        logger.info("Stopping ROXY daemon...")
        self.running.clear()
        
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        logger.info("ROXY daemon stopped")
        
    def _start_hotkey_listener(self):
        """Listen for Ctrl+Space global hotkey"""
        try:
            def on_activate():
                logger.info("Hotkey activated (Ctrl+Space)")
                self._show_chat_interface()
            
            # Ctrl+Space hotkey
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse('<ctrl>+<space>'),
                on_activate
            )
            
            def for_canonical(f):
                return lambda k: f(self.hotkey_listener.canonical(k))
            
            self.hotkey_listener = keyboard.Listener(
                on_press=for_canonical(hotkey.press),
                on_release=for_canonical(hotkey.release)
            )
            self.hotkey_listener.start()
            logger.info("✓ Global hotkey listener started (Ctrl+Space)")
            
        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}")
    
    def _show_chat_interface(self):
        """Show floating chat interface"""
        # For now, use terminal-based chat
        # Future: Qt/GTK floating window
        logger.info("Opening chat interface...")
        
        # Simple terminal interaction
        print("\n" + "="*60)
        print("ROXY CHAT (type 'exit' to close)")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n🎤 You: ")
                if user_input.lower() in ['exit', 'quit', 'close']:
                    break
                
                # Process with existing ROXY assistant
                if self.roxy_assistant and HAS_ASSISTANT:
                    # TODO: Integrate with roxy_assistant_v2 properly
                    response = self._process_query(user_input)
                    print(f"🤖 ROXY: {response}")
                else:
                    print("🤖 ROXY: Voice assistant not available in this session")
                    
            except (EOFError, KeyboardInterrupt):
                break
        
        print("Chat closed")
    
    def _process_query(self, query):
        """Process user query through ROXY systems"""
        # Route through existing command parser
        try:
            result = subprocess.run(
                ["python3", str(Path.home() / ".roxy" / "roxy_commands.py"), query],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout or "Processed"
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return f"Error: {e}"
    
    def _monitor_loop(self):
        """Background monitoring for proactive features"""
        logger.info("Starting background monitoring...")
        
        last_health_check = 0
        health_check_interval = 300  # 5 minutes
        
        while self.running.is_set():
            try:
                current_time = time.time()
                
                # Periodic health check
                if current_time - last_health_check > health_check_interval:
                    self._check_system_health()
                    last_health_check = current_time
                
                # TODO: Add file watchers, git hooks, etc.
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(60)
    
    def _check_system_health(self):
        """Check system health status"""
        try:
            # Use existing system_health.py
            result = subprocess.run(
                ["python3", str(Path.home() / ".roxy" / "system_health.py")],
                capture_output=True,
                text=True,
                timeout=30
            )
            logger.debug("Health check completed")
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
    
    def _index_projects(self):
        """Index all projects to ChromaDB for RAG"""
        logger.info("Starting project indexing to ChromaDB...")
        
        projects = [
            Path.home() / "mindsong-juke-hub",
            Path.home() / ".roxy",
            # Add more project paths as needed
        ]
        
        for project in projects:
            if project.exists():
                logger.info(f"Indexing: {project.name}")
                try:
                    # Use existing bootstrap_rag.py
                    subprocess.run(
                        ["python3", str(Path.home() / ".roxy" / "bootstrap_rag.py")],
                        cwd=project,
                        timeout=300
                    )
                    logger.info(f"✓ Indexed: {project.name}")
                except Exception as e:
                    logger.warning(f"Failed to index {project.name}: {e}")
            else:
                logger.warning(f"Project not found: {project}")
        
        logger.info("Project indexing complete")


def main():
    """Main entry point"""
    # Handle signals
    daemon = RoxyDaemon()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start daemon
    daemon.start()


if __name__ == "__main__":
    main()
