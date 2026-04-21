#!/usr/bin/env bash
set -euo pipefail

CANONICAL_ROOT="${ROXY_MINDSONG_CANONICAL_ROOT:-$HOME/mindsong-juke-hub}"
MIRROR_ROOT="${ROXY_GITNEXUS_MINDSONG_INDEX_PATH:-$HOME/work/gitnexus-mirrors/mindsong-juke-hub}"
DEFAULT_BRANCH="${ROXY_GITNEXUS_DEFAULT_BRANCH:-main}"
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

if [[ ! -d "$MIRROR_ROOT/.git" ]]; then
  rm -rf "$MIRROR_ROOT"
  git clone --origin canonical --branch "$SOURCE_BRANCH" --single-branch --depth 1 --no-local "$CANONICAL_ROOT" "$MIRROR_ROOT"
else
  if git -C "$MIRROR_ROOT" remote get-url canonical >/dev/null 2>&1; then
    git -C "$MIRROR_ROOT" remote set-url canonical "$CANONICAL_ROOT"
  else
    git -C "$MIRROR_ROOT" remote add canonical "$CANONICAL_ROOT"
  fi
fi

git -C "$MIRROR_ROOT" remote set-branches canonical "$SOURCE_BRANCH"
git -C "$MIRROR_ROOT" fetch --depth 1 --prune canonical "+refs/heads/$SOURCE_BRANCH:refs/remotes/canonical/$SOURCE_BRANCH"

SOURCE_HEAD="$(git -C "$CANONICAL_ROOT" rev-parse HEAD)"
git -C "$MIRROR_ROOT" checkout -B "$SOURCE_BRANCH" "$SOURCE_HEAD"
git -C "$MIRROR_ROOT" reset --hard "$SOURCE_HEAD"
git -C "$MIRROR_ROOT" clean -fdx

cat > "$MIRROR_ROOT/.gitnexus-source.json" <<EOF
{
  "canonical_repo": "$CANONICAL_ROOT",
  "mirror_repo": "$MIRROR_ROOT",
  "branch": "$SOURCE_BRANCH",
  "source_head": "$SOURCE_HEAD",
  "synced_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "[gitnexus-sync] synced $SOURCE_BRANCH@$SOURCE_HEAD to $MIRROR_ROOT"
