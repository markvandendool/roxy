#!/usr/bin/env python3
"""
NDI Widget Bridge for 8K Theater Integration
SKOREQ-OBS-EPIC-001-STORY-001

Provides NDI output wrapper for 8K Theater widgets:
- Piano, Fretboard, Braid, COF, HarmonicProfile, ScoreTab, Metronome, TempoGeometry

Requirements:
- DistroAV NDI Tools for Linux
- NDI SDK (libndi)
- OBS with NDI plugin
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional, List, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ndi_bridge")

# Widget registry - maps widget names to their NDI source configuration
WIDGET_REGISTRY = {
    "Piano": {
        "ndi_name": "ROXY-Piano",
        "resolution": (1920, 1080),
        "alpha_channel": True,
        "frame_rate": 60,
        "source_url": "http://localhost:9135/widgets/piano"
    },
    "Fretboard": {
        "ndi_name": "ROXY-Fretboard",
        "resolution": (1920, 540),
        "alpha_channel": True,
        "frame_rate": 60,
        "source_url": "http://localhost:9135/widgets/fretboard"
    },
    "Braid": {
        "ndi_name": "ROXY-Braid",
        "resolution": (1080, 1080),
        "alpha_channel": True,
        "frame_rate": 30,
        "source_url": "http://localhost:9135/widgets/braid"
    },
    "COF": {
        "ndi_name": "ROXY-CircleOfFifths",
        "resolution": (1080, 1080),
        "alpha_channel": True,
        "frame_rate": 30,
        "source_url": "http://localhost:9135/widgets/cof"
    },
    "HarmonicProfile": {
        "ndi_name": "ROXY-HarmonicProfile",
        "resolution": (1920, 540),
        "alpha_channel": True,
        "frame_rate": 30,
        "source_url": "http://localhost:9135/widgets/harmonic-profile"
    },
    "ScoreTab": {
        "ndi_name": "ROXY-ScoreTab",
        "resolution": (1920, 1080),
        "alpha_channel": True,
        "frame_rate": 30,
        "source_url": "http://localhost:9135/widgets/score-tab"
    },
    "Metronome": {
        "ndi_name": "ROXY-Metronome",
        "resolution": (400, 400),
        "alpha_channel": True,
        "frame_rate": 60,
        "source_url": "http://localhost:9135/widgets/metronome"
    },
    "TempoGeometry": {
        "ndi_name": "ROXY-TempoGeometry",
        "resolution": (800, 800),
        "alpha_channel": True,
        "frame_rate": 30,
        "source_url": "http://localhost:9135/widgets/tempo-geometry"
    }
}


@dataclass
class NDISource:
    """Represents an NDI source for a widget"""
    name: str
    widget_id: str
    resolution: tuple
    alpha_channel: bool
    frame_rate: int
    source_url: str
    active: bool = False
    last_frame_time: float = 0.0


class NDIWidgetBridge:
    """
    Bridge between 8K Theater widgets and NDI output.

    Each widget is exposed as an independent NDI source that can be
    discovered by OBS via DistroAV NDI scanner on the local network.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.sources: Dict[str, NDISource] = {}
        self.config_path = config_path or Path.home() / ".roxy/obs-portable/config/ndi-widget-bridge.json"
        self._running = False
        self._ndi_initialized = False

    async def initialize(self) -> bool:
        """Initialize NDI library and create sources"""
        logger.info("Initializing NDI Widget Bridge...")

        # Load or create config
        self._load_config()

        # Check for NDI library
        if not self._check_ndi_available():
            logger.warning("NDI library not found. Running in simulation mode.")
            self._ndi_initialized = False
        else:
            self._ndi_initialized = True

        # Create NDI sources for all registered widgets
        for widget_id, config in WIDGET_REGISTRY.items():
            self.sources[widget_id] = NDISource(
                name=config["ndi_name"],
                widget_id=widget_id,
                resolution=config["resolution"],
                alpha_channel=config["alpha_channel"],
                frame_rate=config["frame_rate"],
                source_url=config["source_url"]
            )
            logger.info(f"Registered NDI source: {config['ndi_name']} for {widget_id}")

        return True

    def _check_ndi_available(self) -> bool:
        """Check if NDI library is available"""
        try:
            # Try to import NDI bindings
            # In production, this would use pyndi or similar
            import ctypes
            ndi_lib = ctypes.CDLL("libndi.so.5")
            return True
        except (ImportError, OSError):
            return False

    def _load_config(self) -> None:
        """Load configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = json.load(f)
                logger.info(f"Loaded config from {self.config_path}")
        else:
            # Create default config
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to JSON file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "version": "1.0.0",
            "widgets": WIDGET_REGISTRY,
            "settings": {
                "auto_start": True,
                "network_interface": "auto",
                "discovery_subnet": "192.168.x.x"
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to {self.config_path}")

    async def start_source(self, widget_id: str) -> bool:
        """Start NDI output for a specific widget"""
        if widget_id not in self.sources:
            logger.error(f"Unknown widget: {widget_id}")
            return False

        source = self.sources[widget_id]
        if source.active:
            logger.warning(f"Source {source.name} already active")
            return True

        logger.info(f"Starting NDI source: {source.name}")
        source.active = True

        if self._ndi_initialized:
            # In production: Create actual NDI sender
            # ndi_send = NDI.create_send(source.name, ...)
            pass

        return True

    async def stop_source(self, widget_id: str) -> bool:
        """Stop NDI output for a specific widget"""
        if widget_id not in self.sources:
            return False

        source = self.sources[widget_id]
        source.active = False
        logger.info(f"Stopped NDI source: {source.name}")
        return True

    async def start_all(self) -> None:
        """Start all NDI sources"""
        for widget_id in self.sources:
            await self.start_source(widget_id)
        self._running = True

    async def stop_all(self) -> None:
        """Stop all NDI sources"""
        for widget_id in self.sources:
            await self.stop_source(widget_id)
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        """Get status of all NDI sources"""
        return {
            "ndi_available": self._ndi_initialized,
            "running": self._running,
            "sources": {
                widget_id: {
                    "name": source.name,
                    "active": source.active,
                    "resolution": source.resolution,
                    "frame_rate": source.frame_rate
                }
                for widget_id, source in self.sources.items()
            }
        }

    def list_sources(self) -> List[str]:
        """List all NDI source names for OBS discovery"""
        return [source.name for source in self.sources.values()]


# MCP Tool handlers for OBS server integration
async def ndi_bridge_start(widget: Optional[str] = None) -> Dict[str, Any]:
    """MCP tool: Start NDI bridge for widget(s)"""
    bridge = NDIWidgetBridge()
    await bridge.initialize()

    if widget:
        success = await bridge.start_source(widget)
        return {"success": success, "widget": widget}
    else:
        await bridge.start_all()
        return {"success": True, "sources": bridge.list_sources()}


async def ndi_bridge_stop(widget: Optional[str] = None) -> Dict[str, Any]:
    """MCP tool: Stop NDI bridge for widget(s)"""
    bridge = NDIWidgetBridge()
    await bridge.initialize()

    if widget:
        success = await bridge.stop_source(widget)
        return {"success": success, "widget": widget}
    else:
        await bridge.stop_all()
        return {"success": True}


async def ndi_bridge_status() -> Dict[str, Any]:
    """MCP tool: Get NDI bridge status"""
    bridge = NDIWidgetBridge()
    await bridge.initialize()
    return bridge.get_status()


# CLI interface
if __name__ == "__main__":
    import sys

    async def main():
        bridge = NDIWidgetBridge()
        await bridge.initialize()

        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd == "start":
                widget = sys.argv[2] if len(sys.argv) > 2 else None
                result = await ndi_bridge_start(widget)
                print(json.dumps(result, indent=2))
            elif cmd == "stop":
                widget = sys.argv[2] if len(sys.argv) > 2 else None
                result = await ndi_bridge_stop(widget)
                print(json.dumps(result, indent=2))
            elif cmd == "status":
                result = await ndi_bridge_status()
                print(json.dumps(result, indent=2))
            elif cmd == "list":
                print("Available NDI sources:")
                for name in bridge.list_sources():
                    print(f"  - {name}")
            else:
                print(f"Unknown command: {cmd}")
                print("Usage: ndi_bridge.py [start|stop|status|list] [widget]")
        else:
            print("NDI Widget Bridge - 8K Theater Integration")
            print("=" * 50)
            status = bridge.get_status()
            print(f"NDI Available: {status['ndi_available']}")
            print(f"Running: {status['running']}")
            print("\nRegistered widgets:")
            for widget_id, info in status['sources'].items():
                print(f"  {widget_id}: {info['name']} ({info['resolution'][0]}x{info['resolution'][1]})")

    asyncio.run(main())
