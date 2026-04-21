#!/usr/bin/env bash
set -euo pipefail

CANONICAL_ROOT="${ROXY_MINDSONG_CANONICAL_ROOT:-$HOME/mindsong-juke-hub}"
MIRROR_ROOT="${ROXY_GITNEXUS_MINDSONG_INDEX_PATH:-$HOME/work/gitnexus-mirrors/mindsong-juke-hub}"
DEFAULT_BRANCH="${ROXY_GITNEXUS_DEFAULT_BRANCH:-main}"
DEFAULT_EXPORT_PATHS=".claude .github .kiro .skoreq api apps automation backend breakroom ci config deploy docs infra infrastructure luno-orchestrator ops packages patches plugins public recipes release_notes schemas scripts services shows sql src supabase test test-fixtures tests third_party tools validation-results wasm workshops"
EXPORT_PATHS_RAW="${ROXY_GITNEXUS_EXPORT_PATHS:-$DEFAULT_EXPORT_PATHS}"
DEFAULT_EXCLUDE_PREFIXES="public/releaseplan/archive/backups public/vgm/midi/extracted data/vgm-midi/extracted data/rocky-score-db/quick-access/folkrnn-tunes"
EXCLUDE_PREFIXES_RAW="${ROXY_GITNEXUS_EXCLUDE_PREFIXES:-$DEFAULT_EXCLUDE_PREFIXES}"
DEFAULT_TEXT_EXTENSIONS=".c .cc .conf .cpp .css .csv .cjs .dockerignore .editorconfig .env .eslintrc .gitattributes .gitignore .go .gql .graphql .h .hh .hpp .htm .html .ini .java .js .json .jsonl .jsx .kt .less .lua .m .md .mdx .mermaid .mjs .mm .mmd .nvmrc .php .plist .prettierignore .prettierrc .proto .ps1 .py .r .rb .rs .sass .scss .service .sh .socket .sql .svg .swift .timer .toml .ts .tsx .txt .xml .yaml .yml .zsh"
TEXT_EXTENSIONS_RAW="${ROXY_GITNEXUS_TEXT_EXTENSIONS:-$DEFAULT_TEXT_EXTENSIONS}"
DEFAULT_TEXT_FILENAMES="Dockerfile Gemfile Justfile LICENSE Makefile Procfile README Rakefile bunfig.toml compose.yaml compose.yml docker-compose.yaml docker-compose.yml go.mod go.sum package-lock.json package.json pnpm-lock.yaml pyproject.toml requirements.txt tsconfig.json vite.config.js vite.config.ts"
TEXT_FILENAMES_RAW="${ROXY_GITNEXUS_TEXT_FILENAMES:-$DEFAULT_TEXT_FILENAMES}"
MAX_FILE_BYTES="${ROXY_GITNEXUS_MAX_FILE_BYTES:-5242880}"
LOCK_ROOT="${XDG_RUNTIME_DIR:-/tmp}"
LOCK_FILE="$LOCK_ROOT/gitnexus-sync-mindsong.lock"

mkdir -p "$(dirname "$MIRROR_ROOT")"
exec 9>"$LOCK_FILE"
flock -n 9 || {
  echo "[gitnexus-sync] another sync is already running"
  exit 0
}

if [[ ! -d "$CANONICAL_ROOT/.git" ]]; then
  echo "[gitnexus-sync] canonical repo missing: $CANONICAL_ROOT" >&2
  exit 1
fi

export GIT_LFS_SKIP_SMUDGE=1

SOURCE_BRANCH="$(git -C "$CANONICAL_ROOT" branch --show-current 2>/dev/null || true)"
if [[ -z "$SOURCE_BRANCH" ]]; then
  SOURCE_BRANCH="$DEFAULT_BRANCH"
fi

SOURCE_HEAD="$(git -C "$CANONICAL_ROOT" rev-parse HEAD)"

rm -rf "$MIRROR_ROOT"
mkdir -p "$MIRROR_ROOT"

COPY_SUMMARY_PATH="$MIRROR_ROOT/.gitnexus-copy-summary.json"
MANIFEST_PATH="$(mktemp)"

cleanup_manifest() {
  rm -f "$MANIFEST_PATH"
}
trap cleanup_manifest EXIT

git -C "$CANONICAL_ROOT" ls-files -z > "$MANIFEST_PATH"

export CANONICAL_ROOT MIRROR_ROOT EXPORT_PATHS_RAW EXCLUDE_PREFIXES_RAW COPY_SUMMARY_PATH MANIFEST_PATH TEXT_EXTENSIONS_RAW TEXT_FILENAMES_RAW MAX_FILE_BYTES
python3 - <<'PY'
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


canonical_root = Path(os.environ["CANONICAL_ROOT"])
mirror_root = Path(os.environ["MIRROR_ROOT"])
copy_summary_path = Path(os.environ["COPY_SUMMARY_PATH"])
manifest_path = Path(os.environ["MANIFEST_PATH"])
allow_roots = {entry for entry in os.environ["EXPORT_PATHS_RAW"].split() if entry}
exclude_prefixes = tuple(
    prefix.rstrip("/") + "/"
    for prefix in os.environ["EXCLUDE_PREFIXES_RAW"].split()
    if prefix
)
text_extensions = {entry.lower() for entry in os.environ["TEXT_EXTENSIONS_RAW"].split() if entry}
text_filenames = {entry.lower() for entry in os.environ["TEXT_FILENAMES_RAW"].split() if entry}
max_file_bytes = int(os.environ["MAX_FILE_BYTES"])

summary = {
    "selected": 0,
    "copied": 0,
    "skipped_outside_scope": 0,
    "skipped_excluded": 0,
    "skipped_nontext": 0,
    "skipped_large": 0,
    "skipped_unreadable": 0,
    "skipped_errors": 0,
    "skipped_samples": [],
}


def include_path(repo_path: str) -> bool:
    if "/" not in repo_path:
        return True
    return repo_path.split("/", 1)[0] in allow_roots


def excluded_path(repo_path: str) -> bool:
    for prefix in exclude_prefixes:
        if repo_path == prefix[:-1] or repo_path.startswith(prefix):
            return True
    return False


def textual_path(repo_path: str) -> bool:
    name = Path(repo_path).name
    lower_name = name.lower()
    if lower_name in text_filenames:
        return True
    if lower_name.startswith(".") and lower_name.count(".") == 1:
        return lower_name in text_extensions or lower_name in text_filenames
    suffixes = Path(lower_name).suffixes
    return any(suffix in text_extensions for suffix in suffixes)


def note_skip(path: str, reason: str) -> None:
    if len(summary["skipped_samples"]) < 25:
        summary["skipped_samples"].append({"path": path, "reason": reason})


for raw_path in manifest_path.read_bytes().split(b"\0"):
    if not raw_path:
        continue
    repo_path = raw_path.decode("utf-8", errors="surrogateescape")
    if not include_path(repo_path):
        summary["skipped_outside_scope"] += 1
        continue
    if excluded_path(repo_path):
        summary["skipped_excluded"] += 1
        note_skip(repo_path, "excluded")
        continue
    if not textual_path(repo_path):
        summary["skipped_nontext"] += 1
        continue

    summary["selected"] += 1
    source_path = canonical_root / repo_path
    dest_path = mirror_root / repo_path
    try:
        if not source_path.exists() or not os.access(source_path, os.R_OK):
            summary["skipped_unreadable"] += 1
            note_skip(repo_path, "unreadable")
            continue
        if not source_path.is_symlink() and source_path.stat().st_size > max_file_bytes:
            summary["skipped_large"] += 1
            note_skip(repo_path, f"large>{max_file_bytes}")
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_symlink():
            target = os.readlink(source_path)
            if dest_path.exists() or dest_path.is_symlink():
                dest_path.unlink()
            os.symlink(target, dest_path)
        else:
            shutil.copy2(source_path, dest_path, follow_symlinks=False)
        summary["copied"] += 1
    except OSError as exc:
        summary["skipped_errors"] += 1
        note_skip(repo_path, f"{type(exc).__name__}: {exc}")

copy_summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
if summary["copied"] == 0:
    raise SystemExit("no files copied into GitNexus mirror")
PY

cat > "$MIRROR_ROOT/.gitnexus-source.json" <<EOF
{
  "canonical_repo": "$CANONICAL_ROOT",
  "mirror_repo": "$MIRROR_ROOT",
  "branch": "$SOURCE_BRANCH",
  "source_head": "$SOURCE_HEAD",
  "canonical_head": "$SOURCE_HEAD",
  "mode": "snapshot_export",
  "synced_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "copy_summary_path": "$COPY_SUMMARY_PATH"
}
EOF

echo "[gitnexus-sync] exported filtered snapshot $SOURCE_BRANCH@$SOURCE_HEAD to $MIRROR_ROOT"
