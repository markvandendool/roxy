#!/usr/bin/env python3
"""
APOLLO AUDIO BRIDGE SERVER
==========================
Sprint 2: RRR-004 - WebSocket bridge connecting MCP music tools to browser Apollo

Architecture:
  MCP Tools (Python) → WebSocket (8788) → Browser Apollo (Tone.js)

Protocol:
  Messages are JSON with format:
  {
    "type": "playChord" | "playNote" | "playProgression" | "stop",
    "notes": ["C4", "E4", "G4"],      # For playChord/playNote
    "duration": 2.0,                   # Seconds
    "velocity": 0.8,                   # 0-1
    "instrument": "piano",             # Optional
    "progression": [...],              # For playProgression
    "tempo": 120                       # BPM for progressions
  }

Usage:
  # Start the server:
  python apollo_bridge.py
  
  # Or import and use:
  from apollo_bridge import ApolloBridge
  bridge = ApolloBridge()
  await bridge.start()
  await bridge.send_chord(["C4", "E4", "G4"], duration=2.0, velocity=0.8)
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("apollo.bridge")

# Try to import websockets - if not available, provide instructions
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets package not installed. Install with: pip install websockets")


class ApolloBridge:
    """
    WebSocket server that bridges MCP music tools to browser Apollo.
    
    The browser connects as a WebSocket client, and MCP tools send
    commands through this bridge which are forwarded to the browser.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8788):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        
    async def register_client(self, websocket: WebSocketServerProtocol):
        """Register a new browser client."""
        self.clients.add(websocket)
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"🎵 Browser connected: {client_info} (total: {len(self.clients)})")
        
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "Apollo Bridge connected",
            "timestamp": datetime.now().isoformat()
        }))
        
    async def unregister_client(self, websocket: WebSocketServerProtocol):
        """Unregister a disconnected browser client."""
        self.clients.discard(websocket)
        logger.info(f"🔌 Browser disconnected (remaining: {len(self.clients)})")
        
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str = "/"):
        """Handle a WebSocket client connection."""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "ack":
                        # Browser acknowledging a command
                        logger.debug(f"✅ Browser ack: {data.get('command', 'unknown')}")
                    elif msg_type == "ready":
                        # Browser Apollo is ready
                        logger.info(f"🎹 Apollo ready: {data.get('instruments', 0)} instruments")
                    elif msg_type == "error":
                        # Browser encountered an error
                        logger.error(f"❌ Browser error: {data.get('error', 'unknown')}")
                    else:
                        logger.debug(f"📩 Browser message: {msg_type}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from browser: {message[:100]}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
            
    async def broadcast(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected browser clients.
        Returns the number of clients that received the message.
        """
        if not self.clients:
            logger.warning("⚠️ No browser clients connected - audio command lost")
            return 0
            
        message_json = json.dumps(message)
        
        # Send to all clients, collect any failures
        send_tasks = []
        for client in self.clients.copy():
            send_tasks.append(self._safe_send(client, message_json))
            
        results = await asyncio.gather(*send_tasks)
        sent_count = sum(1 for r in results if r)
        
        msg_type = message.get("type", "unknown")
        logger.info(f"📤 Broadcast {msg_type} to {sent_count}/{len(self.clients)} clients")
        
        return sent_count
        
    async def _safe_send(self, client: WebSocketServerProtocol, message: str) -> bool:
        """Safely send a message to a client, handling disconnections."""
        try:
            await client.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(client)
            return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
            
    # ═══════════════════════════════════════════════════════════════════
    # PUBLIC API - Called by MCP music tools
    # ═══════════════════════════════════════════════════════════════════
    
    async def send_play_chord(
        self, 
        notes: List[str], 
        duration: float = 2.0, 
        velocity: float = 0.8,
        instrument: Optional[str] = None
    ) -> int:
        """
        Send a playChord command to browser Apollo.
        
        Args:
            notes: List of note names with octave, e.g. ["C4", "E4", "G4"]
            duration: Duration in seconds
            velocity: Volume 0-1
            instrument: Optional instrument override
            
        Returns:
            Number of clients that received the command
        """
        message = {
            "type": "playChord",
            "notes": notes,
            "duration": duration,
            "velocity": velocity,
            "timestamp": datetime.now().isoformat()
        }
        if instrument:
            message["instrument"] = instrument
            
        return await self.broadcast(message)
        
    async def send_play_note(
        self,
        note: str,
        duration: float = 1.0,
        velocity: float = 0.8,
        voice: str = "melody"
    ) -> int:
        """
        Send a playNote command to browser Apollo.
        
        Args:
            note: Note name with octave, e.g. "C4"
            duration: Duration in seconds
            velocity: Volume 0-1
            voice: Voice type: "chord", "melody", or "bass"
        """
        message = {
            "type": "playNote",
            "note": note,
            "duration": duration,
            "velocity": velocity,
            "voice": voice,
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message)
        
    async def send_play_progression(
        self,
        chords: List[Dict[str, Any]],
        tempo: int = 120,
        beats_per_chord: int = 4
    ) -> int:
        """
        Send a playProgression command to browser Apollo.
        
        Args:
            chords: List of chord dicts with notes, e.g. 
                    [{"notes": ["C4","E4","G4"]}, {"notes": ["A3","C4","E4"]}]
            tempo: Beats per minute
            beats_per_chord: Beats to hold each chord
        """
        message = {
            "type": "playProgression",
            "chords": chords,
            "tempo": tempo,
            "beatsPerChord": beats_per_chord,
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message)
        
    async def send_stop(self) -> int:
        """Send a stop command to halt all playback."""
        message = {
            "type": "stop",
            "timestamp": datetime.now().isoformat()
        }
        return await self.broadcast(message)
        
    # ═══════════════════════════════════════════════════════════════════
    # SERVER LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════
    
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Cannot start: websockets package not installed")
            return
            
        self._running = True
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        logger.info(f"🎵 Apollo Bridge started on ws://{self.host}:{self.port}")
        logger.info(f"   Waiting for browser clients...")
        
    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("🛑 Apollo Bridge stopped")
            
    async def run_forever(self):
        """Start the server and run until interrupted."""
        await self.start()
        if self.server:
            await self.server.wait_closed()
            
    def get_status(self) -> Dict[str, Any]:
        """Get current bridge status."""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "connected_clients": len(self.clients),
            "websockets_available": WEBSOCKETS_AVAILABLE
        }


# Global singleton for easy access from MCP tools
_bridge_instance: Optional[ApolloBridge] = None
_bridge_task: Optional[asyncio.Task] = None

async def get_bridge() -> ApolloBridge:
    """Get or create the global Apollo bridge instance."""
    global _bridge_instance, _bridge_task
    
    if _bridge_instance is None:
        _bridge_instance = ApolloBridge()
        
    if not _bridge_instance._running:
        await _bridge_instance.start()
        
    return _bridge_instance


async def send_chord_to_apollo(
    notes: List[str],
    duration: float = 2.0,
    velocity: float = 0.8,
    instrument: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function for MCP tools to send a chord to Apollo.
    
    Returns a status dict with connection info.
    """
    bridge = await get_bridge()
    sent = await bridge.send_play_chord(notes, duration, velocity, instrument)
    
    return {
        "sent": sent > 0,
        "clients": sent,
        "notes": notes,
        "instrument": instrument,
        "message": f"Sent to {sent} client(s)" if sent else "No clients connected"
    }


async def send_progression_to_apollo(
    chord_list: List[List[str]],
    tempo: int = 120,
    beats_per_chord: int = 4
) -> Dict[str, Any]:
    """
    Convenience function for MCP tools to send a progression to Apollo.
    """
    bridge = await get_bridge()
    
    # Convert list of note lists to chord dicts
    chords = [{"notes": notes} for notes in chord_list]
    
    sent = await bridge.send_play_progression(chords, tempo, beats_per_chord)
    
    return {
        "sent": sent > 0,
        "clients": sent,
        "chord_count": len(chords),
        "message": f"Sent {len(chords)} chords to {sent} client(s)" if sent else "No clients connected"
    }


def health_check() -> Dict[str, Any]:
    """Check if the bridge is healthy."""
    if _bridge_instance:
        return {
            "status": "running" if _bridge_instance._running else "stopped",
            **_bridge_instance.get_status()
        }
    return {
        "status": "not_initialized",
        "websockets_available": WEBSOCKETS_AVAILABLE
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Main entry point for running the bridge as a standalone server."""
    print("═" * 60)
    print("🎵 APOLLO AUDIO BRIDGE SERVER")
    print("═" * 60)
    print()
    
    if not WEBSOCKETS_AVAILABLE:
        print("ERROR: websockets package not installed!")
        print("Install with: pip install websockets")
        sys.exit(1)
        
    bridge = ApolloBridge()
    
    try:
        await bridge.start()
        print()
        print("Server running. Press Ctrl+C to stop.")
        print()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
