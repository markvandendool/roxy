#!/usr/bin/env python3
"""
NATS Event Streaming - Real-time event processing for ROXY
Uses JetStream for persistent messaging with pattern detection
"""
import logging
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger("roxy.event_stream")

# Try to import NATS
try:
    import nats
    from nats.aio.client import Client as NATS
    from nats.js.api import StreamConfig, RetentionPolicy, StorageType
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    logger.warning("nats-py not installed, event streaming disabled")


@dataclass
class RoxyEvent:
    """Standard event structure for ROXY events."""
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    source: str = "roxy"
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> 'RoxyEvent':
        return cls(**json.loads(data))


class EventStreamProcessor:
    """
    Real-time event processing with NATS JetStream.
    
    Features:
    - Persistent messaging with JetStream
    - Configurable retention policies
    - Pattern detection subscriptions
    - Quality monitoring
    - Feedback learning
    """
    
    # Stream configurations
    STREAMS = {
        'ROXY_QUERIES': {
            'subjects': ['roxy.query.>'],
            'retention_days': 7,
            'description': 'All ROXY queries'
        },
        'ROXY_RESPONSES': {
            'subjects': ['roxy.response.>'],
            'retention_days': 7,
            'description': 'All ROXY responses'
        },
        'ROXY_FEEDBACK': {
            'subjects': ['roxy.feedback.>'],
            'retention_days': 30,
            'description': 'User feedback events'
        },
        'ROXY_METRICS': {
            'subjects': ['roxy.metrics.>'],
            'retention_days': 1,
            'description': 'Performance metrics'
        },
        'ROXY_ALERTS': {
            'subjects': ['roxy.alert.>'],
            'retention_days': 7,
            'description': 'System alerts'
        }
    }
    
    def __init__(self, 
                 nats_url: str = "nats://localhost:4222",
                 enable_jetstream: bool = True):
        """
        Initialize NATS event stream.
        
        Args:
            nats_url: NATS server URL
            enable_jetstream: Whether to use JetStream for persistence
        """
        self.nats_url = nats_url
        self.enable_jetstream = enable_jetstream
        
        self.nc: Optional[NATS] = None
        self.js = None
        self.connected = False
        
        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}
        
        # In-memory buffer for when NATS unavailable
        self._event_buffer: List[RoxyEvent] = []
        self._buffer_max_size = 1000
        
        # Statistics
        self._stats = {
            'events_published': 0,
            'events_received': 0,
            'connection_errors': 0,
            'buffer_size': 0
        }
    
    async def connect(self) -> bool:
        """Establish NATS connection and setup streams."""
        if not NATS_AVAILABLE:
            logger.info("NATS not available, using local event buffer")
            return False
        
        try:
            self.nc = NATS()
            await self.nc.connect(
                self.nats_url,
                connect_timeout=5,
                max_reconnect_attempts=3
            )
            self.connected = True
            logger.info(f"Connected to NATS at {self.nats_url}")
            
            # Enable JetStream if requested
            if self.enable_jetstream:
                try:
                    self.js = self.nc.jetstream()
                    await self._setup_streams()
                    logger.info("JetStream enabled")
                except Exception as e:
                    logger.warning(f"JetStream setup failed: {e}")
                    self.js = None
            
            # Flush buffered events
            await self._flush_buffer()
            
            return True
            
        except Exception as e:
            logger.warning(f"NATS connection failed: {e}")
            self._stats['connection_errors'] += 1
            self.connected = False
            return False
    
    async def _setup_streams(self):
        """Create JetStream streams with retention policies."""
        if not self.js:
            return
        
        for stream_name, config in self.STREAMS.items():
            try:
                await self.js.add_stream(
                    name=stream_name,
                    subjects=config['subjects'],
                    retention=RetentionPolicy.LIMITS,
                    max_age=float(config['retention_days'] * 86400),  # seconds
                    storage=StorageType.FILE,
                    description=config['description']
                )
                logger.debug(f"Created stream: {stream_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"Stream {stream_name} already exists")
                else:
                    logger.warning(f"Failed to create stream {stream_name}: {e}")
    
    async def _flush_buffer(self):
        """Flush buffered events to NATS."""
        if not self._event_buffer or not self.connected:
            return
        
        logger.info(f"Flushing {len(self._event_buffer)} buffered events")
        
        flushed = 0
        for event in self._event_buffer:
            try:
                await self._publish_internal(event)
                flushed += 1
            except Exception as e:
                logger.warning(f"Failed to flush event: {e}")
        
        self._event_buffer = self._event_buffer[flushed:]
        self._stats['buffer_size'] = len(self._event_buffer)
        logger.info(f"Flushed {flushed} events")
    
    def _buffer_event(self, event: RoxyEvent):
        """Buffer event when NATS unavailable."""
        if len(self._event_buffer) >= self._buffer_max_size:
            # Remove oldest events
            self._event_buffer = self._event_buffer[100:]
        
        self._event_buffer.append(event)
        self._stats['buffer_size'] = len(self._event_buffer)
    
    async def _publish_internal(self, event: RoxyEvent):
        """Internal publish method."""
        subject = f"roxy.{event.event_type}"
        payload = event.to_json().encode()
        
        if self.js:
            await self.js.publish(subject, payload)
        elif self.nc:
            await self.nc.publish(subject, payload)
    
    async def publish(self, 
                     event_type: str, 
                     data: Dict[str, Any],
                     session_id: str = None,
                     correlation_id: str = None):
        """
        Publish an event to NATS.
        
        Args:
            event_type: Type of event (e.g., 'query.received', 'response.sent')
            data: Event data payload
            session_id: Optional session identifier
            correlation_id: Optional correlation ID for tracing
        """
        event = RoxyEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
            session_id=session_id,
            correlation_id=correlation_id
        )
        
        if self.connected and self.nc:
            try:
                await self._publish_internal(event)
                self._stats['events_published'] += 1
                logger.debug(f"Published event: {event_type}")
            except Exception as e:
                logger.warning(f"Publish failed: {e}, buffering event")
                self._buffer_event(event)
        else:
            self._buffer_event(event)
    
    def publish_sync(self,
                    event_type: str,
                    data: Dict[str, Any],
                    session_id: str = None,
                    correlation_id: str = None):
        """Synchronous publish wrapper."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Schedule for later execution
            asyncio.ensure_future(
                self.publish(event_type, data, session_id, correlation_id)
            )
        else:
            loop.run_until_complete(
                self.publish(event_type, data, session_id, correlation_id)
            )
    
    # Convenience methods for common event types
    
    async def publish_query(self, 
                           query: str, 
                           session_id: str = None,
                           metadata: Dict = None):
        """Publish a query event."""
        await self.publish(
            'query.received',
            {
                'query': query[:1000],  # Truncate long queries
                'query_length': len(query),
                'metadata': metadata or {}
            },
            session_id=session_id
        )
    
    async def publish_response(self,
                              query: str,
                              response: str,
                              elapsed_time: float,
                              model: str = None,
                              session_id: str = None,
                              cached: bool = False):
        """Publish a response event."""
        await self.publish(
            'response.sent',
            {
                'query': query[:500],
                'response_length': len(response),
                'elapsed_time': elapsed_time,
                'model': model,
                'cached': cached
            },
            session_id=session_id
        )
    
    async def publish_feedback(self,
                              query: str,
                              response: str,
                              feedback_type: str,
                              correction: str = None,
                              session_id: str = None):
        """Publish a feedback event."""
        await self.publish(
            f'feedback.{feedback_type}',
            {
                'query': query[:500],
                'response': response[:500],
                'feedback_type': feedback_type,
                'correction': correction
            },
            session_id=session_id
        )
    
    async def publish_metric(self,
                            metric_name: str,
                            value: float,
                            labels: Dict = None):
        """Publish a metric event."""
        await self.publish(
            f'metrics.{metric_name}',
            {
                'metric': metric_name,
                'value': value,
                'labels': labels or {}
            }
        )
    
    async def publish_alert(self,
                           alert_type: str,
                           message: str,
                           severity: str = 'warning',
                           details: Dict = None):
        """Publish an alert event."""
        await self.publish(
            f'alert.{alert_type}',
            {
                'alert_type': alert_type,
                'message': message,
                'severity': severity,
                'details': details or {}
            }
        )
    
    # Subscription methods
    
    async def subscribe(self,
                       subject: str,
                       handler: Callable,
                       durable: str = None):
        """
        Subscribe to events.
        
        Args:
            subject: NATS subject pattern (e.g., 'roxy.query.>')
            handler: Async callback function
            durable: Durable subscriber name for JetStream
        """
        if not self.connected:
            logger.warning(f"Cannot subscribe to {subject}: not connected")
            return
        
        async def message_handler(msg):
            try:
                event = RoxyEvent.from_json(msg.data.decode())
                self._stats['events_received'] += 1
                await handler(event)
            except Exception as e:
                logger.error(f"Handler error for {subject}: {e}")
        
        try:
            if self.js and durable:
                await self.js.subscribe(
                    subject,
                    cb=message_handler,
                    durable=durable
                )
                logger.info(f"JetStream subscription: {subject} (durable={durable})")
            elif self.nc:
                await self.nc.subscribe(
                    subject,
                    cb=message_handler
                )
                logger.info(f"Core NATS subscription: {subject}")
        except Exception as e:
            logger.error(f"Subscription failed for {subject}: {e}")
    
    async def setup_default_subscriptions(self):
        """Setup default event handlers."""
        
        # Pattern detection for queries
        async def detect_patterns(event: RoxyEvent):
            query = event.data.get('query', '')
            # Simple pattern detection
            if len(query) < 10:
                await self.publish_alert(
                    'short_query',
                    f"Very short query detected: {query}",
                    severity='info'
                )
        
        # Quality monitoring for responses
        async def monitor_quality(event: RoxyEvent):
            elapsed = event.data.get('elapsed_time', 0)
            if elapsed > 5.0:
                await self.publish_alert(
                    'slow_response',
                    f"Slow response: {elapsed:.2f}s",
                    severity='warning',
                    details={'elapsed_time': elapsed}
                )
        
        # Feedback learning
        async def learn_feedback(event: RoxyEvent):
            feedback_type = event.data.get('feedback_type')
            if feedback_type == 'thumbs_down':
                logger.info(f"Negative feedback received, logging for review")
                # Could trigger retraining or adjustment
        
        await self.subscribe('roxy.query.>', detect_patterns, durable='pattern-detector')
        await self.subscribe('roxy.response.>', monitor_quality, durable='quality-monitor')
        await self.subscribe('roxy.feedback.>', learn_feedback, durable='feedback-learner')
    
    async def close(self):
        """Close NATS connection."""
        if self.nc:
            await self.nc.close()
            self.connected = False
            logger.info("NATS connection closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event stream statistics."""
        return {
            **self._stats,
            'connected': self.connected,
            'jetstream_enabled': self.js is not None,
            'nats_available': NATS_AVAILABLE
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check event stream health."""
        status = {
            'healthy': False,
            'connected': self.connected,
            'jetstream': self.js is not None,
            'details': {}
        }
        
        if self.connected and self.nc:
            try:
                # Send a test message
                await self.nc.flush()
                status['healthy'] = True
                status['details']['server'] = self.nats_url
            except Exception as e:
                status['details']['error'] = str(e)
        else:
            status['healthy'] = True  # Buffer fallback works
            status['details']['mode'] = 'buffered'
            status['details']['buffer_size'] = len(self._event_buffer)
        
        return status


# Synchronous wrapper
class EventStreamSync:
    """Synchronous wrapper for EventStreamProcessor."""
    
    def __init__(self, **kwargs):
        self._async_processor = EventStreamProcessor(**kwargs)
        self._loop = None
        self._connected = False
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def connect(self) -> bool:
        loop = self._get_loop()
        self._connected = loop.run_until_complete(
            self._async_processor.connect()
        )
        return self._connected
    
    def publish(self, event_type: str, data: Dict[str, Any], **kwargs):
        """Publish event (non-blocking)."""
        self._async_processor.publish_sync(event_type, data, **kwargs)
    
    def publish_query(self, query: str, session_id: str = None, metadata: Dict = None):
        self.publish('query.received', {
            'query': query[:1000],
            'query_length': len(query),
            'metadata': metadata or {}
        }, session_id=session_id)
    
    def publish_response(self, query: str, response: str, elapsed_time: float, 
                        model: str = None, session_id: str = None, cached: bool = False):
        self.publish('response.sent', {
            'query': query[:500],
            'response_length': len(response),
            'elapsed_time': elapsed_time,
            'model': model,
            'cached': cached
        }, session_id=session_id)
    
    def publish_feedback(self, query: str, response: str, feedback_type: str,
                        correction: str = None, session_id: str = None):
        self.publish(f'feedback.{feedback_type}', {
            'query': query[:500],
            'response': response[:500],
            'feedback_type': feedback_type,
            'correction': correction
        }, session_id=session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        return self._async_processor.get_stats()
    
    def health_check(self) -> Dict[str, Any]:
        loop = self._get_loop()
        return loop.run_until_complete(
            self._async_processor.health_check()
        )
    
    def close(self):
        loop = self._get_loop()
        loop.run_until_complete(self._async_processor.close())


# Singleton instance
_event_stream: Optional[EventStreamSync] = None


def get_event_stream() -> EventStreamSync:
    """Get global event stream instance."""
    global _event_stream
    if _event_stream is None:
        _event_stream = EventStreamSync()
    return _event_stream
