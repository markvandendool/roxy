#!/usr/bin/env python3
"""
ROXY Event Bus - NATS JetStream Integration
Provides pub/sub messaging for all ROXY services
"""
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime
import nats
from nats.js.api import StreamConfig, ConsumerConfig, DeliverPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NATS_URL = "nats://localhost:4222"

# Stream definitions
STREAMS = {
    "ROXY_EVENTS": {
        "subjects": ["roxy.>"],
        "retention": "limits",
        "max_msgs": 100000,
        "max_bytes": 1024 * 1024 * 100,  # 100MB
        "max_age": 86400 * 7,  # 7 days
    },
    "ROXY_COMMANDS": {
        "subjects": ["cmd.>"],
        "retention": "workqueue",
        "max_msgs": 10000,
    }
}

class RoxyEventBus:
    def __init__(self, url: str = NATS_URL):
        self.url = url
        self.nc = None
        self.js = None
        self.subscriptions = {}
    
    async def connect(self):
        """Connect to NATS and initialize JetStream"""
        logger.info(f"Connecting to NATS: {self.url}")
        self.nc = await nats.connect(self.url)
        self.js = self.nc.jetstream()
        
        # Create streams
        for stream_name, config in STREAMS.items():
            try:
                await self.js.add_stream(
                    name=stream_name,
                    subjects=config["subjects"],
                    retention=config["retention"],
                    max_msgs=config.get("max_msgs", -1),
                    max_bytes=config.get("max_bytes", -1),
                    max_age=config.get("max_age", 0)
                )
                logger.info(f"Stream created/verified: {stream_name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"Stream {stream_name}: {e}")
        
        logger.info("Connected to NATS JetStream")
        return self
    
    async def disconnect(self):
        """Disconnect from NATS"""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            logger.info("Disconnected from NATS")
    
    async def publish(self, subject: str, data: Dict[str, Any], headers: Dict[str, str] = None):
        """Publish an event to NATS JetStream"""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": subject,
            "data": data
        }
        
        msg = json.dumps(payload).encode()
        try:
            ack = await self.js.publish(subject, msg, headers=headers)
            logger.debug(f"Published to {subject}: seq={ack.seq}")
            return ack
        except Exception as e:
            logger.warning(f"Failed to publish to {subject}: {e}")
            return None
    
    async def subscribe(self, subject: str, callback: Callable, durable: str = None):
        """Subscribe to events with optional durable consumer"""
        async def message_handler(msg):
            try:
                payload = json.loads(msg.data.decode())
                await callback(payload)
                await msg.ack()
            except Exception as e:
                logger.error(f"Handler error for {subject}: {e}")
                await msg.nak()
        
        if durable:
            sub = await self.js.subscribe(subject, durable=durable, cb=message_handler)
        else:
            sub = await self.js.subscribe(subject, cb=message_handler)
        
        self.subscriptions[subject] = sub
        logger.info(f"Subscribed to: {subject}")
        return sub
    
    async def request(self, subject: str, data: Dict[str, Any], timeout: float = 5.0) -> Dict:
        """Send a request and wait for response"""
        payload = json.dumps(data).encode()
        response = await self.nc.request(subject, payload, timeout=timeout)
        return json.loads(response.data.decode())


# Event subjects
class Events:
    # Content pipeline
    CONTENT_QUEUED = "roxy.content.queued"
    CONTENT_TRANSCRIBED = "roxy.content.transcribed"
    CONTENT_ANALYZED = "roxy.content.analyzed"
    CONTENT_CLIPPED = "roxy.content.clipped"
    CONTENT_COMPLETE = "roxy.content.complete"
    
    # Voice
    WAKE_WORD_DETECTED = "roxy.voice.wakeword"
    COMMAND_RECEIVED = "roxy.voice.command"
    RESPONSE_READY = "roxy.voice.response"
    
    # Desktop
    SCREENSHOT_TAKEN = "roxy.desktop.screenshot"
    CLIPBOARD_CHANGED = "roxy.desktop.clipboard"
    
    # Browser
    PAGE_LOADED = "roxy.browser.loaded"
    FORM_SUBMITTED = "roxy.browser.form"
    
    # System
    SERVICE_STARTED = "roxy.system.started"
    SERVICE_STOPPED = "roxy.system.stopped"
    ERROR_OCCURRED = "roxy.system.error"


# Global event bus instance
_bus: Optional[RoxyEventBus] = None

async def get_bus() -> RoxyEventBus:
    """Get or create global event bus instance"""
    global _bus
    if _bus is None:
        _bus = RoxyEventBus()
        await _bus.connect()
    return _bus


async def publish(subject: str, data: Dict[str, Any]):
    """Convenience function to publish events"""
    bus = await get_bus()
    return await bus.publish(subject, data)


async def subscribe(subject: str, callback: Callable, durable: str = None):
    """Convenience function to subscribe to events"""
    bus = await get_bus()
    return await bus.subscribe(subject, callback, durable)


# Demo/test
async def main():
    bus = RoxyEventBus()
    await bus.connect()
    
    # Subscribe to all roxy events
    async def handler(msg):
        print(f"Received: {msg}")
    
    await bus.subscribe("roxy.>", handler)
    
    # Publish test event
    await bus.publish(Events.SERVICE_STARTED, {
        "service": "event-bus-demo",
        "version": "1.0.0"
    })
    
    print("Listening for events... (Ctrl+C to stop)")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    
    await bus.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
