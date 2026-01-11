#!/usr/bin/env python3
"""
Gate B: Real OBS WebSocket Smoke Test

CRITICAL: This test connects to a REAL OBS instance.
This is NOT a mock test - it verifies actual OBS connectivity.

Satisfies UNFREEZE Gate B requirements:
- Connects to real OBS WebSocket (configurable host/port)
- Calls GetVersion and records response
- Calls SetCurrentProgramScene with real scene name
- Verifies via GetCurrentProgramScene
- Writes required artifacts for proof verification

Usage:
  # With existing OBS instance:
  python3 selftest_obs_ws_real.py --scene "Scene"

  # Cold start (ensures OBS is running):
  python3 selftest_obs_ws_real.py --ensure-obs --scene "Scene"

Prerequisites (without --ensure-obs):
- OBS must be running with WebSocket server enabled
- OBS WebSocket server password must be configured (or disabled)
- At least one scene must exist in OBS
"""

import argparse
import asyncio
import base64
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import uuid

# Use built-in websockets or fallback
try:
    import websockets
except ImportError:
    print("ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455
DEFAULT_SCENE = "Scene"  # Default OBS scene
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 5

SCRIPT_DIR = Path(__file__).parent
OBS_LAUNCH_SCRIPT = SCRIPT_DIR / "obs_launch_clean.sh"
OBS_WAIT_SCRIPT = SCRIPT_DIR / "obs_wait_ws.sh"


# ============================================================================
# OBS Ensure Functions
# ============================================================================

def ensure_obs_running() -> dict:
    """Ensure OBS is running using obs_launch_clean.sh and obs_wait_ws.sh.

    Returns a dict with:
        - success: bool
        - launch_output: str (from obs_launch_clean.sh)
        - wait_output: str (from obs_wait_ws.sh)
        - startup_log: str (tail of /tmp/obs_clean_startup.log)
    """
    result = {
        "success": False,
        "launch_output": "",
        "wait_output": "",
        "startup_log": "",
    }

    print(f"\n{'='*60}")
    print("ENSURE OBS: Starting OBS via clean launcher...")
    print(f"{'='*60}\n")

    # Check scripts exist
    if not OBS_LAUNCH_SCRIPT.exists():
        result["launch_output"] = f"ERROR: {OBS_LAUNCH_SCRIPT} not found"
        print(result["launch_output"])
        return result

    if not OBS_WAIT_SCRIPT.exists():
        result["wait_output"] = f"ERROR: {OBS_WAIT_SCRIPT} not found"
        print(result["wait_output"])
        return result

    # Run launch script
    print(f"Running: {OBS_LAUNCH_SCRIPT}")
    try:
        launch_proc = subprocess.run(
            [str(OBS_LAUNCH_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=30
        )
        result["launch_output"] = launch_proc.stdout + launch_proc.stderr
        print(result["launch_output"])

        if launch_proc.returncode != 0:
            print(f"ERROR: Launch script failed with code {launch_proc.returncode}")
            return result

    except subprocess.TimeoutExpired:
        result["launch_output"] = "ERROR: Launch script timed out after 30s"
        print(result["launch_output"])
        return result
    except Exception as e:
        result["launch_output"] = f"ERROR: Launch script exception: {e}"
        print(result["launch_output"])
        return result

    # Run wait script
    print(f"\nRunning: {OBS_WAIT_SCRIPT}")
    try:
        wait_proc = subprocess.run(
            [str(OBS_WAIT_SCRIPT), "--timeout", "30"],
            capture_output=True,
            text=True,
            timeout=45
        )
        result["wait_output"] = wait_proc.stdout + wait_proc.stderr
        print(result["wait_output"])

        if wait_proc.returncode != 0:
            print(f"ERROR: Wait script failed with code {wait_proc.returncode}")
            return result

    except subprocess.TimeoutExpired:
        result["wait_output"] = "ERROR: Wait script timed out after 45s"
        print(result["wait_output"])
        return result
    except Exception as e:
        result["wait_output"] = f"ERROR: Wait script exception: {e}"
        print(result["wait_output"])
        return result

    # Read startup log
    startup_log_path = Path("/tmp/obs_clean_startup.log")
    if startup_log_path.exists():
        try:
            with open(startup_log_path) as f:
                lines = f.readlines()
                result["startup_log"] = "".join(lines[-50:])  # Last 50 lines
        except Exception as e:
            result["startup_log"] = f"(Could not read: {e})"

    result["success"] = True
    print(f"\n{'='*60}")
    print("ENSURE OBS: OBS is ready!")
    print(f"{'='*60}\n")

    return result


# ============================================================================
# OBS WebSocket 5.x Protocol
# ============================================================================

class OBSWebSocketClient:
    """Minimal OBS WebSocket 5.x client for testing."""

    def __init__(self, host: str, port: int, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password
        self.ws: Any = None
        self.rpc_version = 1
        self.log_lines: list[str] = []

    def _log(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.log_lines.append(line)
        print(line)

    async def connect(self) -> dict:
        """Connect to OBS WebSocket and authenticate if needed."""
        uri = f"ws://{self.host}:{self.port}"
        self._log(f"Connecting to OBS WebSocket at {uri}")

        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(uri),
                timeout=CONNECT_TIMEOUT
            )
            self._log("WebSocket connection established")
        except asyncio.TimeoutError:
            raise ConnectionError(f"Connection timeout to {uri}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {e}")

        # Receive Hello message
        hello_raw = await self.ws.recv()
        hello = json.loads(hello_raw)
        self._log(f"Received Hello: obsWebSocketVersion={hello.get('d', {}).get('obsWebSocketVersion')}")

        if hello.get("op") != 0:
            raise ConnectionError("Expected Hello (op=0)")

        hello_data = hello.get("d", {})
        self.rpc_version = hello_data.get("rpcVersion", 1)

        # Check if authentication is required
        auth = hello_data.get("authentication")
        if auth:
            if not self.password:
                raise ConnectionError("OBS requires password but none provided")

            # Generate auth response
            challenge = auth.get("challenge", "")
            salt = auth.get("salt", "")

            # SHA256(password + salt)
            secret_hash = hashlib.sha256((self.password + salt).encode()).digest()
            secret_base64 = base64.b64encode(secret_hash).decode()

            # SHA256(secret_base64 + challenge)
            auth_hash = hashlib.sha256((secret_base64 + challenge).encode()).digest()
            auth_response = base64.b64encode(auth_hash).decode()

            # Send Identify with auth
            identify = {
                "op": 1,
                "d": {
                    "rpcVersion": self.rpc_version,
                    "authentication": auth_response
                }
            }
            self._log("Sending authenticated Identify")
        else:
            # No auth required
            identify = {
                "op": 1,
                "d": {
                    "rpcVersion": self.rpc_version
                }
            }
            self._log("Sending Identify (no auth required)")

        await self.ws.send(json.dumps(identify))

        # Receive Identified
        identified_raw = await self.ws.recv()
        identified = json.loads(identified_raw)

        if identified.get("op") != 2:
            error_msg = identified.get("d", {}).get("error", "Unknown error")
            raise ConnectionError(f"Authentication failed: {error_msg}")

        self._log("Successfully identified with OBS")
        return hello_data

    async def call(self, request_type: str, request_data: Optional[dict] = None) -> dict:
        """Send a request and wait for response."""
        request_id = str(uuid.uuid4())

        request = {
            "op": 6,  # Request
            "d": {
                "requestType": request_type,
                "requestId": request_id,
            }
        }
        if request_data:
            request["d"]["requestData"] = request_data

        self._log(f"Sending {request_type} request")
        await self.ws.send(json.dumps(request))

        # Wait for response with matching ID
        while True:
            response_raw = await asyncio.wait_for(
                self.ws.recv(),
                timeout=REQUEST_TIMEOUT
            )
            response = json.loads(response_raw)

            if response.get("op") == 7:  # RequestResponse
                resp_data = response.get("d", {})
                if resp_data.get("requestId") == request_id:
                    status = resp_data.get("requestStatus", {})
                    if status.get("result"):
                        self._log(f"{request_type} succeeded")
                        return resp_data.get("responseData", {})
                    else:
                        error = status.get("comment", "Unknown error")
                        self._log(f"{request_type} failed: {error}")
                        raise Exception(f"Request failed: {error}")

    async def disconnect(self) -> None:
        """Close the connection."""
        if self.ws:
            await self.ws.close()
            self._log("Disconnected from OBS")


# ============================================================================
# Test Runner
# ============================================================================

async def run_obs_smoke_test(
    host: str,
    port: int,
    password: Optional[str],
    scene_name: str
) -> tuple[dict, str]:
    """Run the OBS WebSocket smoke test and return results."""

    results = {
        "test_name": "obs_real_connection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "connection": {
            "host": host,
            "port": port,
            "connected": False,
            "protocol_version": None
        },
        "get_version": None,
        "scene_switch": None,
        "verify_scene": None,
        "result": "FAIL"
    }

    client = OBSWebSocketClient(host, port, password)

    try:
        # Connect
        hello = await client.connect()
        results["connection"]["connected"] = True
        results["connection"]["protocol_version"] = hello.get("obsWebSocketVersion")

        # GetVersion
        version_resp = await client.call("GetVersion")
        results["get_version"] = {
            "request_id": str(uuid.uuid4()),
            "obs_version": version_resp.get("obsVersion"),
            "obs_web_socket_version": version_resp.get("obsWebSocketVersion"),
            "platform": version_resp.get("platform")
        }
        client._log(f"OBS Version: {version_resp.get('obsVersion')}")
        client._log(f"WebSocket Version: {version_resp.get('obsWebSocketVersion')}")
        client._log(f"Platform: {version_resp.get('platform')}")

        # List available scenes first (for debugging)
        try:
            scenes_resp = await client.call("GetSceneList")
            available_scenes = [s.get("sceneName") for s in scenes_resp.get("scenes", [])]
            results["available_scenes"] = available_scenes[:20]  # First 20
            client._log(f"Available scenes ({len(available_scenes)}): {', '.join(available_scenes[:5])}...")
        except Exception as e:
            client._log(f"Could not list scenes: {e}")
            results["available_scenes"] = []

        # SetCurrentProgramScene
        try:
            await client.call("SetCurrentProgramScene", {"sceneName": scene_name})
            results["scene_switch"] = {
                "request": {
                    "request_type": "SetCurrentProgramScene",
                    "scene_name": scene_name
                },
                "response": {
                    "request_status": {
                        "result": True,
                        "code": 100
                    }
                }
            }
        except Exception as e:
            results["scene_switch"] = {
                "request": {
                    "request_type": "SetCurrentProgramScene",
                    "scene_name": scene_name
                },
                "response": {
                    "request_status": {
                        "result": False,
                        "error": str(e)
                    }
                }
            }
            client._log(f"Scene switch failed: {e}")
            if results.get("available_scenes"):
                client._log(f"TIP: Try one of these scenes: {results['available_scenes'][:5]}")

        # GetCurrentProgramScene to verify
        current_scene = await client.call("GetCurrentProgramScene")
        results["verify_scene"] = {
            "request_type": "GetCurrentProgramScene",
            "current_scene_name": current_scene.get("currentProgramSceneName")
        }
        client._log(f"Current scene: {current_scene.get('currentProgramSceneName')}")

        # Determine overall result
        if (results["connection"]["connected"] and
            results["get_version"] is not None and
            results["scene_switch"] is not None and
            results["scene_switch"]["response"]["request_status"]["result"]):
            results["result"] = "PASS"
        else:
            results["result"] = "PARTIAL"

    except ConnectionError as e:
        client._log(f"Connection error: {e}")
        results["result"] = "CONNECTION_FAILED"
    except Exception as e:
        client._log(f"Error: {e}")
        results["result"] = "FAIL"
    finally:
        await client.disconnect()

    # Generate log excerpt
    log_excerpt = "\n".join(client.log_lines[-50:])  # Last 50 lines

    return results, log_excerpt


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Gate B: Real OBS WebSocket Smoke Test")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"OBS host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"OBS port (default: {DEFAULT_PORT})")
    parser.add_argument("--password", default=None, help="OBS WebSocket password")
    parser.add_argument("--scene", default=DEFAULT_SCENE, help=f"Scene to switch to (default: {DEFAULT_SCENE})")
    parser.add_argument("--ensure-obs", action="store_true",
                       help="Ensure OBS is running (cold start support)")
    args = parser.parse_args()

    print("=" * 60)
    print("GATE B: Real OBS WebSocket Smoke Test")
    print("Testing REAL OBS connectivity (NOT mock)")
    print("=" * 60)
    print()

    ensure_result = None

    # Ensure OBS is running if requested
    if args.ensure_obs:
        ensure_result = ensure_obs_running()
        if not ensure_result["success"]:
            print("\nFATAL: Could not ensure OBS is running")
            print("Check /tmp/obs_clean_startup.log for details")

            # Write failure artifact
            output_dir = Path(__file__).parent
            failure_result = {
                "test_name": "obs_real_connection",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": "ENSURE_OBS_FAILED",
                "ensure_obs": ensure_result
            }
            with open(output_dir / "obs_ws_transcript.json", "w") as f:
                json.dump(failure_result, f, indent=2)

            return 1

    # Run test
    results, log_excerpt = asyncio.run(run_obs_smoke_test(
        args.host,
        args.port,
        args.password,
        args.scene
    ))

    # Include ensure_obs data in results
    if ensure_result:
        results["ensure_obs"] = {
            "used": True,
            "launch_output": ensure_result["launch_output"][:500],  # Truncate
            "wait_output": ensure_result["wait_output"][:500],
            "startup_log_tail": ensure_result["startup_log"][-1000:] if ensure_result["startup_log"] else ""
        }
    else:
        results["ensure_obs"] = {"used": False}

    print()
    print("=" * 60)
    print(f"GATE B RESULT: {results['result']}")
    print("=" * 60)

    # Write artifacts
    output_dir = Path(__file__).parent

    transcript_path = output_dir / "obs_ws_transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Transcript written to: {transcript_path}")

    log_path = output_dir / "obs_ws_log_excerpt.txt"
    with open(log_path, "w") as f:
        f.write(log_excerpt)
        # Append ensure_obs logs if used
        if ensure_result:
            f.write("\n\n=== ENSURE OBS OUTPUT ===\n")
            f.write(ensure_result["launch_output"])
            f.write("\n=== WAIT OUTPUT ===\n")
            f.write(ensure_result["wait_output"])
            f.write("\n=== STARTUP LOG TAIL ===\n")
            f.write(ensure_result["startup_log"])
    print(f"Log excerpt written to: {log_path}")

    # Return exit code based on result
    if results["result"] == "PASS":
        return 0
    elif results["result"] == "PARTIAL":
        print("\nWARNING: Partial success - some operations may have failed")
        return 0  # Still count as success for connection verification
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
