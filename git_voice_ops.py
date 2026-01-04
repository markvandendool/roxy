#!/usr/bin/env python3
"""
Voice-Triggered Git Operations for ROXY
Execute git commands via voice with intelligent summaries

Usage:
  python3 git_voice_ops.py status
  python3 git_voice_ops.py commit "message"
  python3 git_voice_ops.py push
  python3 git_voice_ops.py pull
  python3 git_voice_ops.py diff
  python3 git_voice_ops.py log

Part of LUNA-000 CITADEL - PRODUCT organ
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

import requests

REPO_PATH = Path.home() / "mindsong-juke-hub"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3:8b"

def run_git(args, cwd=None):
    """Run a git command and return output"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd or REPO_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def summarize_with_llm(text, prompt):
    """Get LLM summary of git output"""
    full_prompt = f"{prompt}\n\nGit output:\n{text[:2000]}\n\nProvide a concise 1-2 sentence summary:"

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 100}
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except:
        pass
    return None

def git_status():
    """Get repository status with summary"""
    stdout, stderr, code = run_git(["status", "--porcelain"])

    if code != 0:
        return f"Error getting status: {stderr}"

    if not stdout:
        return "Working directory is clean. No changes to commit."

    lines = stdout.strip().split("\n")
    modified = len([l for l in lines if l.startswith(" M") or l.startswith("M ")])
    added = len([l for l in lines if l.startswith("A ") or l.startswith("??")])
    deleted = len([l for l in lines if l.startswith(" D") or l.startswith("D ")])

    summary = f"Repository has {len(lines)} changes: {modified} modified, {added} new, {deleted} deleted files."

    # Get branch info
    branch_out, _, _ = run_git(["branch", "--show-current"])
    if branch_out:
        summary = f"On branch {branch_out}. " + summary

    return summary

def git_diff_summary():
    """Get diff summary"""
    stdout, stderr, code = run_git(["diff", "--stat"])

    if code != 0:
        return f"Error getting diff: {stderr}"

    if not stdout:
        return "No unstaged changes."

    # Get LLM summary
    llm_summary = summarize_with_llm(stdout, "Summarize these git changes for a developer:")

    if llm_summary:
        return llm_summary

    # Fallback to basic stats
    lines = stdout.strip().split("\n")
    if lines:
        return lines[-1]  # Last line has summary stats

    return "Changes detected but could not summarize."

def git_commit(message):
    """Stage all and commit with message"""
    # Stage all changes
    run_git(["add", "-A"])

    # Commit
    stdout, stderr, code = run_git(["commit", "-m", message])

    if code != 0:
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            return "Nothing to commit. Working directory is clean."
        return f"Commit failed: {stderr}"

    # Get commit hash
    hash_out, _, _ = run_git(["rev-parse", "--short", "HEAD"])

    return f"Committed as {hash_out}: {message}"

def git_push():
    """Push to origin"""
    stdout, stderr, code = run_git(["push"])

    if code != 0:
        return f"Push failed: {stderr}"

    # Check what was pushed
    if "Everything up-to-date" in stderr:
        return "Already up to date with remote."

    return "Successfully pushed to remote."

def git_pull():
    """Pull from origin"""
    stdout, stderr, code = run_git(["pull"])

    if code != 0:
        return f"Pull failed: {stderr}"

    if "Already up to date" in stdout:
        return "Already up to date with remote."

    # Summarize changes
    llm_summary = summarize_with_llm(stdout, "Summarize what was pulled from git:")
    if llm_summary:
        return llm_summary

    return "Successfully pulled from remote."

def git_log_summary(count=5):
    """Get recent commit log summary"""
    stdout, stderr, code = run_git([
        "log",
        f"-{count}",
        "--pretty=format:%h %s (%ar)",
        "--no-merges"
    ])

    if code != 0:
        return f"Error getting log: {stderr}"

    if not stdout:
        return "No recent commits found."

    commits = stdout.strip().split("\n")

    summary = f"Last {len(commits)} commits:\n"
    for commit in commits:
        summary += f"  - {commit}\n"

    return summary.strip()

def main():
    if len(sys.argv) < 2:
        print("Usage: git_voice_ops.py <command> [args]")
        print("Commands:")
        print("  status  - Get repository status")
        print("  diff    - Summarize current changes")
        print("  commit  - Stage all and commit")
        print("  push    - Push to remote")
        print("  pull    - Pull from remote")
        print("  log     - Show recent commits")
        return

    command = sys.argv[1].lower()

    print(f"[GIT] Running: {command}")

    if command == "status":
        result = git_status()

    elif command == "diff":
        result = git_diff_summary()

    elif command == "commit":
        if len(sys.argv) < 3:
            # Generate commit message from diff
            diff_out, _, _ = run_git(["diff", "--staged", "--stat"])
            if not diff_out:
                run_git(["add", "-A"])
                diff_out, _, _ = run_git(["diff", "--staged", "--stat"])

            if diff_out:
                llm_msg = summarize_with_llm(
                    diff_out,
                    "Generate a short git commit message (max 50 chars) for these changes:"
                )
                message = llm_msg or f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            else:
                message = f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        else:
            message = " ".join(sys.argv[2:])

        result = git_commit(message)

    elif command == "push":
        result = git_push()

    elif command == "pull":
        result = git_pull()

    elif command == "log":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        result = git_log_summary(count)

    else:
        result = f"Unknown command: {command}"

    print(f"\n{result}")

if __name__ == "__main__":
    main()
