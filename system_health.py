#!/usr/bin/env python3
"""
System Health Monitor for ROXY
Monitors GPU temps, memory, Docker, and services

Usage:
  python3 system_health.py          # One-time check
  python3 system_health.py --watch  # Continuous monitoring
  python3 system_health.py --json   # JSON output for Grafana

Part of LUNA-000 CITADEL - Monitoring & Observability
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Thresholds for alerts
THRESHOLDS = {
    "gpu_temp_warn": 75,
    "gpu_temp_critical": 85,
    "memory_warn_percent": 80,
    "disk_warn_percent": 85,
    "cpu_warn_percent": 90
}

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except:
        return ""

def get_gpu_info():
    """Get AMD GPU info via ROCm"""
    gpus = []

    # Try rocm-smi
    output = run_cmd("rocm-smi --showtemp --showuse --showmeminfo vram --json 2>/dev/null")

    if output:
        try:
            data = json.loads(output)
            for card_id, card_data in data.items():
                if card_id.startswith("card"):
                    gpu = {
                        "id": card_id,
                        "temp": None,
                        "usage": None,
                        "vram_used": None,
                        "vram_total": None
                    }

                    # Parse temperature
                    if "Temperature (Sensor edge) (C)" in card_data:
                        gpu["temp"] = float(card_data["Temperature (Sensor edge) (C)"])

                    # Parse usage
                    if "GPU use (%)" in card_data:
                        gpu["usage"] = float(card_data["GPU use (%)"])

                    # Parse VRAM
                    if "VRAM Total Memory (B)" in card_data:
                        gpu["vram_total"] = int(card_data["VRAM Total Memory (B)"]) / (1024**3)
                    if "VRAM Total Used Memory (B)" in card_data:
                        gpu["vram_used"] = int(card_data["VRAM Total Used Memory (B)"]) / (1024**3)

                    gpus.append(gpu)
        except:
            pass

    # Fallback: parse sensors output
    if not gpus:
        sensors = run_cmd("sensors 2>/dev/null | grep -A5 'amdgpu'")
        if sensors:
            # Basic parsing
            for line in sensors.split("\n"):
                if "edge" in line.lower() and "+" in line:
                    try:
                        temp = float(line.split("+")[1].split("°")[0])
                        gpus.append({"id": "amdgpu", "temp": temp})
                    except:
                        pass

    return gpus

def get_memory_info():
    """Get system memory info"""
    output = run_cmd("free -b")
    if not output:
        return None

    lines = output.split("\n")
    for line in lines:
        if line.startswith("Mem:"):
            parts = line.split()
            total = int(parts[1]) / (1024**3)
            used = int(parts[2]) / (1024**3)
            return {
                "total_gb": round(total, 1),
                "used_gb": round(used, 1),
                "percent": round((used/total)*100, 1)
            }
    return None

def get_disk_info():
    """Get disk usage info"""
    output = run_cmd("df -B1 / | tail -1")
    if not output:
        return None

    parts = output.split()
    total = int(parts[1]) / (1024**3)
    used = int(parts[2]) / (1024**3)

    return {
        "total_gb": round(total, 1),
        "used_gb": round(used, 1),
        "percent": round((used/total)*100, 1)
    }

def get_cpu_info():
    """Get CPU usage and load"""
    # Load average
    load = run_cmd("cat /proc/loadavg")
    load_1, load_5, load_15 = 0, 0, 0
    if load:
        parts = load.split()
        load_1 = float(parts[0])
        load_5 = float(parts[1])
        load_15 = float(parts[2])

    # CPU count
    cpu_count = int(run_cmd("nproc") or "1")

    # CPU usage (quick sample)
    usage = run_cmd("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
    cpu_percent = float(usage) if usage else 0

    return {
        "cores": cpu_count,
        "usage_percent": round(cpu_percent, 1),
        "load_1m": load_1,
        "load_5m": load_5,
        "load_15m": load_15
    }

def get_docker_status():
    """Get Docker container status"""
    output = run_cmd("docker ps --format '{{.Names}}:{{.Status}}' 2>/dev/null")
    if not output:
        return []

    containers = []
    for line in output.split("\n"):
        if ":" in line:
            name, status = line.split(":", 1)
            healthy = "Up" in status
            containers.append({
                "name": name,
                "status": status,
                "healthy": healthy
            })

    return containers

def get_service_status(services):
    """Check systemd service status"""
    results = []
    for service in services:
        output = run_cmd(f"systemctl is-active {service} 2>/dev/null")
        results.append({
            "name": service,
            "active": output == "active"
        })
    return results

def get_ollama_status():
    """Check Ollama status"""
    output = run_cmd("curl -s http://127.0.0.1:11435/api/tags 2>/dev/null")
    if output:
        try:
            data = json.loads(output)
            models = [m["name"] for m in data.get("models", [])]
            return {"running": True, "models": models}
        except:
            pass
    return {"running": False, "models": []}

def collect_health():
    """Collect all health metrics"""
    return {
        "timestamp": datetime.now().isoformat(),
        "gpus": get_gpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "cpu": get_cpu_info(),
        "docker": get_docker_status(),
        "services": get_service_status(["ollama", "grafana-server", "docker"]),
        "ollama": get_ollama_status()
    }

def check_alerts(health):
    """Check for alert conditions"""
    alerts = []

    # GPU temperature
    for gpu in health.get("gpus", []):
        temp = gpu.get("temp")
        if temp:
            if temp >= THRESHOLDS["gpu_temp_critical"]:
                alerts.append(f"CRITICAL: {gpu['id']} at {temp}°C")
            elif temp >= THRESHOLDS["gpu_temp_warn"]:
                alerts.append(f"WARNING: {gpu['id']} at {temp}°C")

    # Memory
    mem = health.get("memory")
    if mem and mem["percent"] >= THRESHOLDS["memory_warn_percent"]:
        alerts.append(f"WARNING: Memory at {mem['percent']}%")

    # Disk
    disk = health.get("disk")
    if disk and disk["percent"] >= THRESHOLDS["disk_warn_percent"]:
        alerts.append(f"WARNING: Disk at {disk['percent']}%")

    # Services
    for svc in health.get("services", []):
        if not svc["active"]:
            alerts.append(f"WARNING: Service {svc['name']} not running")

    return alerts

def print_health(health, json_mode=False):
    """Print health status"""
    if json_mode:
        print(json.dumps(health, indent=2))
        return

    print(f"\n{'='*60}")
    print(f"  JARVIS-1 System Health - {health['timestamp'][:19]}")
    print(f"{'='*60}\n")

    # GPUs
    print("GPU Status:")
    for gpu in health.get("gpus", []):
        temp = gpu.get("temp", "N/A")
        usage = gpu.get("usage", "N/A")
        vram = f"{gpu.get('vram_used', 0):.1f}/{gpu.get('vram_total', 0):.1f} GB" if gpu.get("vram_total") else "N/A"
        print(f"  {gpu['id']}: {temp}°C | Usage: {usage}% | VRAM: {vram}")

    # Memory
    mem = health.get("memory")
    if mem:
        print(f"\nMemory: {mem['used_gb']:.1f}/{mem['total_gb']:.1f} GB ({mem['percent']}%)")

    # Disk
    disk = health.get("disk")
    if disk:
        print(f"Disk: {disk['used_gb']:.1f}/{disk['total_gb']:.1f} GB ({disk['percent']}%)")

    # CPU
    cpu = health.get("cpu")
    if cpu:
        print(f"CPU: {cpu['usage_percent']}% | Load: {cpu['load_1m']:.2f} / {cpu['load_5m']:.2f} / {cpu['load_15m']:.2f}")

    # Docker
    docker = health.get("docker", [])
    if docker:
        print(f"\nDocker Containers ({len(docker)}):")
        for c in docker:
            status = "✓" if c["healthy"] else "✗"
            print(f"  {status} {c['name']}: {c['status']}")

    # Services
    services = health.get("services", [])
    if services:
        print(f"\nServices:")
        for svc in services:
            status = "✓" if svc["active"] else "✗"
            print(f"  {status} {svc['name']}")

    # Ollama
    ollama = health.get("ollama", {})
    if ollama.get("running"):
        print(f"\nOllama: Running ({len(ollama.get('models', []))} models)")
    else:
        print(f"\nOllama: NOT RUNNING")

    # Alerts
    alerts = check_alerts(health)
    if alerts:
        print(f"\n⚠️  ALERTS:")
        for alert in alerts:
            print(f"  {alert}")

    print()

def main():
    json_mode = "--json" in sys.argv
    watch_mode = "--watch" in sys.argv

    if watch_mode:
        print("Monitoring system health (Ctrl+C to stop)...")
        try:
            while True:
                health = collect_health()
                os.system("clear")
                print_health(health, json_mode)
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        health = collect_health()
        print_health(health, json_mode)

        # Return non-zero if alerts
        alerts = check_alerts(health)
        if alerts:
            sys.exit(1)

if __name__ == "__main__":
    main()
