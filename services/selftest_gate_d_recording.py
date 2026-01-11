#!/usr/bin/env python3
"""
Gate D: Recording Mode Selftest

Tests OBS recording start/stop functionality via WebSocket.
Verifies recording state transitions.

Requirements:
- --ensure-obs: Ensure OBS is running (cold start support)
- StartRecord → verify recording active
- StopRecord → verify recording stopped
- Check recording output files exist

Artifacts:
- gate_d_transcript.json
- gate_d_log_excerpt.txt
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid

# Reuse OBS client from Gate B
sys.path.insert(0, str(Path(__file__).parent))
from selftest_obs_ws_real import OBSWebSocketClient, ensure_obs_running

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455
RECORDING_DURATION = 3  # seconds


# ============================================================================
# Gate D Test Runner
# ============================================================================

async def run_gate_d_test(
    host: str,
    port: int,
    password: Optional[str],
    duration: int
) -> tuple[dict, str]:
    """Run the Gate D recording test."""

    results = {
        "test_name": "gate_d_recording",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recording_duration_seconds": duration,
        "tests": [],
        "result": "FAIL"
    }

    client = OBSWebSocketClient(host, port, password)
    all_passed = True

    try:
        # Connect to OBS
        hello = await client.connect()
        results["obs_connected"] = True
        results["obs_version"] = hello.get("obsWebSocketVersion")

        # Test 1: Get initial recording status
        test1 = {
            "name": "get_initial_status",
            "result": "FAIL"
        }
        try:
            client._log("Getting initial recording status...")
            status = await client.call("GetRecordStatus")
            test1["outputActive"] = status.get("outputActive", False)
            test1["outputPaused"] = status.get("outputPaused", False)
            test1["result"] = "PASS"
            client._log(f"Initial status: active={status.get('outputActive')}, paused={status.get('outputPaused')}")

            # If already recording, stop first
            if status.get("outputActive"):
                client._log("Recording already active, stopping first...")
                await client.call("StopRecord")
                await asyncio.sleep(1)

        except Exception as e:
            test1["error"] = str(e)
            client._log(f"Get status failed: {e}")
            all_passed = False
        results["tests"].append(test1)

        # Test 2: Start recording
        test2 = {
            "name": "start_recording",
            "result": "FAIL"
        }
        try:
            client._log("Calling StartRecord...")
            start_time = time.time()
            await client.call("StartRecord")
            test2["start_time"] = datetime.now(timezone.utc).isoformat()
            client._log("StartRecord succeeded")

            # Wait a moment for recording to start
            await asyncio.sleep(0.5)

            # Verify recording is active
            status = await client.call("GetRecordStatus")
            test2["outputActive_after_start"] = status.get("outputActive", False)

            if status.get("outputActive"):
                test2["result"] = "PASS"
                client._log("✓ Recording is active")
            else:
                test2["error"] = "Recording not active after StartRecord"
                client._log("✗ Recording not active after StartRecord")
                all_passed = False

        except Exception as e:
            test2["error"] = str(e)
            client._log(f"StartRecord failed: {e}")
            all_passed = False
        results["tests"].append(test2)

        # Test 3: Wait and verify recording continues
        test3 = {
            "name": "recording_active_during_wait",
            "duration_seconds": duration,
            "result": "FAIL"
        }
        try:
            client._log(f"Recording for {duration} seconds...")
            await asyncio.sleep(duration)

            # Check recording is still active
            status = await client.call("GetRecordStatus")
            test3["outputActive"] = status.get("outputActive", False)
            test3["outputTimecode"] = status.get("outputTimecode")

            if status.get("outputActive"):
                test3["result"] = "PASS"
                client._log(f"✓ Recording still active, timecode: {status.get('outputTimecode')}")
            else:
                test3["error"] = "Recording stopped unexpectedly"
                client._log("✗ Recording stopped unexpectedly")
                all_passed = False

        except Exception as e:
            test3["error"] = str(e)
            client._log(f"Recording check failed: {e}")
            all_passed = False
        results["tests"].append(test3)

        # Test 4: Stop recording
        test4 = {
            "name": "stop_recording",
            "result": "FAIL"
        }
        try:
            client._log("Calling StopRecord...")
            response = await client.call("StopRecord")
            test4["stop_time"] = datetime.now(timezone.utc).isoformat()
            test4["outputPath"] = response.get("outputPath")
            client._log(f"StopRecord succeeded, output: {response.get('outputPath')}")

            # Wait a moment for recording to stop
            await asyncio.sleep(0.5)

            # Verify recording is stopped
            status = await client.call("GetRecordStatus")
            test4["outputActive_after_stop"] = status.get("outputActive", False)

            if not status.get("outputActive"):
                test4["result"] = "PASS"
                client._log("✓ Recording is stopped")
            else:
                test4["error"] = "Recording still active after StopRecord"
                client._log("✗ Recording still active after StopRecord")
                all_passed = False

        except Exception as e:
            test4["error"] = str(e)
            client._log(f"StopRecord failed: {e}")
            all_passed = False
        results["tests"].append(test4)

        # Test 5: Verify output file exists
        test5 = {
            "name": "verify_output_file",
            "result": "FAIL"
        }
        try:
            output_path = test4.get("outputPath")
            if output_path:
                path = Path(output_path)
                test5["path"] = str(path)
                test5["exists"] = path.exists()

                if path.exists():
                    test5["size_bytes"] = path.stat().st_size
                    test5["result"] = "PASS"
                    client._log(f"✓ Output file exists: {path} ({path.stat().st_size} bytes)")
                else:
                    test5["error"] = f"Output file not found: {path}"
                    client._log(f"✗ Output file not found: {path}")
                    all_passed = False
            else:
                test5["error"] = "No output path returned"
                client._log("✗ No output path returned from StopRecord")
                all_passed = False

        except Exception as e:
            test5["error"] = str(e)
            client._log(f"File verification failed: {e}")
            all_passed = False
        results["tests"].append(test5)

        # Overall result
        passed_count = sum(1 for t in results["tests"] if t["result"] == "PASS")
        total_count = len(results["tests"])

        if all_passed and passed_count == total_count:
            results["result"] = "PASS"
        elif passed_count > 0:
            results["result"] = "PARTIAL"
        else:
            results["result"] = "FAIL"

        results["summary"] = f"{passed_count}/{total_count} tests passed"

    except ConnectionError as e:
        client._log(f"Connection error: {e}")
        results["error"] = str(e)
        results["result"] = "CONNECTION_FAILED"
    except Exception as e:
        client._log(f"Error: {e}")
        results["error"] = str(e)
        results["result"] = "FAIL"
    finally:
        await client.disconnect()

    log_excerpt = "\n".join(client.log_lines[-100:])
    return results, log_excerpt


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Gate D: Recording Mode Selftest")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"OBS host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"OBS port (default: {DEFAULT_PORT})")
    parser.add_argument("--password", default=None, help="OBS WebSocket password")
    parser.add_argument("--ensure-obs", action="store_true", help="Ensure OBS is running")
    parser.add_argument("--duration", type=int, default=RECORDING_DURATION,
                       help=f"Recording duration in seconds (default: {RECORDING_DURATION})")
    args = parser.parse_args()

    print("=" * 60)
    print("GATE D: Recording Mode Selftest")
    print("Testing OBS recording start/stop functionality")
    print("=" * 60)
    print()

    ensure_result = None

    # Ensure OBS is running if requested
    if args.ensure_obs:
        ensure_result = ensure_obs_running()
        if not ensure_result["success"]:
            print("\nFATAL: Could not ensure OBS is running")

            # Write failure artifact
            failure_result = {
                "test_name": "gate_d_recording",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": "ENSURE_OBS_FAILED",
                "ensure_obs": ensure_result
            }
            with open(SCRIPT_DIR / "gate_d_transcript.json", "w") as f:
                json.dump(failure_result, f, indent=2)

            return 1

    # Run test
    results, log_excerpt = asyncio.run(run_gate_d_test(
        args.host,
        args.port,
        args.password,
        args.duration
    ))

    # Include ensure_obs data
    if ensure_result:
        results["ensure_obs"] = {
            "used": True,
            "success": ensure_result["success"]
        }
    else:
        results["ensure_obs"] = {"used": False}

    print()
    print("=" * 60)
    print(f"GATE D RESULT: {results['result']}")
    if "summary" in results:
        print(f"Summary: {results['summary']}")
    print("=" * 60)

    # Write artifacts
    transcript_path = SCRIPT_DIR / "gate_d_transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Transcript written to: {transcript_path}")

    log_path = SCRIPT_DIR / "gate_d_log_excerpt.txt"
    with open(log_path, "w") as f:
        f.write(log_excerpt)
        if ensure_result:
            f.write("\n\n=== ENSURE OBS OUTPUT ===\n")
            f.write(ensure_result.get("launch_output", ""))
            f.write("\n=== WAIT OUTPUT ===\n")
            f.write(ensure_result.get("wait_output", ""))
    print(f"Log excerpt written to: {log_path}")

    # Return exit code
    if results["result"] == "PASS":
        return 0
    elif results["result"] == "PARTIAL":
        print("\nWARNING: Partial success")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
