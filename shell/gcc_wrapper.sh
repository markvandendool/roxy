#!/bin/bash
# Rocky Shell - GCC Error Wrapper
# Story: RAF-016
# Target: Parse compiler errors, suggest fixes via ROXY
#
# Usage: Add to PATH before /usr/bin, or use roxy-gcc alias

ROXY_SHM="/dev/shm/roxy_brain"
REAL_GCC="/usr/bin/gcc"
REAL_GPP="/usr/bin/g++"

# Determine which compiler to use
COMPILER="$REAL_GCC"
if [[ "$0" == *"g++"* ]] || [[ "$0" == *"roxy-g++"* ]]; then
    COMPILER="$REAL_GPP"
fi

# Run the actual compiler and capture output
TMPFILE=$(mktemp)
"$COMPILER" "$@" 2>&1 | tee "$TMPFILE"
EXIT_CODE=${PIPESTATUS[0]}

# Only process if there were errors
if [[ $EXIT_CODE -ne 0 ]]; then
    # Parse error output
    ERRORS=$(grep -E "^[^:]+:[0-9]+:[0-9]+: error:" "$TMPFILE")
    WARNINGS=$(grep -E "^[^:]+:[0-9]+:[0-9]+: warning:" "$TMPFILE")

    ERROR_COUNT=$(echo "$ERRORS" | grep -c "error:" || echo 0)
    WARNING_COUNT=$(echo "$WARNINGS" | grep -c "warning:" || echo 0)

    # Send to ROXY if brain is running
    if [[ -e "$ROXY_SHM" ]]; then
        # Create JSON payload
        PAYLOAD=$(cat <<EOF
{
    "type": "compiler_error",
    "compiler": "$(basename $COMPILER)",
    "exit_code": $EXIT_CODE,
    "error_count": $ERROR_COUNT,
    "warning_count": $WARNING_COUNT,
    "errors": $(echo "$ERRORS" | head -5 | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip().split("\n")))'),
    "command": "$*",
    "timestamp": "$(date -Iseconds)"
}
EOF
)
        # Write to shared memory via helper
        echo "$PAYLOAD" | python3 -c '
import sys
import json
sys.path.insert(0, "'$HOME'/.roxy/ipc")
try:
    from shm_brain import RoxyShmBrain
    brain = RoxyShmBrain(create=False)
    data = json.load(sys.stdin)
    brain.write_json(brain.MSG_STATE, data)
    brain.cleanup()
except:
    pass
' 2>/dev/null
    fi

    # Print helpful suggestions for common errors
    if echo "$ERRORS" | grep -q "undeclared"; then
        echo ""
        echo -e "\033[33m[ROXY] Tip: Check for missing #include or typos in variable names\033[0m"
    fi

    if echo "$ERRORS" | grep -q "expected"; then
        echo ""
        echo -e "\033[33m[ROXY] Tip: Check for missing semicolons, brackets, or parentheses\033[0m"
    fi

    if echo "$ERRORS" | grep -q "undefined reference"; then
        echo ""
        echo -e "\033[33m[ROXY] Tip: Link the required library with -l flag\033[0m"
    fi

    if echo "$ERRORS" | grep -q "incompatible types"; then
        echo ""
        echo -e "\033[33m[ROXY] Tip: Check type conversions and function signatures\033[0m"
    fi
fi

rm -f "$TMPFILE"
exit $EXIT_CODE
