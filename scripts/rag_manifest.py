#!/usr/bin/env python3
"""
Generate a deterministic RAG manifest for a repo.
Includes file counts/bytes, index stats, and config fingerprint.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path.home() / ".roxy"
sys.path.insert(0, str(ROOT / "services"))

try:
    from repository_indexer import get_repo_indexer
except Exception as exc:
    print(f"Failed to import repository_indexer: {exc}")
    sys.exit(1)

SCRIPT_VERSION = "1.0.0"


def git_info(repo_path: str) -> dict:
    info = {"commit": None, "branch": None, "dirty": None, "remote": None}
    try:
        info["commit"] = subprocess.check_output(
            ["git", "-C", repo_path, "rev-parse", "HEAD"], text=True
        ).strip()
        info["branch"] = subprocess.check_output(
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", repo_path, "status", "--porcelain"], text=True
        ).strip()
        info["dirty"] = bool(status)
        try:
            info["remote"] = subprocess.check_output(
                ["git", "-C", repo_path, "config", "--get", "remote.origin.url"], text=True
            ).strip() or None
        except Exception:
            info["remote"] = None
    except Exception:
        pass
    return info


def compute_repo_manifest(repo_path: str, collection: str | None) -> dict:
    indexer = get_repo_indexer(repo_path, collection)

    total_files = 0
    total_bytes = 0
    ext_counts: dict[str, int] = {}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in indexer.skip_dirs]
        for name in files:
            file_path = Path(root) / name
            if indexer._should_index_file(file_path):
                total_files += 1
                try:
                    size = file_path.stat().st_size
                    total_bytes += size
                except OSError:
                    size = 0
                ext = file_path.suffix.lower() or "<none>"
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

    # Sort extension counts by frequency
    ext_counts_sorted = dict(sorted(ext_counts.items(), key=lambda kv: kv[1], reverse=True))

    stats = indexer.get_stats()

    return {
        "repo_path": repo_path,
        "collection": collection,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": {
            "name": "rag_manifest.py",
            "version": SCRIPT_VERSION,
        },
        "repo": git_info(repo_path),
        "index": {
            "stats": stats,
            "skip_dirs": list(getattr(indexer, "skip_dirs", [])),
            "skip_exts": list(getattr(indexer, "skip_exts", [])),
            "max_file_size": getattr(indexer, "max_file_size", None),
        },
        "filesystem": {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "ext_counts": ext_counts_sorted,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getenv("ROXY_RAG_REPO", str(Path.home() / "mindsong-juke-hub")))
    parser.add_argument("--collection", default=None)
    parser.add_argument("--out", default=str(ROOT / "artifacts"))
    args = parser.parse_args()

    repo_path = args.repo
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = compute_repo_manifest(repo_path, args.collection)

    # Compute manifest hash without the hash itself
    payload = json.dumps(manifest, sort_keys=True, indent=2)
    manifest_hash = sha256(payload.encode("utf-8")).hexdigest()
    manifest["manifest_sha256"] = manifest_hash

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"rag-manifest-{ts}.json"
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(out_path)


if __name__ == "__main__":
    main()
