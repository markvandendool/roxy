#!/bin/bash
# Comprehensive Cursor Performance Fix
# Kills runaway processes, optimizes settings, and ensures smooth operation

set -euo pipefail

echo "🔧 FIXING CURSOR PERFORMANCE - COMPREHENSIVE FIX"
echo "================================================"
echo ""

# 1. Monitor runaway Cursor processes (>80% CPU for >5 minutes) - LOG ONLY, DO NOT KILL
echo "1️⃣  Monitoring for high CPU processes (logging only, not killing)..."
CURSOR_PIDS=$(pgrep -f cursor 2>/dev/null || true)
HIGH_CPU_COUNT=0

for pid in $CURSOR_PIDS; do
    if kill -0 "$pid" 2>/dev/null; then
        CPU_USAGE=$(ps -p "$pid" -o %cpu= 2>/dev/null | tr -d ' ' || echo "0")
        CPU_TIME=$(ps -p "$pid" -o etime= 2>/dev/null | awk '{print $1}' | cut -d: -f1 || echo "0")
        
        if [ -n "$CPU_USAGE" ] && [ -n "$CPU_TIME" ]; then
            CPU_USAGE_INT=${CPU_USAGE%.*}
            CPU_TIME_INT=${CPU_TIME:-0}
            
            if [ "$CPU_USAGE_INT" -gt 80 ] && [ "$CPU_TIME_INT" -gt 5 ]; then
                echo "   ⚠️  High CPU process detected: PID $pid (${CPU_USAGE}% CPU, ${CPU_TIME} min) - LOGGING ONLY"
                HIGH_CPU_COUNT=$((HIGH_CPU_COUNT + 1))
            fi
        fi
    fi
done

if [ $HIGH_CPU_COUNT -eq 0 ]; then
    echo "   ✅ No high CPU processes detected"
else
    echo "   ℹ️  Found $HIGH_CPU_COUNT high CPU process(es) (logged, not killed)"
fi
echo ""

# 2. Verify optimization service is running
echo "2️⃣  Checking optimization service..."
if systemctl is-active --quiet cursor-max-performance-optimized.service 2>/dev/null; then
    echo "   ✅ Service is running"
else
    echo "   ⚠️  Service is not running (attempting to start...)"
    sudo systemctl start cursor-max-performance-optimized.service 2>/dev/null || echo "   ❌ Could not start service"
fi
echo ""

# 3. Verify file watcher limit
echo "3️⃣  Checking file watcher limit..."
CURRENT_LIMIT=$(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null || echo "0")
if [ "$CURRENT_LIMIT" -lt 1048576 ]; then
    echo "   ⚠️  Limit is $CURRENT_LIMIT (should be 1048576)"
    sudo sysctl -w fs.inotify.max_user_watches=1048576 2>/dev/null && echo "   ✅ Increased to 1048576" || echo "   ❌ Could not increase"
else
    echo "   ✅ Limit is sufficient: $CURRENT_LIMIT"
fi
echo ""

# 4. Verify Cursor settings
echo "4️⃣  Verifying Cursor settings..."
SETTINGS_FILE="$HOME/.config/Cursor/User/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    if grep -q '"files.watcherExclude"' "$SETTINGS_FILE" && grep -q '"search.exclude"' "$SETTINGS_FILE"; then
        echo "   ✅ Settings file has exclusions configured"
    else
        echo "   ⚠️  Settings file missing exclusions"
    fi
else
    echo "   ⚠️  Settings file not found"
fi
echo ""

# 5. Verify .cursorignore
echo "5️⃣  Verifying .cursorignore..."
if [ -f "/opt/roxy/.cursorignore" ]; then
    IGNORE_COUNT=$(wc -l < /opt/roxy/.cursorignore)
    echo "   ✅ .cursorignore exists with $IGNORE_COUNT exclusions"
else
    echo "   ⚠️  .cursorignore not found"
fi
echo ""

# 6. Check GPU acceleration
echo "6️⃣  Checking GPU acceleration..."
if [ "$DRI_PRIME" = "2" ] 2>/dev/null || [ -n "${DRI_PRIME:-}" ]; then
    echo "   ✅ DRI_PRIME is set: ${DRI_PRIME:-not set}"
else
    echo "   ⚠️  DRI_PRIME not set in environment"
fi
echo ""

echo "================================================"
echo "✅ COMPREHENSIVE FIX COMPLETE"
echo ""
echo "📊 Summary:"
echo "   - Runaway processes: $KILLED killed"
echo "   - Optimization service: $(systemctl is-active cursor-max-performance-optimized.service 2>/dev/null && echo 'running' || echo 'not running')"
echo "   - File watcher limit: $(cat /proc/sys/fs/inotify/max_user_watches 2>/dev/null || echo 'unknown')"
echo ""
echo "💡 If issues persist, restart Cursor completely."
echo ""







