#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GITNEXUS_URL = os.getenv("ROXY_GITNEXUS_URL", "http://127.0.0.1:4747").rstrip("/")
CANONICAL_ROOT = Path(
    os.getenv(
        "ROXY_MINDSONG_CANONICAL_ROOT",
        str(Path.home() / "mindsong-juke-hub"),
    )
).expanduser()
MIRROR_ROOT = Path(
    os.getenv(
        "ROXY_GITNEXUS_MINDSONG_INDEX_PATH",
        str(Path.home() / "work" / "gitnexus-mirrors" / "mindsong-juke-hub"),
    )
).expanduser()
STATUS_PATH = Path(
    os.getenv(
        "ROXY_GITNEXUS_STATUS_PATH",
        str(Path.home() / ".roxy" / "run" / "gitnexus" / "mindsong_status.json"),
    )
).expanduser()
POLL_SECONDS = float(os.getenv("ROXY_GITNEXUS_ANALYZE_POLL_SECONDS", "5"))
MAX_WAIT_SECONDS = float(os.getenv("ROXY_GITNEXUS_ANALYZE_MAX_WAIT_SECONDS", "14400"))


def _request_json(url: str, payload: dict | None = None, method: str = "GET") -> dict:
    data = None
    headers = {"User-Agent": "roxy-gitnexus-analyze/1"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    with urlopen(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else {}


def _status_line(payload: dict) -> str:
    progress = payload.get("progress") or {}
    phase = progress.get("phase") or payload.get("status") or "unknown"
    percent = progress.get("percent")
    message = progress.get("message") or ""
    if percent is None:
        return f"{phase}: {message}".strip()
    return f"{phase} {percent}%: {message}".strip()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_source_metadata() -> dict:
    source_path = MIRROR_ROOT / ".gitnexus-source.json"
    if not source_path.exists():
        return {}
    try:
        return json.loads(source_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_git_head(repo_root: Path) -> str | None:
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return None
    try:
        import subprocess

        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        head = (completed.stdout or "").strip()
        return head or None
    except Exception:
        return None


def _write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=str(STATUS_PATH.parent), delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(STATUS_PATH)


def _status_payload(
    *,
    state: str,
    job_id: str | None = None,
    progress: dict | None = None,
    error: str | None = None,
    registered: bool | None = None,
    repo_name: str | None = None,
) -> dict:
    source_meta = _read_source_metadata()
    return {
        "state": state,
        "job_id": job_id,
        "canonical_root": str(CANONICAL_ROOT),
        "mirror_root": str(MIRROR_ROOT),
        "canonical_head": _safe_git_head(CANONICAL_ROOT),
        "mirror_head": _safe_git_head(MIRROR_ROOT),
        "source_head": source_meta.get("source_head"),
        "synced_at": source_meta.get("synced_at"),
        "progress": progress or {},
        "registered": registered,
        "repo_name": repo_name,
        "error": error,
        "updated_at": _utc_now(),
    }


def main() -> int:
    if not MIRROR_ROOT.is_dir():
        print(f"[gitnexus-analyze] mirror root missing: {MIRROR_ROOT}", file=sys.stderr)
        return 1

    _write_status(_status_payload(state="starting"))

    job = _request_json(
        f"{GITNEXUS_URL}/api/analyze",
        payload={"path": str(MIRROR_ROOT), "force": True},
        method="POST",
    )
    job_id = job.get("jobId")
    if not job_id:
        print(f"[gitnexus-analyze] missing job id: {job}", file=sys.stderr)
        _write_status(
            _status_payload(
                state="failed",
                error=f"missing job id: {job}",
            )
        )
        return 1

    _write_status(_status_payload(state="submitted", job_id=job_id))
    print(f"[gitnexus-analyze] started job {job_id} for {MIRROR_ROOT}", flush=True)
    last_line = ""
    deadline = time.time() + MAX_WAIT_SECONDS

    while time.time() < deadline:
        payload = _request_json(f"{GITNEXUS_URL}/api/analyze/{job_id}")
        status = str(payload.get("status") or "").lower()
        line = _status_line(payload)
        _write_status(
            _status_payload(
                state="indexing" if status not in {"complete", "failed"} else status,
                job_id=job_id,
                progress=payload.get("progress") or {},
            )
        )
        if line and line != last_line:
            print(f"[gitnexus-analyze] {line}", flush=True)
            last_line = line

        if status == "complete":
            repos = _request_json(f"{GITNEXUS_URL}/api/repos")
            matched = next(
                (
                    entry
                    for entry in repos
                    if isinstance(entry, dict)
                    and str(entry.get("path") or "") == str(MIRROR_ROOT)
                ),
                None,
            )
            _write_status(
                _status_payload(
                    state="complete",
                    job_id=job_id,
                    progress=payload.get("progress") or {},
                    registered=bool(matched),
                    repo_name=matched.get("name") if matched else None,
                )
            )
            print(
                "[gitnexus-analyze] complete",
                json.dumps(
                    {
                        "job_id": job_id,
                        "mirror_root": str(MIRROR_ROOT),
                        "registered": bool(matched),
                        "repo_name": matched.get("name") if matched else None,
                    }
                ),
                flush=True,
            )
            return 0
        if status == "failed":
            error = str(payload.get("error") or payload)
            _write_status(
                _status_payload(
                    state="failed",
                    job_id=job_id,
                    progress=payload.get("progress") or {},
                    error=error,
                )
            )
            print(f"[gitnexus-analyze] failed: {error}", file=sys.stderr, flush=True)
            return 1

        time.sleep(POLL_SECONDS)

    _write_status(
        _status_payload(
            state="failed",
            job_id=job_id,
            error=f"timed out waiting for {job_id}",
        )
    )
    print(f"[gitnexus-analyze] timed out waiting for {job_id}", file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        _write_status(
            _status_payload(
                state="failed",
                error=f"transport error: {exc}",
            )
        )
        print(f"[gitnexus-analyze] transport error: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
