#!/bin/bash
# ROXY Command Center Launcher
# Desktop entry target. Lets Gio.Application enforce single-instance behavior.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ID="org.roxy.CommandCenter"
APP_SCRIPT="$SCRIPT_DIR/main.py"
CACHE_DIR="$HOME/.cache/roxy-command-center"
LOGFILE="$CACHE_DIR/run.log"

pick_python() {
    local venv_python="$HOME/.roxy/venv/bin/python"
    local system_python="/usr/bin/python3"

    if [ -x "$venv_python" ] && "$venv_python" - <<'PY' >/dev/null 2>&1
import gi
import cairo
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Soup", "3.0")
from gi.repository import Gtk, Adw, Soup
PY
    then
        printf '%s\n' "$venv_python"
        return 0
    fi

    printf '%s\n' "$system_python"
}

pick_gdk_backend() {
    if [ -n "${ROXY_GDK_BACKEND:-}" ]; then
        printf '%s\n' "$ROXY_GDK_BACKEND"
        return 0
    fi

    if [ "${XDG_SESSION_TYPE:-}" = "wayland" ] && [ -n "${WAYLAND_DISPLAY:-}" ]; then
        printf '%s\n' "wayland"
        return 0
    fi

    if [ -n "${DISPLAY:-}" ]; then
        printf '%s\n' "x11"
        return 0
    fi

    printf '%s\n' ""
}

mkdir -p "$CACHE_DIR"

PYTHON_BIN="$(pick_python)"
GDK_BACKEND_VALUE="$(pick_gdk_backend)"
SESSION_STAMP="$(date '+%Y-%m-%dT%H:%M:%S%z')"
SESSION_TAG="$(date '+%Y%m%d-%H%M%S')"

launch_env=("PYTHONUNBUFFERED=1" "ROXY_COMMAND_CENTER_APP_ID=$APP_ID")
if [ -n "$GDK_BACKEND_VALUE" ]; then
    launch_env+=("GDK_BACKEND=$GDK_BACKEND_VALUE")
fi
if [ "$GDK_BACKEND_VALUE" = "x11" ] && [ -z "${DISPLAY:-}" ]; then
    launch_env+=("DISPLAY=:0")
fi

if [ -t 1 ] && [ -t 2 ]; then
    exec env "${launch_env[@]}" "$PYTHON_BIN" "$APP_SCRIPT" "$@"
fi

if [ -f "$LOGFILE" ] && [ -s "$LOGFILE" ]; then
    mv -f "$LOGFILE" "$CACHE_DIR/run-$SESSION_TAG.log"
fi

: > "$LOGFILE"
{
    echo "=== ROXY Command Center launch $SESSION_STAMP ==="
    echo "app_id=$APP_ID"
    echo "launcher=$0"
    echo "python=$PYTHON_BIN"
    echo "backend=${GDK_BACKEND_VALUE:-auto}"
    echo "display=${DISPLAY:-unset}"
    echo "wayland_display=${WAYLAND_DISPLAY:-unset}"
    echo "xdg_session_type=${XDG_SESSION_TYPE:-unset}"
    echo "app_script=$APP_SCRIPT"
    echo
} >> "$LOGFILE"

exec env "${launch_env[@]}" "$PYTHON_BIN" "$APP_SCRIPT" "$@" >> "$LOGFILE" 2>&1
