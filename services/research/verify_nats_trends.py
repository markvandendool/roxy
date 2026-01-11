#!/usr/bin/env python3
"""
Verify NATS publish for trend detector.
Subscribes to ghost.content.trends and waits for a message.
"""
import asyncio
import json
import nats

async def main():
    print("[NATS VERIFY] Connecting to NATS...")
    nc = await nats.connect("nats://localhost:4222")

    received = []

    async def handler(msg):
        data = json.loads(msg.data.decode())
        received.append(data)
        print(f"[NATS VERIFY] Received message:")
        print(f"  Snapshot: {data.get('snapshot_id')}")
        print(f"  Status: {data.get('status', 'unknown')}")
        print(f"  Degraded: {data.get('degraded', False)}")
        print(f"  Trends: {data.get('trend_count')}")
        top_trends = data.get('top_trends', [])
        if top_trends:
            print(f"  Top trend: {top_trends[0].get('title', 'N/A')[:60]}...")
        else:
            print(f"  Top trend: (none - degraded mode)")

    sub = await nc.subscribe("ghost.content.trends", cb=handler)

    print("[NATS VERIFY] Subscribed to ghost.content.trends")
    print("[NATS VERIFY] Run trend_detector.py in another terminal to verify...")
    print("[NATS VERIFY] Waiting 10 seconds for messages...")

    await asyncio.sleep(10)
    await sub.unsubscribe()
    await nc.close()

    if received:
        print(f"\n[NATS VERIFY] SUCCESS: Received {len(received)} message(s)")
        return True
    else:
        print("\n[NATS VERIFY] No messages received (run trend_detector.py)")
        return False

if __name__ == "__main__":
    asyncio.run(main())
