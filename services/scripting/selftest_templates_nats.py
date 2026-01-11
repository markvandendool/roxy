#!/usr/bin/env python3
"""
SKYBEAM Selftest: Template Library NATS Integration
====================================================

Deterministic test that:
1. Spawns subscriber task
2. Runs the publisher function
3. Asserts received message count == 1
4. Exits 0 (PASS) or 1 (FAIL)

Usage: python3 selftest_templates_nats.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

import nats
from template_library import (
    generate_library, publish_to_nats, validate_schema, write_library,
    load_templates, TEMPLATES_FILE
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.script.templates"


async def run_selftest():
    """Run the deterministic selftest."""
    print("=" * 60)
    print("  SELFTEST: Template Library NATS Integration")
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
        print(f"  Received: {data.get('library_id')}")

    # Subscribe
    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)  # Let subscription settle

    # Load templates
    print("[3] Loading templates...")
    templates, error = load_templates(TEMPLATES_FILE)
    if error:
        print(f"  Warning: {error}")
        templates = []
    else:
        print(f"  Loaded: {len(templates)} templates")

    # Generate library
    print("[4] Generating library...")
    library = generate_library(templates, test_degraded=False)

    valid, error = validate_schema(library)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing library...")
    write_library(library)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(library)
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
        print(f"  Library: {msg.get('library_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Templates: {msg.get('meta', {}).get('template_count')}")
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
