#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


GITNEXUS_URL = os.getenv("ROXY_GITNEXUS_URL", "http://127.0.0.1:4747").rstrip("/")
GITNEXUS_CLI = os.getenv("ROXY_GITNEXUS_CLI", str(Path.home() / ".local" / "bin" / "gitnexus"))
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
HEARTBEAT_SECONDS = float(os.getenv("ROXY_GITNEXUS_ANALYZE_HEARTBEAT_SECONDS", "10"))


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


def _run_cli(command: list[str], *, state: str, job_id: str, phase: str) -> tuple[int, str]:
    env = os.environ.copy()
    env["PATH"] = f"{Path.home() / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    env.setdefault("NODE_OPTIONS", "--max-old-space-size=12288")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    last_line = ""
    try:
        assert process.stdout is not None
        stdout_fd = process.stdout.fileno()
        while True:
            ready, _, _ = select.select([stdout_fd], [], [], HEARTBEAT_SECONDS)
            if ready:
                raw_line = process.stdout.readline()
                if raw_line == "":
                    if process.poll() is not None:
                        break
                    continue
                line = raw_line.strip()
                if not line:
                    continue
                last_line = line
                print(f"[gitnexus-analyze] {line}", flush=True)
                _write_status(
                    _status_payload(
                        state=state,
                        job_id=job_id,
                        progress={"phase": phase, "message": line},
                    )
                )
                continue
            if process.poll() is not None:
                break
            heartbeat_message = last_line or f"{phase} running"
            _write_status(
                _status_payload(
                    state=state,
                    job_id=job_id,
                    progress={
                        "phase": phase,
                        "message": heartbeat_message,
                        "heartbeat": True,
                    },
                )
            )
    finally:
        return_code = process.wait()
    return return_code, last_line


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
        "indexed_source_head": source_meta.get("source_head") if state == "complete" else None,
        "mode": source_meta.get("mode"),
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

    job_id = f"cli-{int(time.time())}"
    _write_status(_status_payload(state="starting", job_id=job_id))

    analyze_cmd = [
        GITNEXUS_CLI,
        "analyze",
        "--force",
        "--skip-git",
        "--skip-agents-md",
        "--no-stats",
        str(MIRROR_ROOT),
    ]
    print(f"[gitnexus-analyze] starting CLI analyze for {MIRROR_ROOT}", flush=True)
    _write_status(
        _status_payload(
            state="indexing",
            job_id=job_id,
            progress={"phase": "cli_analyze", "message": "Starting CLI analyze"},
        )
    )
    analyze_rc, analyze_tail = _run_cli(analyze_cmd, state="indexing", job_id=job_id, phase="cli_analyze")
    if analyze_rc != 0:
        error = f"gitnexus analyze exited {analyze_rc}: {analyze_tail}".strip()
        _write_status(_status_payload(state="failed", job_id=job_id, error=error))
        print(f"[gitnexus-analyze] failed: {error}", file=sys.stderr, flush=True)
        return 1

    index_cmd = [GITNEXUS_CLI, "index", "--allow-non-git", str(MIRROR_ROOT)]
    _write_status(
        _status_payload(
            state="indexing",
            job_id=job_id,
            progress={"phase": "cli_index", "message": "Registering GitNexus repo"},
        )
    )
    index_rc, index_tail = _run_cli(index_cmd, state="indexing", job_id=job_id, phase="cli_index")
    if index_rc != 0:
        error = f"gitnexus index exited {index_rc}: {index_tail}".strip()
        _write_status(_status_payload(state="failed", job_id=job_id, error=error))
        print(f"[gitnexus-analyze] failed: {error}", file=sys.stderr, flush=True)
        return 1

    _write_status(
        _status_payload(
            state="reloading",
            job_id=job_id,
            progress={"phase": "service_reload", "message": "Restarting gitnexus.service"},
        )
    )
    subprocess.run(["systemctl", "--user", "restart", "gitnexus.service"], check=True)
    time.sleep(max(POLL_SECONDS, 2))

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
            progress={"phase": "done", "percent": 100, "message": "Done"},
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
