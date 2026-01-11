#!/usr/bin/env python3
"""
SKYBEAM Selftest: Render Request Builder NATS Integration
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import nats
from render_request_builder import (
    generate_render_requests, publish_to_nats, validate_schema, write_requests,
    load_json_file, REVIEWED_FILE, STORYBOARDS_FILE, QA_FILE
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.prod.render_request"


async def run_selftest():
    print("=" * 60)
    print("  SELFTEST: Render Request Builder NATS Integration")
    print("=" * 60)

    received_messages = []

    print("\n[1] Connecting to NATS...")
    try:
        nc = await nats.connect(NATS_URL)
    except Exception as e:
        print(f"  FAIL: Cannot connect to NATS: {e}")
        return False

    async def handler(msg):
        data = json.loads(msg.data.decode())
        received_messages.append(data)
        print(f"  Received: {data.get('request_id')}")

    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)

    print("[3] Loading inputs...")
    reviewed_data, _ = load_json_file(REVIEWED_FILE)
    storyboards_data, _ = load_json_file(STORYBOARDS_FILE)
    qa_data, _ = load_json_file(QA_FILE)
    if reviewed_data:
        print(f"  Review: {reviewed_data.get('review_id')}")

    print("[4] Generating requests...")
    requests = generate_render_requests(reviewed_data, storyboards_data, qa_data, test_degraded=False)

    valid, error = validate_schema(requests)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing requests...")
    write_requests(requests)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(requests)
    if not pub_ok:
        print("  FAIL: Publish failed")
        await sub.unsubscribe()
        await nc.close()
        return False

    print("[7] Waiting for message...")
    await asyncio.sleep(1.0)

    await sub.unsubscribe()
    await nc.close()

    print(f"\n[8] Assertion: received_count == 1")
    print(f"  Received: {len(received_messages)} message(s)")

    if len(received_messages) == 1:
        msg = received_messages[0]
        print(f"  Request ID: {msg.get('request_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Requests: {msg.get('meta', {}).get('request_count')}")
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
