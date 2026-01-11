#!/usr/bin/env python3
"""
SKYBEAM Selftest: Script Generator NATS Integration
====================================================

Deterministic test that:
1. Spawns subscriber task
2. Runs the publisher function
3. Asserts received message count == 1
4. Exits 0 (PASS) or 1 (FAIL)

Usage: python3 selftest_scripts_nats.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

import nats
from script_generator import (
    generate_scripts, publish_to_nats, validate_schema, write_scripts,
    load_json_file, BUNDLE_FILE, TEMPLATES_FILE
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.script.generated"


async def run_selftest():
    """Run the deterministic selftest."""
    print("=" * 60)
    print("  SELFTEST: Script Generator NATS Integration")
    print("=" * 60)

    received_messages = []

    # Connect to NATS
    print("\n[1] Connecting to NATS...")
    try:
        nc = await nats.connect(NATS_URL)
    except Exception as e:
        print(f"  FAIL: Cannot connect to NATS: {e}")
        return False

    # Define handler
    async def handler(msg):
        data = json.loads(msg.data.decode())
        received_messages.append(data)
        print(f"  Received: {data.get('script_id')}")

    # Subscribe
    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)  # Let subscription settle

    # Load inputs
    print("[3] Loading inputs...")
    bundle, _ = load_json_file(BUNDLE_FILE)
    templates_data, _ = load_json_file(TEMPLATES_FILE)

    if bundle:
        print(f"  Bundle: {bundle.get('bundle_id')}")
    if templates_data:
        print(f"  Templates: {templates_data.get('library_id')}")

    # Generate scripts
    print("[4] Generating scripts...")
    scripts = generate_scripts(bundle, templates_data, top_n=3, test_degraded=False)

    valid, error = validate_schema(scripts)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing scripts...")
    write_scripts(scripts)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(scripts)
    if not pub_ok:
        print("  FAIL: Publish failed")
        await sub.unsubscribe()
        await nc.close()
        return False

    # Wait for message to arrive
    print("[7] Waiting for message...")
    await asyncio.sleep(1.0)

    # Cleanup
    await sub.unsubscribe()
    await nc.close()

    # Assert
    print(f"\n[8] Assertion: received_count == 1")
    print(f"  Received: {len(received_messages)} message(s)")

    if len(received_messages) == 1:
        msg = received_messages[0]
        print(f"  Script ID: {msg.get('script_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Scripts: {msg.get('meta', {}).get('script_count')}")
        print("\n" + "=" * 60)
        print("  RESULT: PASS")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("  RESULT: FAIL")
        print("=" * 60)
        return False


def main():
    success = asyncio.run(run_selftest())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
