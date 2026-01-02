#!/usr/bin/env python3
"""
ROXY Health Monitor - Real-time health checks for all ROXY services
"""
import asyncio
import logging
import os
from typing import Dict, List, Any
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.health')

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class HealthMonitor:
    """Monitor health of all ROXY services"""
    
    def __init__(self):
        self.services = {}
        self.checks = []
        self._register_checks()
    
    def _register_checks(self):
        """Register health check functions"""
        self.checks = [
            self._check_event_bus,
            self._check_knowledge_index,
            self._check_memory_db,
            self._check_postgres,
            self._check_redis,
            self._check_chromadb,
        ]
    
    async def check_all(self) -> Dict[str, Any]:
        """Check health of all services"""
        results = {}
        for check in self.checks:
            try:
                name, status, details = await check()
                results[name] = {
                    'status': status.value if isinstance(status, HealthStatus) else status,
                    'details': details,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                results[check.__name__] = {
                    'status': 'unknown',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        return results
    
    async def _check_event_bus(self) -> tuple:
        """Check NATS event bus health"""
        try:
            from eventbus import RoxyEventBus
            bus = RoxyEventBus()
            await bus.connect()
            await bus.disconnect()
            return ('event_bus', HealthStatus.HEALTHY, {'connected': True})
        except Exception as e:
            return ('event_bus', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    async def _check_knowledge_index(self) -> tuple:
        """Check ChromaDB knowledge index"""
        try:
            from knowledge import KnowledgeIndex
            index = KnowledgeIndex()
            stats = index.get_stats()
            return ('knowledge_index', HealthStatus.HEALTHY, stats)
        except Exception as e:
            return ('knowledge_index', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    async def _check_memory_db(self) -> tuple:
        """Check memory database"""
        try:
            from roxy_core import RoxyMemory
            memory = RoxyMemory()
            stats = memory.get_stats()
            return ('memory_db', HealthStatus.HEALTHY, stats)
        except Exception as e:
            return ('memory_db', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    async def _check_postgres(self) -> tuple:
        """Check PostgreSQL connection"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='roxy',
                user=os.getenv('POSTGRES_USER', 'roxy'),
                password=os.getenv('POSTGRES_PASSWORD', '')
            )
            conn.close()
            return ('postgres', HealthStatus.HEALTHY, {'connected': True})
        except Exception as e:
            return ('postgres', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    async def _check_redis(self) -> tuple:
        """Check Redis connection"""
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            return ('redis', HealthStatus.HEALTHY, {'connected': True})
        except Exception as e:
            return ('redis', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    async def _check_chromadb(self) -> tuple:
        """Check ChromaDB connection"""
        try:
            import chromadb
            client = chromadb.HttpClient(host='localhost', port=8000)
            client.heartbeat()
            return ('chromadb', HealthStatus.HEALTHY, {'connected': True})
        except Exception as e:
            return ('chromadb', HealthStatus.UNHEALTHY, {'error': str(e)})
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        # This would aggregate all service statuses
        return HealthStatus.HEALTHY

