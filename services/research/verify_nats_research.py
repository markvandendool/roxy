#!/usr/bin/env python3
"""
Verify NATS publish for deep research agent.
Subscribes to ghost.content.research and waits for a message.
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
        print(f"  Brief: {data.get('brief_id')}")
        print(f"  Status: {data.get('status', 'unknown')}")
        print(f"  Degraded: {data.get('degraded', False)}")
        print(f"  Briefs: {data.get('brief_count')}")
        print(f"  Source: {data.get('source_snapshot')}")

    sub = await nc.subscribe("ghost.content.research", cb=handler)

    print("[NATS VERIFY] Subscribed to ghost.content.research")
    print("[NATS VERIFY] Run deep_research_agent.py in another terminal to verify...")
    print("[NATS VERIFY] Waiting 10 seconds for messages...")

    await asyncio.sleep(10)
    await sub.unsubscribe()
    await nc.close()

    if received:
        print(f"\n[NATS VERIFY] SUCCESS: Received {len(received)} message(s)")
        return True
    else:
        print("\n[NATS VERIFY] No messages received")
        return False

if __name__ == "__main__":
    asyncio.run(main())
