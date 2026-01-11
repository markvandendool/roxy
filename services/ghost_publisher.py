#!/usr/bin/env python3
"""
PROJECT SKYBEAM — Ghost Protocol Publisher

Publishes ROXY infrastructure state to NATS topics for visualization
on Mac Studio Ghost Protocol UI.

Topics:
  ghost.skybeam.machines   - Machine health (containers, services)
  ghost.skybeam.agents     - AI agent state (Ollama models)
  ghost.skybeam.links      - Service connections (ports, health)
  ghost.skybeam.full       - Complete infrastructure snapshot

Content Pipeline Topics (SKYBEAM-STORY-005):
  ghost.content.request    - New content request received
  ghost.content.research   - Research stage updates
  ghost.content.script     - Script generation updates
  ghost.content.assets     - Asset generation updates
  ghost.content.production - Video production updates
  ghost.content.publish    - Publishing updates
  ghost.content.status     - Content pipeline status snapshot

Usage:
  python3 ghost_publisher.py           # Run once
  python3 ghost_publisher.py --daemon  # Run continuously (30s interval)
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import nats
except ImportError:
    print("ERROR: nats-py not installed. Run: pip install nats-py")
    sys.exit(1)


NATS_URL = "nats://127.0.0.1:4222"
PUBLISH_INTERVAL = 30  # seconds


def run_cmd(cmd: str) -> str:
    """Run shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def get_docker_containers() -> list[dict[str, Any]]:
    """Get running Docker container info."""
    output = run_cmd(
        'docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}" 2>/dev/null'
    )
    containers = []
    for line in output.split("\n"):
        if line and "|" in line:
            parts = line.split("|")
            containers.append({
                "name": parts[0],
                "status": parts[1] if len(parts) > 1 else "unknown",
                "ports": parts[2] if len(parts) > 2 else "",
                "healthy": "healthy" in parts[1].lower() if len(parts) > 1 else False,
            })
    return containers


def get_systemd_services() -> list[dict[str, Any]]:
    """Get ROXY systemd service states."""
    output = run_cmd(
        'systemctl --user list-units --type=service --all 2>/dev/null | grep -E "roxy|ollama"'
    )
    services = []
    for line in output.split("\n"):
        parts = line.split()
        if len(parts) >= 3 and ".service" in parts[0]:
            services.append({
                "name": parts[0].replace(".service", ""),
                "load": parts[1] if len(parts) > 1 else "unknown",
                "active": parts[2] if len(parts) > 2 else "unknown",
                "sub": parts[3] if len(parts) > 3 else "unknown",
            })
    return services


def get_ollama_models() -> list[dict[str, Any]]:
    """Get Ollama model info."""
    output = run_cmd("ollama list 2>/dev/null")
    models = []
    for line in output.split("\n")[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 3:
            models.append({
                "name": parts[0],
                "size": parts[2] if len(parts) > 2 else "unknown",
                "modified": parts[3] if len(parts) > 3 else "unknown",
            })
    return models


def get_port_status(port: int) -> bool:
    """Check if a port is listening."""
    output = run_cmd(f"ss -tlnp 2>/dev/null | grep :{port}")
    return bool(output)


def build_machines_payload() -> dict[str, Any]:
    """Build machines (containers + services) payload."""
    return {
        "type": "machines",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "citadel",
        "containers": get_docker_containers(),
        "services": get_systemd_services(),
    }


def build_agents_payload() -> dict[str, Any]:
    """Build agents (AI models) payload."""
    return {
        "type": "agents",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "citadel",
        "models": get_ollama_models(),
        "gpus": [
            {"id": 0, "name": "W5700X", "port": 11435, "purpose": "background"},
            {"id": 1, "name": "RX 6900 XT", "port": 11434, "purpose": "primary"},
        ],
    }


def build_links_payload() -> dict[str, Any]:
    """Build service links/connections payload."""
    ports = {
        "nats": 4222,
        "postgres": 5432,
        "redis": 6379,
        "chromadb": 8000,
        "minio": 9000,
        "neo4j": 7687,
        "n8n": 5678,
        "grafana": 3030,
        "prometheus": 9099,
        "alertmanager": 9093,
        "obs": 4455,
        "ollama_primary": 11434,
        "ollama_background": 11435,
    }

    links = []
    for name, port in ports.items():
        links.append({
            "service": name,
            "port": port,
            "healthy": get_port_status(port),
        })

    return {
        "type": "links",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "citadel",
        "links": links,
    }


def build_full_payload() -> dict[str, Any]:
    """Build complete infrastructure snapshot."""
    return {
        "type": "full",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "citadel",
        "hostname": "citadel",
        "ip": "10.0.0.69",
        "machines": build_machines_payload(),
        "agents": build_agents_payload(),
        "links": build_links_payload(),
        "content": build_content_status_payload(),
        "meta": {
            "project": "SKYBEAM",
            "version": "1.1.0",
            "mcp_servers": 10,
            "mcp_tools": 39,
            "ollama_models": 18,
        },
    }


# =============================================================================
# Content Pipeline Status (SKYBEAM-STORY-005)
# =============================================================================

import os
from pathlib import Path

CONTENT_JOBS_DIR = Path.home() / ".roxy" / "content-pipeline" / "jobs"


def get_content_jobs() -> list[dict[str, Any]]:
    """Get all content pipeline jobs with their current status."""
    jobs = []

    if not CONTENT_JOBS_DIR.exists():
        return jobs

    for job_dir in sorted(CONTENT_JOBS_DIR.iterdir(), reverse=True):
        manifest_path = job_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)

                # Calculate overall progress
                stages = manifest.get("stages", {})
                completed = sum(1 for s in stages.values() if s.get("status") == "completed")
                total = len(stages)
                progress = int((completed / total) * 100) if total > 0 else 0

                # Determine current stage
                current_stage = "pending"
                for stage_name in ["research", "script", "assets", "production", "variants", "publish"]:
                    stage = stages.get(stage_name, {})
                    if stage.get("status") == "running":
                        current_stage = stage_name
                        break
                    elif stage.get("status") in ["pending", "failed"]:
                        current_stage = stage_name
                        break

                jobs.append({
                    "job_id": manifest.get("job_id", job_dir.name),
                    "topic": manifest.get("topic", ""),
                    "status": manifest.get("status", "unknown"),
                    "current_stage": current_stage,
                    "progress": progress,
                    "style": manifest.get("style", ""),
                    "platforms": manifest.get("platforms", []),
                    "created_at": manifest.get("created_at", ""),
                    "updated_at": manifest.get("updated_at", ""),
                })
            except Exception as e:
                jobs.append({
                    "job_id": job_dir.name,
                    "status": "error",
                    "error": str(e),
                })

    return jobs[:20]  # Limit to most recent 20


def get_content_handler_status() -> dict[str, Any]:
    """Check if content request handler is running."""
    output = run_cmd("curl -s http://127.0.0.1:8780/health 2>/dev/null")
    try:
        health = json.loads(output)
        return {
            "running": True,
            "status": health.get("status", "unknown"),
            "nats": health.get("nats", "unknown"),
        }
    except Exception:
        return {
            "running": False,
            "status": "offline",
            "nats": "unknown",
        }


def get_pipeline_watcher_status() -> dict[str, Any]:
    """Check if pipeline watcher is running."""
    output = run_cmd("pgrep -f 'pipeline.sh watch' 2>/dev/null")
    return {
        "running": bool(output.strip()),
        "pid": output.strip() if output.strip() else None,
    }


def build_content_status_payload() -> dict[str, Any]:
    """Build content pipeline status snapshot."""
    jobs = get_content_jobs()

    # Count jobs by status
    status_counts = {}
    for job in jobs:
        status = job.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # Find active jobs (running stages)
    active_jobs = [j for j in jobs if j.get("current_stage") and j.get("status") not in ["completed", "failed"]]

    return {
        "type": "content_status",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": "citadel",
        "handler": get_content_handler_status(),
        "watcher": get_pipeline_watcher_status(),
        "jobs": {
            "total": len(jobs),
            "by_status": status_counts,
            "active": len(active_jobs),
            "recent": jobs[:5],  # Most recent 5
        },
    }


async def publish_content_event(nc, stage: str, payload: dict[str, Any]) -> None:
    """Publish content pipeline stage event."""
    topic = f"ghost.content.{stage}"
    await nc.publish(topic, json.dumps(payload).encode())


async def publish_once(nc) -> None:
    """Publish all payloads once."""
    print(f"[{datetime.now().isoformat()}] Publishing to NATS...")

    # Infrastructure topics
    await nc.publish("ghost.skybeam.machines", json.dumps(build_machines_payload()).encode())
    await nc.publish("ghost.skybeam.agents", json.dumps(build_agents_payload()).encode())
    await nc.publish("ghost.skybeam.links", json.dumps(build_links_payload()).encode())
    await nc.publish("ghost.skybeam.full", json.dumps(build_full_payload()).encode())

    # Content pipeline topic (SKYBEAM-STORY-005)
    await nc.publish("ghost.content.status", json.dumps(build_content_status_payload()).encode())

    await nc.flush()
    print(f"[{datetime.now().isoformat()}] Published to ghost.skybeam.* and ghost.content.* topics")


async def run_daemon() -> None:
    """Run publisher as daemon with periodic updates."""
    print(f"PROJECT SKYBEAM — Ghost Protocol Publisher")
    print(f"Connecting to NATS at {NATS_URL}...")

    nc = await nats.connect(NATS_URL)
    print(f"Connected! Publishing every {PUBLISH_INTERVAL}s...")

    try:
        while True:
            await publish_once(nc)
            await asyncio.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await nc.drain()


async def run_once() -> None:
    """Publish once and exit."""
    print(f"PROJECT SKYBEAM — Ghost Protocol Publisher (one-shot)")
    print(f"Connecting to NATS at {NATS_URL}...")

    nc = await nats.connect(NATS_URL)
    await publish_once(nc)
    await nc.drain()
    print("Done!")


def main():
    if "--daemon" in sys.argv:
        asyncio.run(run_daemon())
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
