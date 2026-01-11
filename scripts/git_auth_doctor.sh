#!/usr/bin/env bash
# git_auth_doctor.sh - Verify git auth is correctly configured
# Enforces "any agent, any box, any repo" invariants
set -euo pipefail

echo "========================================"
echo "Git Auth Doctor"
echo "Timestamp: $(date -Iseconds)"
echo "Host: $(hostname)"
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

# === Check 1: Git identity ===
echo "=== Check 1: Git Identity ==="
GIT_NAME=$(git config --global user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")

if [ -n "$GIT_NAME" ]; then
    check_pass "user.name set: $GIT_NAME"
else
    check_fail "user.name not set" "git config --global user.name 'Your Name'"
fi

if [ -n "$GIT_EMAIL" ]; then
    check_pass "user.email set: $GIT_EMAIL"
else
    check_fail "user.email not set" "git config --global user.email 'you@example.com'"
fi
echo ""

# === Check 2: GitHub CLI ===
echo "=== Check 2: GitHub CLI (gh) ==="
if command -v gh &>/dev/null; then
    check_pass "gh CLI installed"

    if gh auth status &>/dev/null; then
        check_pass "gh authenticated"

        # Check for required scopes
        SCOPES=$(gh auth status 2>&1 | grep "Token scopes" || echo "")
        if echo "$SCOPES" | grep -q "repo"; then
            check_pass "Has 'repo' scope"
        else
            check_fail "Missing 'repo' scope" "gh auth refresh -h github.com -s repo"
        fi

        if echo "$SCOPES" | grep -q "workflow"; then
            check_pass "Has 'workflow' scope (can push .github/workflows/*)"
        else
            check_fail "Missing 'workflow' scope" "gh auth refresh -h github.com -s workflow"
        fi
    else
        check_fail "gh not authenticated" "gh auth login"
    fi
else
    check_warn "gh CLI not installed" "Install from https://cli.github.com/"
fi
echo ""

# === Check 3: SSH Key ===
echo "=== Check 3: SSH Key ==="
SSH_KEY="$HOME/.ssh/id_ed25519"
if [ -f "$SSH_KEY" ]; then
    check_pass "SSH key exists: $SSH_KEY"

    # Check if key is in agent
    if ssh-add -l 2>/dev/null | grep -q "ed25519"; then
        check_pass "SSH key loaded in agent"
    else
        check_warn "SSH key not in agent" "eval \"\$(ssh-agent -s)\" && ssh-add $SSH_KEY"
    fi
else
    check_warn "No ed25519 SSH key" "ssh-keygen -t ed25519 -C \"$(hostname)\" -f $SSH_KEY -N \"\""
fi
echo ""

# === Check 4: GitHub SSH connectivity ===
echo "=== Check 4: GitHub SSH Connectivity ==="
SSH_TEST=$(ssh -T git@github.com 2>&1 || true)
if echo "$SSH_TEST" | grep -q "successfully authenticated"; then
    check_pass "SSH to GitHub works"
else
    check_warn "SSH to GitHub failed" "Add SSH key to https://github.com/settings/keys"
fi
echo ""

# === Check 5: Credential helper ===
echo "=== Check 5: Credential Helper ==="
CRED_HELPER=$(git config --global credential.helper 2>/dev/null || echo "")
if [ -n "$CRED_HELPER" ]; then
    check_pass "credential.helper set: $CRED_HELPER"
else
    check_warn "No credential.helper set" "gh auth setup-git (for gh) or configure manually"
fi
echo ""

# === Check 6: Current repo remote (if in a git repo) ===
echo "=== Check 6: Current Repo Remote ==="
if git rev-parse --git-dir &>/dev/null; then
    REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
    if [ -n "$REMOTE" ]; then
        check_pass "origin remote: $REMOTE"
        if echo "$REMOTE" | grep -q "^git@"; then
            check_pass "Using SSH protocol"
        elif echo "$REMOTE" | grep -q "^https://"; then
            check_pass "Using HTTPS protocol (requires gh or credential helper)"
        fi
    else
        check_warn "No origin remote" "git remote add origin <url>"
    fi
else
    echo "  [INFO] Not in a git repository"
fi
echo ""

# === Summary ===
echo "========================================"
echo "Summary: $PASS passed, $FAIL failed, $WARN warnings"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "ACTION REQUIRED: Fix the failures above before pushing."
    echo "See: docs/GIT_AUTH_STANDARD.md for full documentation."
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo ""
    echo "OPTIONAL: Consider addressing warnings for full robustness."
    exit 0
else
    echo ""
    echo "All checks passed. Ready to push to any repo."
    exit 0
fi
