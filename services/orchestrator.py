#!/usr/bin/env python3
"""
ROXY Master Orchestrator
Central coordination service for all ROXY components
"""
import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

ROXY_HOME = Path.home() / ".roxy"
ROXY_SERVICES = ROXY_HOME / "services"
ROXY_VOICE = ROXY_HOME / "voice"
ROXY_LEGACY = ROXY_HOME / "services.LEGACY.20260101_200448"

sys.path.insert(0, str(ROXY_SERVICES))
sys.path.insert(0, str(ROXY_VOICE))
if ROXY_LEGACY.exists():
    sys.path.insert(0, str(ROXY_LEGACY))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('roxy.orchestrator')

class RoxyOrchestrator:
    """Master orchestrator for ROXY AI Assistant"""
    
    def __init__(self):
        self.running = False
        self.services = {}
        self.start_time = None
        
    async def start(self):
        """Start all ROXY services"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("ROXY ORCHESTRATOR STARTING")
        logger.info("=" * 60)
        
        # Initialize services
        await self._init_event_bus()
        await self._init_knowledge_index()
        await self._init_mcp_registry()
        await self._init_voice_router()
        
        # Publish startup event
        if self.services.get('eventbus'):
            await self.services['eventbus'].publish(
                'roxy.system.started',
                {
                    'version': '1.0.0',
                    'services': list(self.services.keys()),
                    'timestamp': self.start_time.isoformat()
                }
            )
        
        logger.info("-" * 60)
        logger.info("ROXY ORCHESTRATOR READY")
        logger.info(f"Services: {len(self.services)}")
        logger.info(f"Uptime: {self.start_time.isoformat()}")
        logger.info("-" * 60)
        
        # Main loop
        while self.running:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Graceful shutdown"""
        logger.info("ROXY ORCHESTRATOR STOPPING...")
        self.running = False
        
        # Publish shutdown event
        if self.services.get('eventbus'):
            await self.services['eventbus'].publish(
                'roxy.system.stopped',
                {'timestamp': datetime.now().isoformat()}
            )
            await self.services['eventbus'].disconnect()
        
        logger.info("ROXY ORCHESTRATOR STOPPED")
    
    async def _init_event_bus(self):
        """Initialize NATS event bus"""
        try:
            from eventbus import RoxyEventBus
            bus = RoxyEventBus()
            await bus.connect()
            self.services['eventbus'] = bus
            logger.info("✅ Event bus connected")
        except Exception as e:
            logger.warning(f"⚠️ Event bus unavailable: {e}")
    
    async def _init_knowledge_index(self):
        """Initialize ChromaDB knowledge index"""
        try:
            from knowledge import KnowledgeIndex
            index = KnowledgeIndex()
            self.services['knowledge'] = index
            stats = index.get_stats()
            total_docs = sum(s['count'] for s in stats.values())
            logger.info(f"✅ Knowledge index connected ({total_docs} documents)")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge index unavailable: {e}")
    
    async def _init_mcp_registry(self):
        """Initialize MCP server registry"""
        try:
            from mcp_registry import MCPRegistry
            registry = MCPRegistry()
            self.services['mcp_registry'] = registry
            tools = registry.get_all_tools()
            logger.info(f"✅ MCP registry loaded ({len(tools)} tools)")
        except Exception as e:
            logger.warning(f"⚠️ MCP registry unavailable: {e}")
    
    async def _init_voice_router(self):
        """Initialize voice command router"""
        try:
            from voice_router import VoiceRouter
            router = VoiceRouter()
            self.services['voice_router'] = router
            logger.info(f"✅ Voice router loaded ({len(router.routes)} routes)")
        except Exception as e:
            logger.warning(f"⚠️ Voice router unavailable: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'services': {
                name: 'active' for name in self.services.keys()
            }
        }


async def main():
    orchestrator = RoxyOrchestrator()
    
    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(orchestrator.stop()))
    
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(main())
