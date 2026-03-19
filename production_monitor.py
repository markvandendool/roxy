#!/usr/bin/env python3
"""
Production State Monitor for ROXY
Real-time awareness of MindSong/SkyBeam production ecosystem

Provides:
- SkyBeam render queue status
- StackKraft campaign status
- ShotCaller schedule awareness
- GPU utilization monitoring
- Luno orchestrator state
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("roxy.production_monitor")

# Cache settings
CACHE_TTL_SECONDS = 30  # Cache production state for 30 seconds

# Production system paths (configurable)
SKYBEAM_QUEUE_PATH = os.getenv("SKYBEAM_QUEUE_PATH", "/home/mark/skybeam/queue")
STACKKRAFT_DATA_PATH = os.getenv("STACKKRAFT_DATA_PATH", "/home/mark/stackkraft/data")
SHOT_CALLER_PATH = os.getenv("SHOT_CALLER_PATH", "/home/mark/shotcaller")


class ProductionStateMonitor:
    """
    Monitors MindSong production ecosystem state.
    Provides cached, real-time awareness for ROXY prompts.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid."""
        if key not in self._cache or key not in self._cache_time:
            return False
        age = time.time() - self._cache_time[key]
        return age < CACHE_TTL_SECONDS
    
    def _update_cache(self, key: str, value: Any):
        """Update cache entry."""
        self._cache[key] = value
        self._cache_time[key] = time.time()
    
    def get_skybeam_status(self) -> Dict[str, Any]:
        """
        Get SkyBeam render queue status.
        
        Returns:
            {
                "status": "rendering" | "idle" | "error",
                "queue_length": int,
                "current_render": str,
                "gpu_utilization": float,
                "estimated_completion": str
            }
        """
        if self._is_cache_valid("skybeam"):
            return self._cache["skybeam"]
        
        state = {
            "status": "unknown",
            "queue_length": 0,
            "current_render": None,
            "gpu_utilization": 0.0,
            "estimated_completion": None,
            "last_updated": datetime.now().isoformat(),
        }
        
        try:
            # Check queue directory
            queue_path = Path(SKYBEAM_QUEUE_PATH)
            if queue_path.exists():
                queue_files = list(queue_path.glob("*.render")) + list(queue_path.glob("*.mp4"))
                state["queue_length"] = len(queue_files)
                
                # Check for active render
                active_files = list(queue_path.glob("*.active"))
                if active_files:
                    state["status"] = "rendering"
                    state["current_render"] = str(active_files[0].name)
                elif queue_files:
                    state["status"] = "queued"
                else:
                    state["status"] = "idle"
            
            # Check GPU utilization via system monitoring
            try:
                import subprocess
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    state["gpu_utilization"] = float(result.stdout.strip().split('\n')[0])
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
                pass
            
            state["healthy"] = True
            
        except Exception as e:
            state["error"] = str(e)
            state["healthy"] = False
            logger.debug(f"SkyBeam status check failed: {e}")
        
        self._update_cache("skybeam", state)
        return state
    
    def get_stackkraft_status(self) -> Dict[str, Any]:
        """
        Get StackKraft monetization campaign status.
        
        Returns:
            {
                "active_campaigns": int,
                "total_revenue": float,
                "views": int,
                "platforms": List[str]
            }
        """
        if self._is_cache_valid("stackkraft"):
            return self._cache["stackkraft"]
        
        state = {
            "active_campaigns": 0,
            "total_revenue": 0.0,
            "views": 0,
            "platforms": [],
            "last_updated": datetime.now().isoformat(),
        }
        
        try:
            # Check StackKraft data directory
            data_path = Path(STACKKRAFT_DATA_PATH)
            if data_path.exists():
                # Look for campaign JSON files
                campaign_files = list(data_path.glob("campaign_*.json"))
                state["active_campaigns"] = len(campaign_files)
                
                # Read revenue data if available
                revenue_file = data_path / "revenue.json"
                if revenue_file.exists():
                    with open(revenue_file) as f:
                        revenue_data = json.load(f)
                        state["total_revenue"] = revenue_data.get("total", 0.0)
                        state["views"] = revenue_data.get("views", 0)
                
                # Detect platforms
                platform_files = list(data_path.glob("platform_*.json"))
                state["platforms"] = [
                    f.stem.replace("platform_", "") for f in platform_files
                ]
            
            state["healthy"] = True
            
        except Exception as e:
            state["error"] = str(e)
            state["healthy"] = False
            logger.debug(f"StackKraft status check failed: {e}")
        
        self._update_cache("stackkraft", state)
        return state
    
    def get_shotcaller_status(self) -> Dict[str, Any]:
        """
        Get ShotCaller production schedule status.
        
        Returns:
            {
                "today_shots": int,
                "completed_shots": int,
                "next_deadline": str,
                "schedule_status": "on_track" | "behind" | "ahead"
            }
        """
        if self._is_cache_valid("shotcaller"):
            return self._cache["shotcaller"]
        
        state = {
            "today_shots": 0,
            "completed_shots": 0,
            "next_deadline": None,
            "schedule_status": "unknown",
            "last_updated": datetime.now().isoformat(),
        }
        
        try:
            # Check ShotCaller schedule directory
            schedule_path = Path(SHOT_CALLER_PATH)
            if schedule_path.exists():
                # Look for today's schedule
                today = datetime.now().strftime("%Y-%m-%d")
                today_file = schedule_path / f"schedule_{today}.json"
                
                if today_file.exists():
                    with open(today_file) as f:
                        schedule_data = json.load(f)
                        shots = schedule_data.get("shots", [])
                        state["today_shots"] = len(shots)
                        state["completed_shots"] = sum(
                            1 for s in shots if s.get("status") == "completed"
                        )
                        state["next_deadline"] = schedule_data.get("next_deadline")
                        state["schedule_status"] = schedule_data.get("status", "unknown")
            
            state["healthy"] = True
            
        except Exception as e:
            state["error"] = str(e)
            state["healthy"] = False
            logger.debug(f"ShotCaller status check failed: {e}")
        
        self._update_cache("shotcaller", state)
        return state
    
    def get_luno_status(self) -> Dict[str, Any]:
        """
        Get Luno orchestrator status.
        
        Returns:
            {
                "active_tasks": int,
                "completed_tasks": int,
                "failed_tasks": int,
                "agents_online": List[str]
            }
        """
        if self._is_cache_valid("luno"):
            return self._cache["luno"]
        
        state = {
            "active_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "agents_online": [],
            "last_updated": datetime.now().isoformat(),
        }
        
        try:
            # Check NATS for Luno task status
            import requests
            resp = requests.get("http://localhost:4222/api/v1/streams", timeout=2)
            if resp.status_code == 200:
                streams = resp.json().get("streams", [])
                # Look for Luno-related streams
                luno_streams = [s for s in streams if "luno" in s.get("name", "").lower()]
                if luno_streams:
                    state["healthy"] = True
        except Exception:
            # Fallback to simple process check
            try:
                import subprocess
                result = subprocess.run(
                    ["pgrep", "-f", "luno"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    state["healthy"] = True
                    state["agents_online"] = ["luno"]
            except Exception:
                pass
        
        # Default healthy if we can't check
        if "healthy" not in state:
            state["healthy"] = True  # Assume healthy unless we detect problems
        
        self._update_cache("luno", state)
        return state
    
    def get_full_production_status(self) -> Dict[str, Any]:
        """
        Get complete production ecosystem status.
        
        Returns:
            Combined status of all production systems.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "skybeam": self.get_skybeam_status(),
            "stackkraft": self.get_stackkraft_status(),
            "shotcaller": self.get_shotcaller_status(),
            "luno": self.get_luno_status(),
            "overall_healthy": all([
                self._cache.get(k, {}).get("healthy", False)
                for k in ["skybeam", "stackkraft", "shotcaller", "luno"]
            ])
        }
    
    def get_production_summary(self) -> str:
        """
        Get human-readable production summary for ROXY prompts.
        """
        status = self.get_full_production_status()
        
        lines = []
        
        # SkyBeam
        sb = status.get("skybeam", {})
        if sb.get("status") == "rendering":
            lines.append(f"🔄 SkyBeam: Rendering '{sb.get('current_render', 'unknown')}' ({sb.get('gpu_utilization', 0):.0f}% GPU)")
        elif sb.get("status") == "queued":
            lines.append(f"📋 SkyBeam: {sb.get('queue_length', 0)} videos queued")
        else:
            lines.append(f"💤 SkyBeam: Idle")
        
        # StackKraft
        sk = status.get("stackkraft", {})
        if sk.get("active_campaigns", 0) > 0:
            lines.append(f"💰 StackKraft: {sk.get('active_campaigns')} campaigns, ${sk.get('total_revenue', 0):.2f} revenue")
        else:
            lines.append(f"📊 StackKraft: No active campaigns")
        
        # ShotCaller
        sc = status.get("shotcaller", {})
        if sc.get("today_shots", 0) > 0:
            pct = (sc.get("completed_shots", 0) / max(sc.get("today_shots", 1), 1)) * 100
            lines.append(f"🎬 ShotCaller: {sc.get('completed_shots', 0)}/{sc.get('today_shots', 0)} shots ({pct:.0f}%)")
        else:
            lines.append(f"📅 ShotCaller: No shots scheduled today")
        
        # Luno
        lu = status.get("luno", {})
        if lu.get("agents_online"):
            lines.append(f"🤖 Luno: {' '.join(lu.get('agents_online', []))} online")
        else:
            lines.append(f"💤 Luno: Standby")
        
        return "\n".join(lines) if lines else "Production systems status unknown"


# Global monitor instance
_monitor = None


def get_production_monitor() -> ProductionStateMonitor:
    """Get or create global production monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ProductionStateMonitor()
    return _monitor


def get_production_status() -> Dict[str, Any]:
    """Get current production status."""
    return get_production_monitor().get_full_production_status()


def get_production_summary() -> str:
    """Get human-readable production summary."""
    return get_production_monitor().get_production_summary()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("MindSong Production Status")
    print("=" * 50)
    print()
    print(get_production_summary())
