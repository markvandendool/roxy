#!/usr/bin/env bash
# @pipeline StackKraft
# @locked true
# @change_requires HumanApproval
# @owner Chief
set -euo pipefail

# package_obs.sh
# Usage: ./package_obs.sh --src <source_dir> --out <out_dir> --version <version>
# Default source_dir: ~/.roxy/obs-scripts (change as needed)

SRC_DIR="${SRC_DIR:-$HOME/.roxy/obs-scripts}"
OUT_DIR="${OUT_DIR:-$PWD/releases}"
VERSION="${VERSION:-$(date +%Y%m%d_%H%M%S)}"
PKG_NAME="roxy-obs-scripts-${VERSION}.zip"
TMP_DIR="/tmp/roxy-obs-pkg-${VERSION}"

usage() {
  cat <<EOF
Usage: $0 [--src <source_dir>] [--out <out_dir>] [--version <version>]

Creates a distributable ZIP containing OBS automation scripts, README, LICENSE, and example assets.

Defaults:
  src:  $SRC_DIR
  out:  $OUT_DIR
  version: $VERSION

Example:
  ./package_obs.sh --src ~/.roxy/obs-scripts --out ~/releases --version v1.0.0
EOF
  exit 1
}

# parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC_DIR="$2"; shift 2 ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    --version) VERSION="$2"; PKG_NAME="roxy-obs-scripts-${VERSION}.zip"; TMP_DIR="/tmp/roxy-obs-pkg-${VERSION}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

# sanity checks
if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory not found: $SRC_DIR" >&2
  exit 2
fi
mkdir -p "$OUT_DIR"
rm -rf "$TMP_DIR" && mkdir -p "$TMP_DIR"

# Files to include (adjust as needed)
rsync -av --progress --exclude 'node_modules' --exclude '.git' \
  "$SRC_DIR/" "$TMP_DIR/obs-scripts/"

# Generate RELEASE metadata
cat > "$TMP_DIR/RELEASE_NOTES.txt" <<RELEASE
Package: Roxy OBS Automation Scripts
Version: $VERSION
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Included:
- scripts/ (Python / Bash helper scripts)
- README.md
- LICENSE
- examples/ (optional sample scenes)

Usage:
- Unzip and follow README for installation instructions
- Support: stackkraft@gmail.com
RELEASE

# Create ZIP
pushd "$TMP_DIR" >/dev/null
zip -r "$OUT_DIR/$PKG_NAME" .
popd >/dev/null

# Create checksum
sha256sum "$OUT_DIR/$PKG_NAME" > "$OUT_DIR/$PKG_NAME.sha256"

echo "Created $OUT_DIR/$PKG_NAME"
ls -lh "$OUT_DIR/$PKG_NAME"

# cleanup
rm -rf "$TMP_DIR"

exit 0
