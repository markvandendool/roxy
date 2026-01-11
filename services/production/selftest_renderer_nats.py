#!/usr/bin/env python3
"""
SKYBEAM Selftest: Renderer Runner NATS Integration
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import nats
from renderer_runner import (
    generate_render_result, publish_to_nats, validate_schema, write_result,
    load_json_file, REQUESTS_FILE, acquire_lock, release_lock
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.prod.render_result"


async def run_selftest():
    print("=" * 60)
    print("  SELFTEST: Renderer Runner NATS Integration")
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
        print(f"  Received: {data.get('result_id')}")

    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)

    print("[3] Acquiring lock...")
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("  SKIP: Lock held")
        await sub.unsubscribe()
        await nc.close()
        return True

    try:
        print("[4] Loading requests...")
        requests_data, _ = load_json_file(REQUESTS_FILE)
        if requests_data:
            print(f"  Request: {requests_data.get('request_id')}")

        print("[5] Generating render result...")
        result = generate_render_result(requests_data, test_degraded=False)

        valid, error = validate_schema(result)
        if not valid:
            print(f"  FAIL: Schema validation failed: {error}")
            release_lock(lock_fd)
            await sub.unsubscribe()
            await nc.close()
            return False
        print(f"  Schema: VALID")

        print("[6] Writing result...")
        write_result(result)

        print("[7] Publishing to NATS...")
        pub_ok = await publish_to_nats(result)
        if not pub_ok:
            print("  FAIL: Publish failed")
            release_lock(lock_fd)
            await sub.unsubscribe()
            await nc.close()
            return False

        print("[8] Waiting for message...")
        await asyncio.sleep(1.0)

    finally:
        release_lock(lock_fd)

    await sub.unsubscribe()
    await nc.close()

    print(f"\n[9] Assertion: received_count == 1")
    print(f"  Received: {len(received_messages)} message(s)")

    if len(received_messages) == 1:
        msg = received_messages[0]
        print(f"  Result ID: {msg.get('result_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Renders: {msg.get('meta', {}).get('render_count')}")
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
