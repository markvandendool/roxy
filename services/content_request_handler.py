#!/usr/bin/env python3
"""
SKYBEAM Content Request Handler

FastAPI webhook that receives content requests from iPhone Shortcuts,
validates input, generates job_id, publishes to NATS, and returns confirmation.

Endpoint: POST /api/content/request

Usage:
  uvicorn content_request_handler:app --host 0.0.0.0 --port 8780

  # Or with systemd:
  systemctl start roxy-content-handler
"""

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

try:
    from fastapi import FastAPI, HTTPException, Depends, Header
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print("ERROR: FastAPI not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import nats
except ImportError:
    print("ERROR: nats-py not installed. Run: pip install nats-py")
    sys.exit(1)


# Configuration
NATS_URL = os.getenv("NATS_URL", "nats://127.0.0.1:4222")
CONTENT_TOKEN = os.getenv("ROXY_CONTENT_TOKEN", None)
TOKEN_FILE = os.path.expanduser("~/.roxy/secret.token")
JOBS_DIR = os.path.expanduser("~/.roxy/content-pipeline/jobs")

# Load token from file if not in env
if not CONTENT_TOKEN and os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as f:
        CONTENT_TOKEN = f.read().strip()


class ContentStyle(str, Enum):
    """Content style presets."""
    educational = "educational"
    entertainment = "entertainment"
    tutorial = "tutorial"
    review = "review"
    news = "news"
    storytelling = "storytelling"
    documentary = "documentary"
    anime = "anime"
    vlog = "vlog"
    shorts = "shorts"


class ContentPriority(str, Enum):
    """Content priority levels."""
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class Platform(str, Enum):
    """Target publishing platforms."""
    youtube = "youtube"
    youtube_shorts = "youtube_shorts"
    tiktok = "tiktok"
    instagram = "instagram"
    twitter = "twitter"
    linkedin = "linkedin"
    all = "all"


class ContentRequest(BaseModel):
    """Content request from iPhone Shortcuts or API."""
    topic: str = Field(..., min_length=3, max_length=500, description="Content topic/idea")
    style: ContentStyle = Field(default=ContentStyle.educational, description="Content style preset")
    priority: ContentPriority = Field(default=ContentPriority.normal, description="Processing priority")
    platforms: list[Platform] = Field(default=[Platform.youtube], description="Target platforms")
    duration_hint: Optional[str] = Field(default=None, description="Target duration (e.g., '10min', '60sec')")
    language: str = Field(default="en", description="Content language code")
    voice_style: Optional[str] = Field(default=None, description="Voice style override")
    research_depth: str = Field(default="standard", description="Research depth: quick, standard, deep")
    notes: Optional[str] = Field(default=None, description="Additional notes/instructions")


class ContentRequestResponse(BaseModel):
    """Response after accepting content request."""
    success: bool
    job_id: str
    topic: str
    status: str
    message: str
    estimated_stages: list[str]
    nats_topic: str


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    stage: str
    progress: int
    created_at: str
    updated_at: str


# Global NATS connection
nc = None


def generate_job_id(topic: str) -> str:
    """Generate unique job ID: JOB_YYYYMMDD_HHMMSS_HASH."""
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # Create hash from topic + timestamp + random
    hash_input = f"{topic}_{now.isoformat()}_{os.urandom(8).hex()}"
    hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    return f"JOB_{timestamp}_{hash_suffix}"


async def verify_token(authorization: str = Header(None)) -> str:
    """Verify Bearer token authentication."""
    if not CONTENT_TOKEN:
        # No token configured, allow all (dev mode)
        return "dev-mode"

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")

    token = authorization[7:]
    if token != CONTENT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    return token


async def get_nats():
    """Get or create NATS connection."""
    global nc
    if nc is None or not nc.is_connected:
        nc = await nats.connect(NATS_URL)
    return nc


async def publish_content_request(job_id: str, request: ContentRequest):
    """Publish content request to NATS."""
    try:
        client = await get_nats()

        payload = {
            "job_id": job_id,
            "topic": request.topic,
            "style": request.style.value,
            "priority": request.priority.value,
            "platforms": [p.value for p in request.platforms],
            "duration_hint": request.duration_hint,
            "language": request.language,
            "voice_style": request.voice_style,
            "research_depth": request.research_depth,
            "notes": request.notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "queued"
        }

        await client.publish(
            "ghost.content.request",
            json.dumps(payload).encode()
        )

        return True
    except Exception as e:
        print(f"NATS publish error: {e}")
        return False


def create_job_directory(job_id: str, request: ContentRequest) -> str:
    """Create job directory with initial manifest."""
    job_dir = os.path.join(JOBS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Create subdirectories
    for subdir in ["source", "transcript", "research", "script", "assets", "clips", "publish"]:
        os.makedirs(os.path.join(job_dir, subdir), exist_ok=True)

    # Create initial manifest
    manifest = {
        "job_id": job_id,
        "topic": request.topic,
        "style": request.style.value,
        "priority": request.priority.value,
        "platforms": [p.value for p in request.platforms],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
        "current_stage": "pending",
        "stages": {
            "research": {"status": "pending", "started_at": None, "completed_at": None},
            "script": {"status": "pending", "started_at": None, "completed_at": None},
            "assets": {"status": "pending", "started_at": None, "completed_at": None},
            "production": {"status": "pending", "started_at": None, "completed_at": None},
            "variants": {"status": "pending", "started_at": None, "completed_at": None},
            "publish": {"status": "pending", "started_at": None, "completed_at": None}
        }
    }

    manifest_path = os.path.join(job_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return job_dir


# Create FastAPI app
app = FastAPI(
    title="SKYBEAM Content Request Handler",
    description="Webhook handler for ROXY content pipeline requests",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    nats_status = "connected"
    try:
        client = await get_nats()
        if not client.is_connected:
            nats_status = "disconnected"
    except Exception:
        nats_status = "error"

    return {
        "status": "healthy",
        "service": "content-request-handler",
        "nats": nats_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/content/request", response_model=ContentRequestResponse)
async def create_content_request(
    request: ContentRequest,
    token: str = Depends(verify_token)
):
    """
    Create a new content request.

    Receives topic and preferences from iPhone Shortcuts or API,
    generates job_id, creates job directory, publishes to NATS,
    and returns confirmation.
    """
    # Generate unique job ID
    job_id = generate_job_id(request.topic)

    # Create job directory and manifest
    try:
        job_dir = create_job_directory(job_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job directory: {e}")

    # Publish to NATS
    nats_success = await publish_content_request(job_id, request)
    if not nats_success:
        # Still continue - job is created, NATS can be retried
        print(f"Warning: NATS publish failed for {job_id}")

    # Define expected stages
    stages = [
        "research",
        "script",
        "assets",
        "production",
        "variants",
        "publish"
    ]

    return ContentRequestResponse(
        success=True,
        job_id=job_id,
        topic=request.topic,
        status="queued",
        message=f"Content request queued successfully. Job ID: {job_id}",
        estimated_stages=stages,
        nats_topic="ghost.content.request"
    )


@app.get("/api/content/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, token: str = Depends(verify_token)):
    """Get status of a content job."""
    job_dir = os.path.join(JOBS_DIR, job_id)
    manifest_path = os.path.join(job_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Calculate progress
    stages = manifest.get("stages", {})
    completed = sum(1 for s in stages.values() if s.get("status") == "completed")
    total = len(stages)
    progress = int((completed / total) * 100) if total > 0 else 0

    return JobStatus(
        job_id=job_id,
        status=manifest.get("status", "unknown"),
        stage=manifest.get("current_stage", "unknown"),
        progress=progress,
        created_at=manifest.get("created_at", ""),
        updated_at=manifest.get("updated_at", "")
    )


@app.get("/api/content/jobs")
async def list_jobs(token: str = Depends(verify_token), limit: int = 20):
    """List recent content jobs."""
    if not os.path.exists(JOBS_DIR):
        return {"jobs": []}

    jobs = []
    for job_id in sorted(os.listdir(JOBS_DIR), reverse=True)[:limit]:
        manifest_path = os.path.join(JOBS_DIR, job_id, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                jobs.append({
                    "job_id": job_id,
                    "topic": manifest.get("topic", ""),
                    "status": manifest.get("status", "unknown"),
                    "created_at": manifest.get("created_at", "")
                })
            except Exception:
                pass

    return {"jobs": jobs, "count": len(jobs)}


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    global nc
    if nc and nc.is_connected:
        await nc.close()


if __name__ == "__main__":
    # Ensure jobs directory exists
    os.makedirs(JOBS_DIR, exist_ok=True)

    print("Starting SKYBEAM Content Request Handler...")
    print(f"NATS URL: {NATS_URL}")
    print(f"Jobs Directory: {JOBS_DIR}")
    print(f"Token configured: {bool(CONTENT_TOKEN)}")

    uvicorn.run(app, host="0.0.0.0", port=8780)
