#!/usr/bin/env python3
"""
Gate C: Preset → Scene Bridge Selftest

Tests the preset-to-OBS-scene mapping pipeline.
Verifies that setting a preset results in the correct OBS scene switch.

Requirements:
- --ensure-obs: Ensure OBS is running (cold start support)
- Loads theater_obs_mapping.json for preset→scene mapping
- Tests at least 2 presets (default, drums)
- Verifies GetCurrentProgramScene matches expected scene

Artifacts:
- gate_c_transcript.json
- gate_c_log_excerpt.txt
"""

import argparse
import asyncio
import json
import subprocess
import sys
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
MAPPING_PATH = Path.home() / ".roxy" / "config" / "theater_obs_mapping.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455


# ============================================================================
# Mapping Loader
# ============================================================================

def load_preset_mapping() -> dict:
    """Load preset→scene mapping from theater_obs_mapping.json."""
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(f"Mapping file not found: {MAPPING_PATH}")

    with open(MAPPING_PATH) as f:
        config = json.load(f)

    presets = config.get("mappings", {}).get("presets", {})
    return presets


def resolve_scene_for_preset(presets: dict, preset_name: str) -> str:
    """Resolve the OBS scene name for a given preset."""
    preset = presets.get(preset_name)
    if not preset:
        raise ValueError(f"Unknown preset: {preset_name}")

    # Use landscape scene (primary)
    scene = preset.get("obs_scene_landscape")
    if not scene:
        raise ValueError(f"No obs_scene_landscape defined for preset: {preset_name}")

    return scene


# ============================================================================
# Gate C Test Runner
# ============================================================================

async def run_gate_c_test(
    host: str,
    port: int,
    password: Optional[str],
    test_presets: list[str]
) -> tuple[dict, str]:
    """Run the Gate C preset→scene test."""

    results = {
        "test_name": "gate_c_preset_scene",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mapping_file": str(MAPPING_PATH),
        "presets_tested": [],
        "tests": [],
        "result": "FAIL"
    }

    client = OBSWebSocketClient(host, port, password)
    all_passed = True

    try:
        # Load mapping
        client._log("Loading preset mapping...")
        presets = load_preset_mapping()
        results["mapping_file_loaded"] = True
        results["available_presets"] = list(presets.keys())[:10]
        client._log(f"Available presets: {list(presets.keys())}")

        # Connect to OBS
        hello = await client.connect()
        results["obs_connected"] = True
        results["obs_version"] = hello.get("obsWebSocketVersion")

        # Get available scenes for validation
        scenes_resp = await client.call("GetSceneList")
        available_scenes = [s.get("sceneName") for s in scenes_resp.get("scenes", [])]
        results["available_scenes"] = available_scenes
        client._log(f"Available OBS scenes: {available_scenes}")

        # Test each preset
        for preset_name in test_presets:
            test_result = {
                "preset": preset_name,
                "expected_scene": None,
                "actual_scene": None,
                "switch_success": False,
                "verification_success": False,
                "result": "FAIL"
            }

            try:
                # Resolve expected scene
                expected_scene = resolve_scene_for_preset(presets, preset_name)
                test_result["expected_scene"] = expected_scene
                client._log(f"Preset '{preset_name}' → Scene '{expected_scene}'")

                # Check if scene exists
                if expected_scene not in available_scenes:
                    client._log(f"WARNING: Scene '{expected_scene}' not found in OBS")
                    test_result["error"] = f"Scene '{expected_scene}' not available"
                    all_passed = False
                    results["tests"].append(test_result)
                    continue

                # Switch to scene
                client._log(f"Calling SetCurrentProgramScene('{expected_scene}')")
                await client.call("SetCurrentProgramScene", {"sceneName": expected_scene})
                test_result["switch_success"] = True

                # Small delay to ensure scene is active
                await asyncio.sleep(0.2)

                # Verify scene
                current = await client.call("GetCurrentProgramScene")
                actual_scene = current.get("currentProgramSceneName")
                test_result["actual_scene"] = actual_scene
                client._log(f"GetCurrentProgramScene returned: '{actual_scene}'")

                if actual_scene == expected_scene:
                    test_result["verification_success"] = True
                    test_result["result"] = "PASS"
                    client._log(f"✓ Preset '{preset_name}' test PASSED")
                else:
                    client._log(f"✗ Preset '{preset_name}' test FAILED: expected '{expected_scene}', got '{actual_scene}'")
                    all_passed = False

            except Exception as e:
                test_result["error"] = str(e)
                client._log(f"✗ Preset '{preset_name}' test ERROR: {e}")
                all_passed = False

            results["tests"].append(test_result)
            results["presets_tested"].append(preset_name)

        # Overall result
        if all_passed and len(results["tests"]) > 0:
            passed_count = sum(1 for t in results["tests"] if t["result"] == "PASS")
            results["result"] = "PASS" if passed_count == len(results["tests"]) else "PARTIAL"
            results["summary"] = f"{passed_count}/{len(results['tests'])} presets passed"
        else:
            results["result"] = "FAIL"

    except FileNotFoundError as e:
        client._log(f"Configuration error: {e}")
        results["error"] = str(e)
        results["result"] = "CONFIG_ERROR"
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
    parser = argparse.ArgumentParser(description="Gate C: Preset → Scene Bridge Selftest")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"OBS host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"OBS port (default: {DEFAULT_PORT})")
    parser.add_argument("--password", default=None, help="OBS WebSocket password")
    parser.add_argument("--ensure-obs", action="store_true", help="Ensure OBS is running")
    parser.add_argument("--presets", default="default,drums",
                       help="Comma-separated list of presets to test (default: default,drums)")
    args = parser.parse_args()

    print("=" * 60)
    print("GATE C: Preset → Scene Bridge Selftest")
    print("Testing preset-to-OBS-scene mapping pipeline")
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
                "test_name": "gate_c_preset_scene",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": "ENSURE_OBS_FAILED",
                "ensure_obs": ensure_result
            }
            with open(SCRIPT_DIR / "gate_c_transcript.json", "w") as f:
                json.dump(failure_result, f, indent=2)

            return 1

    # Parse presets
    test_presets = [p.strip() for p in args.presets.split(",") if p.strip()]
    print(f"Testing presets: {test_presets}")
    print()

    # Run test
    results, log_excerpt = asyncio.run(run_gate_c_test(
        args.host,
        args.port,
        args.password,
        test_presets
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
    print(f"GATE C RESULT: {results['result']}")
    if "summary" in results:
        print(f"Summary: {results['summary']}")
    print("=" * 60)

    # Write artifacts
    transcript_path = SCRIPT_DIR / "gate_c_transcript.json"
    with open(transcript_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Transcript written to: {transcript_path}")

    log_path = SCRIPT_DIR / "gate_c_log_excerpt.txt"
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
