#!/usr/bin/env python3
"""
ROXY Health Monitor - Continuous Service Monitoring
Part of ROCKY-ROXY-ROCKIN-V1: Sprint 4 - Polish & Launch

Story: RRR-017

Features:
- Continuous health monitoring of all services
- Auto-restart on failure
- Alert notifications
- Metrics collection
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import logging
import subprocess
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("health_monitor")

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

@dataclass
class ServiceConfig:
    name: str
    endpoint: str
    port: int
    critical: bool = True
    timeout: float = 5.0
    restart_cmd: Optional[str] = None

@dataclass
class ServiceState:
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_healthy: Optional[datetime] = None
    latency_ms: Optional[float] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0

SERVICES: List[ServiceConfig] = [
    ServiceConfig(
        name="ROXY Core",
        endpoint="http://127.0.0.1:8766/health",
        port=8766,
        critical=True,
        restart_cmd="systemctl --user restart roxy-core"
    ),
    ServiceConfig(
        name="Luno Orchestrator",
        endpoint="http://127.0.0.1:3000/health",
        port=3000,
        critical=True
    ),
    ServiceConfig(
        name="n8n",
        endpoint="http://127.0.0.1:5678/healthz",
        port=5678,
        critical=False
    ),
    ServiceConfig(
        name="ChromaDB",
        endpoint="http://127.0.0.1:8000/api/v1/heartbeat",
        port=8000,
        critical=False
    ),
    ServiceConfig(
        name="Ollama",
        endpoint="http://127.0.0.1:11435/api/tags",
        port=11435,
        critical=False
    ),
    ServiceConfig(
        name="Whisper STT",
        endpoint="http://127.0.0.1:10300/health",
        port=10300,
        critical=False
    ),
    ServiceConfig(
        name="Piper TTS",
        endpoint="http://127.0.0.1:10200/health",
        port=10200,
        critical=False
    ),
    ServiceConfig(
        name="Friday",
        endpoint="http://10.0.0.65:8765/health",
        port=8765,
        critical=False,
        timeout=10.0
    ),
]

# ═══════════════════════════════════════════════════════════════
# Health Monitor
# ═══════════════════════════════════════════════════════════════

class HealthMonitor:
    """
    Monitors service health and triggers actions on failures.
    """
    
    def __init__(
        self,
        services: List[ServiceConfig],
        check_interval: float = 30.0,
        max_failures_before_restart: int = 3,
        on_status_change: Optional[Callable] = None
    ):
        self.services = services
        self.check_interval = check_interval
        self.max_failures = max_failures_before_restart
        self.on_status_change = on_status_change
        
        self.states: Dict[str, ServiceState] = {
            svc.name: ServiceState() for svc in services
        }
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._running = False
    
    async def start(self):
        """Start the health monitor loop"""
        self._running = True
        self._session = aiohttp.ClientSession()
        
        logger.info("Health Monitor started")
        logger.info(f"Monitoring {len(self.services)} services every {self.check_interval}s")
        
        while self._running:
            await self._check_all()
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the health monitor"""
        self._running = False
        if self._session:
            await self._session.close()
        logger.info("Health Monitor stopped")
    
    async def _check_all(self):
        """Check all services"""
        tasks = [self._check_service(svc) for svc in self.services]
        await asyncio.gather(*tasks)
        
        # Log summary
        healthy = sum(1 for s in self.states.values() if s.status == ServiceStatus.HEALTHY)
        total = len(self.services)
        
        if healthy == total:
            logger.debug(f"All {total} services healthy")
        else:
            logger.warning(f"{healthy}/{total} services healthy")
    
    async def _check_service(self, service: ServiceConfig):
        """Check a single service"""
        state = self.states[service.name]
        old_status = state.status
        
        try:
            start = asyncio.get_event_loop().time()
            
            async with self._session.get(
                service.endpoint,
                timeout=aiohttp.ClientTimeout(total=service.timeout)
            ) as resp:
                latency = (asyncio.get_event_loop().time() - start) * 1000
                
                if resp.status == 200:
                    state.status = ServiceStatus.HEALTHY
                    state.latency_ms = latency
                    state.consecutive_failures = 0
                    state.last_healthy = datetime.now(timezone.utc)
                else:
                    state.status = ServiceStatus.DEGRADED
                    state.consecutive_failures += 1
                    state.total_failures += 1
                    
        except asyncio.TimeoutError:
            state.status = ServiceStatus.OFFLINE
            state.consecutive_failures += 1
            state.total_failures += 1
            state.latency_ms = None
            
        except Exception as e:
            state.status = ServiceStatus.OFFLINE
            state.consecutive_failures += 1
            state.total_failures += 1
            state.latency_ms = None
            logger.debug(f"{service.name} check failed: {e}")
        
        state.last_check = datetime.now(timezone.utc)
        state.total_checks += 1
        
        # Status changed?
        if old_status != state.status:
            self._on_status_change(service, old_status, state.status)
        
        # Auto-restart if too many failures
        if (state.consecutive_failures >= self.max_failures and 
            service.critical and 
            service.restart_cmd):
            await self._try_restart(service)
    
    def _on_status_change(
        self,
        service: ServiceConfig,
        old: ServiceStatus,
        new: ServiceStatus
    ):
        """Handle status change"""
        icon = "✅" if new == ServiceStatus.HEALTHY else "⚠️" if new == ServiceStatus.DEGRADED else "❌"
        logger.info(f"{icon} {service.name}: {old.value} → {new.value}")
        
        if self.on_status_change:
            self.on_status_change(service.name, old, new)
    
    async def _try_restart(self, service: ServiceConfig):
        """Attempt to restart a failed service"""
        logger.warning(f"Attempting to restart {service.name}...")
        
        try:
            result = subprocess.run(
                service.restart_cmd,
                shell=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Restart command sent for {service.name}")
                # Reset failure counter
                self.states[service.name].consecutive_failures = 0
            else:
                logger.error(f"Restart failed: {result.stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Failed to restart {service.name}: {e}")
    
    def get_status(self) -> Dict:
        """Get current status of all services"""
        return {
            name: {
                "status": state.status.value,
                "latency_ms": state.latency_ms,
                "last_check": state.last_check.isoformat() if state.last_check else None,
                "last_healthy": state.last_healthy.isoformat() if state.last_healthy else None,
                "uptime_percent": (
                    round((state.total_checks - state.total_failures) / state.total_checks * 100, 2)
                    if state.total_checks > 0 else 100
                )
            }
            for name, state in self.states.items()
        }
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        statuses = [s.status for s in self.states.values()]
        
        return {
            "total_services": len(self.services),
            "healthy": statuses.count(ServiceStatus.HEALTHY),
            "degraded": statuses.count(ServiceStatus.DEGRADED),
            "offline": statuses.count(ServiceStatus.OFFLINE),
            "unknown": statuses.count(ServiceStatus.UNKNOWN),
            "overall": (
                "healthy" if all(s == ServiceStatus.HEALTHY for s in statuses)
                else "degraded" if any(s == ServiceStatus.HEALTHY for s in statuses)
                else "offline"
            )
        }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

async def main():
    """Run health monitor"""
    print("=" * 60)
    print("🏥 ROXY Health Monitor")
    print("=" * 60)
    
    monitor = HealthMonitor(
        services=SERVICES,
        check_interval=30.0,
        max_failures_before_restart=3
    )
    
    # Initial check
    await monitor._check_all()
    
    # Print status
    print("\n📊 Current Status:")
    for name, state in monitor.states.items():
        icon = "✅" if state.status == ServiceStatus.HEALTHY else "⚠️" if state.status == ServiceStatus.DEGRADED else "❌"
        latency = f"{state.latency_ms:.0f}ms" if state.latency_ms else "N/A"
        print(f"  {icon} {name}: {state.status.value} ({latency})")
    
    summary = monitor.get_summary()
    print(f"\n📈 Summary: {summary['healthy']}/{summary['total_services']} healthy")
    print(f"   Overall: {summary['overall']}")
    
    # Optionally run continuously
    if os.environ.get("MONITOR_CONTINUOUS"):
        print("\n🔄 Running continuously (Ctrl+C to stop)...")
        try:
            await monitor.start()
        except KeyboardInterrupt:
            await monitor.stop()
    
    if monitor._session:
        await monitor._session.close()


if __name__ == "__main__":
    asyncio.run(main())
