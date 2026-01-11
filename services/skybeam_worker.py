#!/usr/bin/env python3
"""
SKYBEAM Worker — subscribes to ghost.content.request and renders P0 master.mp4

Requires: nats-py in ~/.roxy/venv
"""

from __future__ import annotations
import asyncio
import json
import os
from typing import Any, Dict

from nats.aio.client import Client as NATS

from skybeam_p0_renderer import render_job

NATS_URL = os.getenv("NATS_URL", "nats://127.0.0.1:4222")
SUBJECT = "ghost.content.request"

async def main():
    nc = NATS()
    await nc.connect(servers=[NATS_URL])

    async def handler(msg):
        try:
            payload: Dict[str, Any] = json.loads(msg.data.decode())
            job_id = payload.get("job_id") or payload.get("id")
            if not job_id:
                print("SKIP: message missing job_id")
                return
            print(f"RENDER: {job_id}")
            master = render_job(job_id)
            print(f"DONE: {job_id} -> {master}")
        except Exception as e:
            print(f"ERROR: {e}")

    await nc.subscribe(SUBJECT, cb=handler)
    print(f"SKYBEAM worker listening on {SUBJECT} @ {NATS_URL}")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
