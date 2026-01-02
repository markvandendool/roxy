#!/usr/bin/env python3
"""
ROXY API Gateway - Unified API for all ROXY functions
"""
import logging
from fastapi import FastAPI, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.api')

app = FastAPI(title="ROXY API Gateway", version="1.0.0")

class ChatRequest(BaseModel):
    message: str
    context: Dict = {}

class TaskRequest(BaseModel):
    task_type: str
    parameters: Dict = {}

@app.post("/api/chat")
async def chat(request: ChatRequest) -> Dict:
    """Chat with ROXY"""
    try:
        from roxy_core import RoxyCore
        roxy = RoxyCore()
        response = await roxy.process_interaction(request.message, request.context)
        return {'response': response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/task")
async def execute_task(request: TaskRequest) -> Dict:
    """Execute a task"""
    try:
        # Would route to appropriate service
        return {'status': 'task_received', 'task_type': request.task_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status() -> Dict:
    """Get ROXY status"""
    try:
        from roxy_core import RoxyCore
        roxy = RoxyCore()
        return roxy.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)










