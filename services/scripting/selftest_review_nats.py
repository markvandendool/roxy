#!/usr/bin/env python3
"""
SKYBEAM Selftest: Script Reviewer NATS Integration
===================================================

Deterministic test that:
1. Spawns subscriber task
2. Runs the publisher function
3. Asserts received message count == 1
4. Exits 0 (PASS) or 1 (FAIL)

Usage: python3 selftest_review_nats.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

import nats
from script_reviewer import (
    generate_review, publish_to_nats, validate_schema, write_review,
    load_json_file, SCRIPTS_FILE
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.script.reviewed"


async def run_selftest():
    """Run the deterministic selftest."""
    print("=" * 60)
    print("  SELFTEST: Script Reviewer NATS Integration")
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
        print(f"  Received: {data.get('review_id')}")

    # Subscribe
    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)  # Let subscription settle

    # Load scripts
    print("[3] Loading scripts...")
    scripts_data, _ = load_json_file(SCRIPTS_FILE)
    if scripts_data:
        print(f"  Scripts: {scripts_data.get('script_id')}")

    # Generate review
    print("[4] Generating review...")
    review = generate_review(scripts_data, test_degraded=False)

    valid, error = validate_schema(review)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing review...")
    write_review(review)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(review)
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
        summary = msg.get("summary", {})
        print(f"  Review ID: {msg.get('review_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Reviewed: {summary.get('total_reviewed')}")
        print(f"  Approved: {summary.get('approved')}")
        print(f"  Avg Score: {summary.get('average_score')}")
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
