#!/usr/bin/env python3
"""
ROXY Status Dashboard API
FastAPI endpoint for system health, ROXY status, and metrics
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from datetime import datetime
import os
import subprocess
import sys

sys.path.insert(0, '/home/mark/.roxy/services')

from roxy_core import RoxyMemory

app = FastAPI(title="ROXY Status Dashboard")

class StatusResponse(BaseModel):
    system_health: str
    roxy_service_status: str
    memory_statistics: Dict
    timestamp: str

@app.get("/api/status")
async def get_status():
    """Get ROXY system status"""
    # Check ROXY service status
    roxy_status = "unknown"
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'roxy.service'],
            capture_output=True,
            text=True,
            timeout=2
        )
        roxy_status = result.stdout.strip() if result.returncode == 0 else "inactive"
    except Exception:
        roxy_status = "unknown"
    
    # Get memory statistics
    try:
        memory = RoxyMemory()
        stats = memory.get_stats()
        memory_stats = {
            "conversations": stats.get('conversations', 0),
            "learned_facts": stats.get('learned_facts', 0),
            "preferences": stats.get('preferences', 0)
        }
    except Exception as e:
        memory_stats = {
            "conversations": 0,
            "learned_facts": 0,
            "preferences": 0,
            "error": str(e)
        }
    
    # System health
    system_health = "healthy" if roxy_status == "active" else "degraded"
    
    return StatusResponse(
        system_health=system_health,
        roxy_service_status=roxy_status,
        memory_statistics=memory_stats,
        timestamp=datetime.now().isoformat()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
