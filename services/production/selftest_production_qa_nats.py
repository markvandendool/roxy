#!/usr/bin/env python3
"""
SKYBEAM Selftest: Production QA Gate NATS Integration
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import nats
from production_qa_gate import (
    generate_qa_report, publish_to_nats, validate_schema, write_qa_report,
    load_json_file, MASTER_JSON
)

NATS_URL = "nats://localhost:4222"
NATS_TOPIC = "ghost.prod.qa"


async def run_selftest():
    print("=" * 60)
    print("  SELFTEST: Production QA Gate NATS Integration")
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
        print(f"  Received: {data.get('qa_id')}")

    print("[2] Subscribing to topic...")
    sub = await nc.subscribe(NATS_TOPIC, cb=handler)
    await asyncio.sleep(0.5)

    print("[3] Loading master manifest...")
    master_data, _ = load_json_file(MASTER_JSON)
    if master_data:
        print(f"  Master: {master_data.get('master_id')}")

    print("[4] Generating QA report...")
    report = generate_qa_report(master_data, test_degraded=False)

    valid, error = validate_schema(report)
    if not valid:
        print(f"  FAIL: Schema validation failed: {error}")
        await sub.unsubscribe()
        await nc.close()
        return False
    print(f"  Schema: VALID")

    print("[5] Writing report...")
    write_qa_report(report)

    print("[6] Publishing to NATS...")
    pub_ok = await publish_to_nats(report)
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
        print(f"  QA ID: {msg.get('qa_id')}")
        print(f"  Status: {msg.get('status')}")
        print(f"  Gate: {msg.get('gate_result')}")
        print(f"  Checks: {msg.get('meta', {}).get('passed')}/{msg.get('meta', {}).get('check_count')} passed")
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
