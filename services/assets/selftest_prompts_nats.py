#!/usr/bin/env python3
"""
SKYBEAM Selftest: Prompt Pack Generator NATS Integration
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import nats
from prompt_pack_generator import (
    generate_packs, publish_to_nats, validate_schema, write_packs,
    load_json_file, BRIEFS_FILE
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.asset.prompts"


async def run_selftest():
    print("=" * 60)
    print("  SELFTEST: Prompt Pack Generator NATS Integration")
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
        print(f"  Received: {data.get('pack_id')}")

    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)

    print("[3] Loading briefs...")
    briefs_data, _ = load_json_file(BRIEFS_FILE)
    if briefs_data:
        print(f"  Briefs: {briefs_data.get('brief_id')}")

    print("[4] Generating packs...")
    packs = generate_packs(briefs_data, test_degraded=False)

    valid, error = validate_schema(packs)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing packs...")
    write_packs(packs)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(packs)
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
        print(f"  Pack ID: {msg.get('pack_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Packs: {msg.get('meta', {}).get('pack_count')}")
        print(f"  Prompts: {msg.get('meta', {}).get('prompt_count')}")
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
