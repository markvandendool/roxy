#!/usr/bin/env python3
"""NATS Job Publisher - Send inference jobs to Friday worker"""
import asyncio
import json
import nats

NATS_URL = 'nats://localhost:4222'
FRIDAY_QUEUE = 'citadel.inference.light'

async def publish_job(prompt: str, model: str = 'tinyllama'):
    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()
    
    job = {
        'prompt': prompt,
        'model': model,
        'priority': 'normal'
    }
    
    ack = await js.publish(FRIDAY_QUEUE, json.dumps(job).encode())
    print(f'Published job to {FRIDAY_QUEUE}: {ack.seq}')
    await nc.close()

if __name__ == '__main__':
    asyncio.run(publish_job('Hello, test job'))
    print('Job sent to Friday queue')
