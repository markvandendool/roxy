#!/usr/bin/env python3
"""
Background Scheduler - 24/7 autonomous operation for ROXY
Schedules and executes background tasks with health monitoring.
"""
import asyncio
import json
import logging
import os
import signal
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("roxy.scheduler")

SCHEDULER_CONFIG = Path.home() / ".roxy" / "data" / "scheduler_config.json"
SCHEDULER_STATE = Path.home() / ".roxy" / "data" / "scheduler_state.json"
SCHEDULER_HEARTBEAT = Path.home() / ".roxy" / "data" / "scheduler_heartbeat.json"
SCHEDULER_LEASE = Path.home() / ".roxy" / "data" / "scheduler_lease.json"


@dataclass
class ScheduledTask:
    name: str
    interval_seconds: float
    handler: Callable = field(default=None)
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    error_count: int = 0
    max_errors: int = 3
    description: str = ""
    timeout_seconds: float = 300
    
    def should_run(self) -> bool:
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return time.time() >= self.next_run
    
    def update_after_run(self, success: bool):
        self.last_run = time.time()
        if success:
            self.error_count = 0
        else:
            self.error_count += 1
        self.next_run = time.time() + self.interval_seconds


@dataclass
class TaskResult:
    task_name: str
    success: bool
    duration: float
    error: Optional[str] = None
    output: Optional[str] = None


class BackgroundScheduler:
    """
    24/7 background task scheduler for ROXY.
    
    Features:
    - Configurable task intervals
    - Automatic retry with backoff
    - Health monitoring
    - State persistence
    - Graceful shutdown
    """
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._tick_interval = 60.0
        self._health_check_interval = 300.0
        self._last_health_check = 0
        self.instance_id = str(uuid.uuid4())
        self._lease_ttl = max(120.0, float(os.getenv("ROXY_SCHEDULER_LEASE_TTL_SEC", "300")))
        self._heartbeat_interval = max(5.0, float(os.getenv("ROXY_SCHEDULER_HEARTBEAT_SEC", "30")))
        self._last_heartbeat_write = 0.0
        
        self._register_default_tasks()
        self._load_state()
    
    def _register_default_tasks(self):
        """Register default background tasks."""
        self.register_task(ScheduledTask(
            name="memory_consolidation",
            interval_seconds=3600,
            description="Consolidate memory, forget low-importance memories",
            timeout_seconds=600,
        ))
        
        self.register_task(ScheduledTask(
            name="story_selection_check",
            interval_seconds=300,
            description="Check for new stories to work on",
            timeout_seconds=30,
        ))
        
        self.register_task(ScheduledTask(
            name="health_check",
            interval_seconds=300,
            description="System health check",
            timeout_seconds=60,
        ))
        
        self.register_task(ScheduledTask(
            name="cleanup_old_logs",
            interval_seconds=86400,
            description="Clean up old log files",
            timeout_seconds=120,
        ))
        
        self.register_task(ScheduledTask(
            name="sync_skoreq_status",
            interval_seconds=600,
            description="Sync SKOREQ story statuses",
            timeout_seconds=30,
        ))

        self.register_task(ScheduledTask(
            name="mission_execution",
            interval_seconds=900,
            description="Execute next story from SKOREQ as a mission",
            timeout_seconds=600,
        ))
    
    def register_task(
        self,
        task: ScheduledTask,
        handler: Optional[Callable] = None
    ):
        """Register a background task."""
        self.tasks[task.name] = task
        if handler:
            task.handler = handler
    
    def set_handler(self, name: str, handler: Callable):
        """Set the handler for a task."""
        if name in self.tasks:
            self.tasks[name].handler = handler
    
    async def _execute_task(self, task: ScheduledTask) -> TaskResult:
        """Execute a single task with timeout."""
        start = time.time()
        
        if not task.handler:
            return TaskResult(
                task_name=task.name,
                success=False,
                duration=time.time() - start,
                error="No handler registered",
            )
        
        try:
            if asyncio.iscoroutinefunction(task.handler):
                result = await asyncio.wait_for(
                    task.handler(),
                    timeout=task.timeout_seconds
                )
            else:
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, task.handler),
                    timeout=task.timeout_seconds,
                )
            
            duration = time.time() - start
            return TaskResult(
                task_name=task.name,
                success=True,
                duration=duration,
                output=str(result)[:500] if result else None,
            )
            
        except asyncio.TimeoutError:
            duration = time.time() - start
            logger.warning(f"Task {task.name} timed out after {task.timeout_seconds}s")
            return TaskResult(
                task_name=task.name,
                success=False,
                duration=duration,
                error=f"Timeout after {task.timeout_seconds}s",
            )
        except Exception as e:
            duration = time.time() - start
            logger.error(f"Task {task.name} failed: {e}")
            return TaskResult(
                task_name=task.name,
                success=False,
                duration=duration,
                error=str(e),
            )
    
    async def _run_ready_tasks(self):
        """Run all tasks that are due."""
        for name, task in self.tasks.items():
            if task.should_run():
                logger.info(f"Running task: {name}")
                result = await self._execute_task(task)
                task.update_after_run(result.success)
                
                if result.success:
                    logger.info(f"Task {name} completed in {result.duration:.1f}s")
                else:
                    logger.warning(f"Task {name} failed: {result.error}")
                    
                    if task.error_count >= task.max_errors:
                        logger.error(f"Task {name} exceeded max errors, disabling")
                        task.enabled = False
    
    async def _health_check(self):
        """Perform system health check."""
        checks = {}
        
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8766/health", timeout=5)
            checks["roxy_core"] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
        except:
            checks["roxy_core"] = "unreachable"
        
        try:
            import requests
            resp = requests.get("http://127.0.0.1:11435/api/tags", timeout=5)
            checks["ollama"] = "ok" if resp.status_code == 200 else f"error:{resp.status_code}"
        except:
            checks["ollama"] = "unreachable"
        
        logger.info(f"Health check: {checks}")
        return checks
    
    def _get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        task_status = {}
        for name, task in self.tasks.items():
            task_status[name] = {
                "enabled": task.enabled,
                "interval": task.interval_seconds,
                "last_run": task.last_run,
                "next_run": task.next_run,
                "error_count": task.error_count,
            }
        
        return {
            "running": self.running,
            "instance_id": self.instance_id,
            "tasks": task_status,
            "active_tasks": sum(1 for t in self.tasks.values() if t.enabled),
            "lease_file": str(SCHEDULER_LEASE),
            "heartbeat_file": str(SCHEDULER_HEARTBEAT),
            "timestamp": datetime.now().isoformat(),
        }
    
    async def start(self):
        """Start the scheduler."""
        logger.info("Starting background scheduler...")
        if not self._acquire_lease():
            logger.warning("Background scheduler lease is held by another live instance; refusing to start")
            return
        self.running = True
        self._loop = asyncio.get_event_loop()
        self._write_runtime_files(status="starting")
        
        while self.running:
            try:
                await self._run_ready_tasks()
                self._write_runtime_files(status="running")
                
                if time.time() - self._last_health_check >= self._health_check_interval:
                    await self._health_check()
                    self._last_health_check = time.time()
                    self._save_state()
                
                await asyncio.sleep(self._tick_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
        
        logger.info("Background scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self._save_state()
        self._write_runtime_files(status="stopped")
        self._release_lease()
    
    def _load_state(self):
        """Load scheduler state from disk."""
        if not SCHEDULER_STATE.exists():
            return
        
        try:
            with open(SCHEDULER_STATE) as f:
                state = json.load(f)
            
            task_states = state.get("tasks", {})
            for name, saved in task_states.items():
                if name in self.tasks:
                    self.tasks[name].last_run = saved.get("last_run")
                    self.tasks[name].next_run = saved.get("next_run")
                    self.tasks[name].error_count = saved.get("error_count", 0)
                    self.tasks[name].enabled = saved.get("enabled", True)
            
            logger.info(f"Loaded scheduler state: {len(task_states)} tasks")
        except Exception as e:
            logger.debug(f"Failed to load scheduler state: {e}")
    
    def _save_state(self):
        """Save scheduler state to disk."""
        SCHEDULER_STATE.parent.mkdir(parents=True, exist_ok=True)
        
        task_states = {}
        for name, task in self.tasks.items():
            task_states[name] = {
                "last_run": task.last_run,
                "next_run": task.next_run,
                "error_count": task.error_count,
                "enabled": task.enabled,
            }
        
        state = {
            "tasks": task_states,
            "saved_at": datetime.now().isoformat(),
        }
        
        try:
            with open(SCHEDULER_STATE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")

    def _write_runtime_files(self, status: str = "running"):
        """Persist scheduler heartbeat and lease state for crash detection."""
        now = time.time()
        if status == "running" and (now - self._last_heartbeat_write) < self._heartbeat_interval:
            return
        SCHEDULER_HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "instance_id": self.instance_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "lease_expires_at": datetime.fromtimestamp(now + self._lease_ttl).isoformat(),
            "active_tasks": [name for name, task in self.tasks.items() if task.enabled],
        }
        try:
            with open(SCHEDULER_HEARTBEAT, "w") as f:
                json.dump(payload, f, indent=2)
            with open(SCHEDULER_LEASE, "w") as f:
                json.dump(payload, f, indent=2)
            self._last_heartbeat_write = now
        except Exception as e:
            logger.error(f"Failed to write scheduler heartbeat: {e}")

    def _load_lease(self) -> Optional[Dict[str, Any]]:
        try:
            if not SCHEDULER_LEASE.exists():
                return None
            with open(SCHEDULER_LEASE) as f:
                return json.load(f)
        except Exception:
            return None

    def _acquire_lease(self) -> bool:
        lease = self._load_lease()
        if lease:
            lease_expires_at = lease.get("lease_expires_at")
            lease_owner = lease.get("instance_id")
            if lease_owner == self.instance_id:
                return True
            if lease_expires_at:
                try:
                    expires = datetime.fromisoformat(lease_expires_at).timestamp()
                    if expires > time.time():
                        return False
                except Exception:
                    pass
        self._write_runtime_files(status="leased")
        return True

    def _release_lease(self):
        try:
            lease = self._load_lease() or {}
            if lease.get("instance_id") == self.instance_id and SCHEDULER_LEASE.exists():
                SCHEDULER_LEASE.unlink()
        except Exception:
            pass


def create_memory_consolidation_task():
    """Task: Consolidate memory."""
    def run():
        try:
            from memory_consolidation import run_consolidation
            result = run_consolidation()
            return f"Consolidated: {result.get('deleted', 0)} memories removed"
        except Exception as e:
            return f"Failed: {e}"
    return run


def create_story_check_task():
    """Task: Check for new stories."""
    def run():
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            summary = selector.get_status_summary()
            next_story = selector.get_next_story()
            return f"Stories: {summary['total_stories']}, Next: {next_story.id if next_story else 'none'}"
        except Exception as e:
            return f"Failed: {e}"
    return run


def create_skoreq_sync_task():
    """Task: Force-refresh SKOREQ index and summarize live status."""
    def run():
        try:
            from story_selector import StorySelector
            selector = StorySelector()
            selector._load_index(force=True)
            summary = selector.get_status_summary()
            return (
                f"SKOREQ synced: {summary.get('total_stories', 0)} stories, "
                f"{summary.get('todo', 0)} todo, {summary.get('eligible_now', 0)} eligible"
            )
        except Exception as e:
            return f"Failed: {e}"
    return run


def create_health_check_task():
    """Task: System health check."""
    async def run():
        try:
            import requests
            resp = requests.get("http://127.0.0.1:8766/health", timeout=5)
            return f"ROXY: {resp.status_code}"
        except Exception as e:
            return f"Failed: {e}"
    return run


def create_cleanup_logs_task():
    """Task: Clean up old logs."""
    def run():
        import glob
        import shutil
        import os as os_module
        
        log_dir = Path.home() / ".roxy" / "logs"
        if not log_dir.exists():
            return "No log dir"
        
        deleted = 0
        cutoff = time.time() - (7 * 86400)
        
        for log_file in glob.glob(str(log_dir / "*.log")):
            if os_module.path.getmtime(log_file) < cutoff:
                try:
                    os_module.remove(log_file)
                    deleted += 1
                except:
                    pass
        
        return f"Deleted {deleted} old log files"

    return run


def setup_scheduler(scheduler: BackgroundScheduler):
    """Setup handlers for default tasks."""
    scheduler.set_handler("memory_consolidation", create_memory_consolidation_task())
    scheduler.set_handler("story_selection_check", create_story_check_task())
    scheduler.set_handler("sync_skoreq_status", create_skoreq_sync_task())
    if "sync_skoreq_status" in scheduler.tasks:
        sync_task = scheduler.tasks["sync_skoreq_status"]
        sync_task.enabled = True
        sync_task.error_count = 0
        if sync_task.next_run is None or sync_task.next_run < time.time():
            sync_task.next_run = time.time() + 5
    scheduler.set_handler("health_check", create_health_check_task())
    scheduler.set_handler("cleanup_old_logs", create_cleanup_logs_task())

    try:
        from mission_supervisor import create_mission_task
        scheduler.set_handler("mission_execution", create_mission_task())
    except Exception as e:
        logger.warning(f"Mission supervisor not available: {e}")


if __name__ == "__main__":
    async def main():
        scheduler = BackgroundScheduler()
        setup_scheduler(scheduler)
        
        print("Background Scheduler Status:")
        print(json.dumps(scheduler._get_status(), indent=2))
        
        print("\nStarting scheduler (Ctrl+C to stop)...")
        try:
            await scheduler.start()
        except KeyboardInterrupt:
            scheduler.stop()
    
    asyncio.run(main())
