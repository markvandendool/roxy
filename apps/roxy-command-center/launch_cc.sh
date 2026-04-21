#!/bin/bash
# ROXY Command Center Launch + PID Tracking
# Usage: ./launch_cc.sh [stop|restart|status]

set -euo pipefail

PIDFILE="$HOME/.cache/roxy-command-center/cc.pid"
LOGFILE="$HOME/.cache/roxy-command-center/run.log"
APP_DIR="$HOME/.roxy/apps/roxy-command-center"
APP_SCRIPT="$APP_DIR/main.py"
DESKTOP_LAUNCHER="$APP_DIR/launch.sh"

mkdir -p "$(dirname "$PIDFILE")"

pid_matches_app() {
    local pid="${1:-}"
    local cmdline=""
    local cwd=""
    local stat=""

    [ -n "$pid" ] || return 1
    [ -r "/proc/$pid/cmdline" ] || return 1

    stat="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d '[:space:]' || true)"
    [ -n "$stat" ] || return 1
    case "$stat" in
        Z|Z*) return 1 ;;
    esac

    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline")"

    if printf '%s' "$cmdline" | grep -Fq "$APP_SCRIPT"; then
        return 0
    fi

    if [ -L "/proc/$pid/cwd" ]; then
        cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
        if [ "$cwd" = "$APP_DIR" ] && printf '%s' "$cmdline" | grep -Eq '(^|[[:space:]])main\.py([[:space:]]|$)'; then
            return 0
        fi
    fi

    return 1
}

resolve_app_pid() {
    local pid=""

    if [ -f "$PIDFILE" ]; then
        pid="$(tr -d '[:space:]' < "$PIDFILE")"
        if pid_matches_app "$pid"; then
            printf '%s\n' "$pid"
            return 0
        fi
        rm -f "$PIDFILE"
    fi

    while read -r pid; do
        [ -n "$pid" ] || continue
        if pid_matches_app "$pid"; then
            printf '%s\n' "$pid" > "$PIDFILE"
            printf '%s\n' "$pid"
            return 0
        fi
    done < <(pgrep -f "main.py" || true)

    return 1
}

case "${1:-start}" in
    stop)
        if PID="$(resolve_app_pid)"; then
            echo "Stopping Command Center (PID $PID)..."
            if kill -TERM "$PID" 2>/dev/null; then
                echo "Sent SIGTERM to $PID, waiting up to 10 seconds..."
                for _ in {1..20}; do
                    if ! pid_matches_app "$PID"; then
                        echo "Process $PID exited gracefully"
                        rm -f "$PIDFILE"
                        exit 0
                    fi
                    sleep 0.5
                done
                echo "Process $PID did not exit, sending SIGKILL..."
                kill -KILL "$PID" 2>/dev/null || true
                sleep 1
            fi
            rm -f "$PIDFILE"
            echo "Stopped"
        else
            echo "Command Center not running"
        fi
        ;;
    
    status)
        if PID="$(resolve_app_pid)"; then
            echo "Command Center running (PID $PID)"
            ps -p "$PID" -o pid,ppid,cmd,etime
        else
            echo "Command Center not running"
        fi
        ;;
    
    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;
    
    start)
        if PID="$(resolve_app_pid)"; then
            echo "Command Center already running (PID $PID)"
            exit 0
        fi
        
        echo "Starting ROXY Command Center..."

        rm -f "$PIDFILE"
        setsid -f "$DESKTOP_LAUNCHER" >/dev/null 2>&1

        for _ in {1..40}; do
            sleep 0.25
            if PID="$(resolve_app_pid)"; then
                echo "Command Center started successfully (PID $PID)"
                echo "Logs: $LOGFILE"
                echo "PID: $PIDFILE"
                exit 0
            fi
        done

        echo "Command Center failed to start"
        echo "Last 20 lines of log:"
        tail -20 "$LOGFILE"
        exit 1
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
