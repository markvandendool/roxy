# ROXY Git Workflow Protocol

**Last Updated:** 2026-03-20 | **Status:** Active | **Repo:** mindsong-juke-hub

This protocol defines how ROXY safely interacts with the mindsong-juke-hub repository.

---

## Architecture

```
┌─────────────────────┐          ┌─────────────────────┐          ┌─────────────────────┐
│   Mac Studio        │          │      GitHub         │          │   Linux (ROXY)      │
│   (Primary Dev)     │          │   (Source of Truth) │          │   (Agent Sandbox)   │
│                     │          │                     │          │                     │
│  mindsong-juke-hub  │──push───▶│       main          │◀──fetch──│  LOCAL CLONE        │
│  (direct commits)   │          │    (protected)      │          │  (read-only main)   │
│                     │          │                     │          │                     │
│                     │          │     roxy/* branches │◀──push───│  roxy/* branches    │
│                     │◀─────────│        ↓            │          │  (agent work)       │
│                     │   merge  │    PR + Review      │          │                     │
└─────────────────────┘          └─────────────────────┘          └─────────────────────┘
```

**ROXY Local Clone:** `~/work/mindsong_gh_https_1769765834/mindsong-juke-hub`

Note: There's also an sshfs mount at `~/mindsong-juke-hub` - this is for viewing only, not for ROXY operations.

---

## Core Rules

### ALLOWED Operations

```bash
git fetch origin              # Always safe
git checkout main             # Safe (read-only main)
git reset --hard origin/main  # Safe (sync to latest)
git checkout -b roxy/{name}   # Create work branch
git add {specific files}      # Stage changes
git commit -m "message"       # Commit to branch
git push -u origin roxy/{name} # Push branch
gh pr create                  # Create PR for review
```

### FORBIDDEN Operations

```bash
git push origin main          # BLOCKED by hook
git push --force              # BLOCKED by hook
git merge {anything}          # No local merges
gh pr merge                   # Human must approve
git rebase main               # Dangerous, avoid
git checkout -- {file}        # May destroy work
git add -A                    # May stage wrong files
git add .                     # May stage wrong files
```

---

## Workflow: Before Starting Work

1. **Sync to latest main:**
   ```bash
   cd ~/mindsong-juke-hub
   git fetch origin
   git checkout main
   git reset --hard origin/main
   ```

2. **Create task branch:**
   ```bash
   git checkout -b roxy/{story-id}-{brief-description}
   ```

   Examples:
   ```bash
   git checkout -b roxy/EXTRACT-006-mac-studio-deploy
   git checkout -b roxy/fix-streaming-errors
   git checkout -b roxy/add-qualification-pipeline
   ```

---

## Workflow: During Work

1. **Commit frequently** with clear messages
2. **Stage specific files only:**
   ```bash
   git add src/specific-file.ts
   git add docs/updated-doc.md
   ```

3. **NEVER use:**
   ```bash
   git add -A    # FORBIDDEN
   git add .     # FORBIDDEN
   ```

4. **Run tests before committing** (if applicable)

---

## Workflow: After Completing Work

1. **Push branch to origin:**
   ```bash
   git push -u origin roxy/{branch-name}
   ```

2. **Create Pull Request:**
   ```bash
   gh pr create --title "ROXY: {description}" --body "## Summary
   - Change 1
   - Change 2

   ## Testing
   - Test performed

   ---
   *Automated by ROXY*"
   ```

3. **Return to main:**
   ```bash
   git checkout main
   git reset --hard origin/main
   ```

4. **Wait for human review and merge**

---

## Automated Sync

A cron job runs every 30 minutes to keep main updated:

```
*/30 * * * * ~/.roxy/scripts/git_sync.sh
```

This script:
- Fetches latest from origin
- Resets main to origin/main (only if on main with no changes)
- Prunes deleted remote branches
- Cleans up merged roxy/* branches

**Logs:** `~/.roxy/data/git_sync.log`

---

## Safety Hooks

### pre-push Hook

Blocks:
- Pushes from main branch
- Pushes to remote main

Location: `~/mindsong-juke-hub/.git/hooks/pre-push`

### Existing Hooks (mindsong)

The repo has additional hooks from `.husky/`:
- pre-commit: Linting, type checking
- commit-msg: Commit message format

### GitHub Branch Protection (Recommended)

For additional safety, configure branch protection in GitHub:

**Settings → Branches → Add rule for `main`:**

| Setting | Value |
|---------|-------|
| Require pull request reviews | ✓ (1 approval) |
| Require status checks | ✓ |
| Require linear history | ✓ |
| Do not allow bypassing | ✓ |
| Restrict direct pushes | Only Mac Studio user |

This provides server-side enforcement even if hooks are bypassed.

**Note:** This is a manual configuration step. The local hooks provide immediate protection, GitHub protection adds defense-in-depth.

---

## Branch Naming Convention

```
roxy/{story-id}-{brief-description}
```

| Prefix | Use Case |
|--------|----------|
| `roxy/STORY-ID-*` | SKOREQ story work |
| `roxy/fix-*` | Bug fixes |
| `roxy/add-*` | New features |
| `roxy/update-*` | Updates/improvements |
| `roxy/docs-*` | Documentation only |

---

## Error Recovery

### If you accidentally commit to main

```bash
# Don't panic - you can't push anyway
git checkout -b roxy/recovery-branch
git checkout main
git reset --hard origin/main
git checkout roxy/recovery-branch
# Continue working on branch
```

### If push fails

```bash
# Check you're not on main
git branch

# If on main, create branch first
git checkout -b roxy/your-work

# Try push again
git push -u origin roxy/your-work
```

### If sync script fails

```bash
# Manual sync
cd ~/mindsong-juke-hub
git fetch origin
git checkout main
git reset --hard origin/main
```

---

## Integration with ROXY Missions

When executing a mission:

```python
def pre_mission_git_setup(story_id: str, description: str) -> str:
    """Called before mission execution."""
    repo_dir = Path.home() / "mindsong-juke-hub"

    # Sync main
    subprocess.run(["git", "fetch", "origin"], cwd=repo_dir)
    subprocess.run(["git", "checkout", "main"], cwd=repo_dir)
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_dir)

    # Create branch
    branch = f"roxy/{story_id}-{description[:30].lower().replace(' ', '-')}"
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo_dir)

    return branch

def post_mission_git_cleanup(branch: str, success: bool):
    """Called after mission execution."""
    if success:
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=repo_dir)
        subprocess.run(["gh", "pr", "create", "--fill"], cwd=repo_dir)

    # Return to main
    subprocess.run(["git", "checkout", "main"], cwd=repo_dir)
    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_dir)
```

---

## Quick Reference

```
╔═══════════════════════════════════════════════════════════════╗
║              ROXY GIT WORKFLOW QUICK REFERENCE                ║
╠═══════════════════════════════════════════════════════════════╣
║ Repo:        ~/work/mindsong_gh_https_.../mindsong-juke-hub   ║
║ Branches:    roxy/* only (NEVER main)                         ║
║ Sync:        Auto every 30 min via cron                       ║
║ Logs:        ~/.roxy/data/git_sync.log                        ║
║                                                               ║
║ START WORK:                                                   ║
║   git fetch origin && git checkout main                       ║
║   git reset --hard origin/main                                ║
║   git checkout -b roxy/{story-id}-{desc}                      ║
║                                                               ║
║ FINISH WORK:                                                  ║
║   git push -u origin roxy/{branch}                            ║
║   gh pr create                                                ║
║   git checkout main && git reset --hard origin/main           ║
║                                                               ║
║ FORBIDDEN:                                                    ║
║   git push origin main                                        ║
║   git push --force                                            ║
║   git add -A / git add .                                      ║
║   gh pr merge                                                 ║
╚═══════════════════════════════════════════════════════════════╝
```

---

*This protocol is enforced by git hooks. Violations will be blocked automatically.*
