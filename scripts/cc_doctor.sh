#!/usr/bin/env bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# cc_doctor.sh - Command Center prerequisites check
# Verifies all dependencies before launch to prevent silent failures
set -euo pipefail

echo "========================================"
echo "Command Center Doctor"
echo "Timestamp: $(date -Iseconds)"
echo "========================================"
echo ""

PASS=0
FAIL=0
WARN=0

check_pass() {
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
}

check_fail() {
    echo "  [FAIL] $1"
    echo "         Fix: $2"
    FAIL=$((FAIL + 1))
}

check_warn() {
    echo "  [WARN] $1"
    echo "         Note: $2"
    WARN=$((WARN + 1))
}

# === Check 1: Python + venv ===
echo "=== Check 1: Python Environment ==="
VENV_PYTHON="$HOME/.roxy/venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    check_pass "venv python exists: $VENV_PYTHON"
else
    check_fail "venv python not found" "python3 -m venv ~/.roxy/venv"
fi

# Check system site-packages
if grep -q "include-system-site-packages = true" "$HOME/.roxy/venv/pyvenv.cfg" 2>/dev/null; then
    check_pass "venv includes system site-packages"
else
    check_fail "venv excludes system site-packages (GTK won't work)" \
        "Edit ~/.roxy/venv/pyvenv.cfg: set include-system-site-packages = true"
fi
echo ""

# === Check 2: PyGObject (gi) ===
echo "=== Check 2: PyGObject (GTK bindings) ==="
if $VENV_PYTHON -c "import gi" 2>/dev/null; then
    check_pass "gi module importable"
else
    check_fail "gi module not importable" \
        "apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
fi

if $VENV_PYTHON -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" 2>/dev/null; then
    check_pass "GTK 4.0 available"
else
    check_fail "GTK 4.0 not available" "apt install gir1.2-gtk-4.0 libgtk-4-1"
fi

if $VENV_PYTHON -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw" 2>/dev/null; then
    check_pass "libadwaita available"
else
    check_warn "libadwaita not available" "apt install gir1.2-adw-1 libadwaita-1-0"
fi
echo ""

# === Check 3: Display Environment ===
echo "=== Check 3: Display Environment ==="
if [ -n "${DISPLAY:-}" ]; then
    check_pass "DISPLAY set: $DISPLAY"
elif [ -n "${WAYLAND_DISPLAY:-}" ]; then
    check_pass "WAYLAND_DISPLAY set: $WAYLAND_DISPLAY"
else
    check_fail "No display (DISPLAY/WAYLAND_DISPLAY unset)" \
        "Run from a graphical session, not SSH without X forwarding"
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ]; then
    check_pass "XDG_RUNTIME_DIR set: $XDG_RUNTIME_DIR"
else
    check_warn "XDG_RUNTIME_DIR not set" "May cause issues with some GNOME integrations"
fi
echo ""

# === Check 4: roxy-core ===
echo "=== Check 4: roxy-core Backend ==="
if curl -sS --connect-timeout 2 http://127.0.0.1:8766/health >/dev/null 2>&1; then
    check_pass "roxy-core reachable at :8766"
else
    check_fail "roxy-core not reachable" \
        "systemctl --user start roxy-core.service"
fi

if curl -sS --connect-timeout 2 http://127.0.0.1:8766/ready 2>/dev/null | grep -q '"ready": true'; then
    check_pass "roxy-core reports ready"
else
    check_warn "roxy-core not fully ready" "Check: curl http://127.0.0.1:8766/ready"
fi
echo ""

# === Check 5: Auth Token ===
echo "=== Check 5: Authentication ==="
TOKEN_FILE="$HOME/.roxy/secret.token"
if [ -f "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ]; then
    check_pass "Token file exists and non-empty"
else
    check_fail "Token file missing or empty" \
        "python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > ~/.roxy/secret.token"
fi
echo ""

# === Check 6: App Files ===
echo "=== Check 6: Application Files ==="
APP_DIR="$HOME/.roxy/apps/roxy-command-center"
if [ -f "$APP_DIR/main.py" ]; then
    check_pass "main.py exists"
else
    check_fail "main.py not found" "Check: ls $APP_DIR"
fi

if [ -d "$APP_DIR/ui" ]; then
    check_pass "ui/ directory exists"
else
    check_warn "ui/ directory missing" "UI components may not load"
fi

if [ -d "$APP_DIR/styles" ]; then
    check_pass "styles/ directory exists"
else
    check_warn "styles/ directory missing" "CSS may not load"
fi
echo ""

# === Summary ===
echo "========================================"
echo "Summary: $PASS passed, $FAIL failed, $WARN warnings"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "ACTION REQUIRED: Fix failures before launching Command Center."
    echo "See: docs/RUNBOOK.md for details."
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo ""
    echo "Command Center should launch, but warnings may cause issues."
    exit 0
else
    echo ""
    echo "All checks passed. Command Center ready to launch."
    echo ""
    echo "Launch: ~/.roxy/apps/roxy-command-center/launch_cc.sh"
    echo "   Or:  ~/.roxy/venv/bin/python ~/.roxy/apps/roxy-command-center/main.py"
    exit 0
fi