# ROXY Git Workflow Protocol
**Last Updated:** 2026-04-15 | **Status:** Active | **Repo:** mindsong-juke-hub

This protocol defines how ROXY safely interacts with the mindsong-juke-hub repository.

---

## Architecture

```
Mac Studio (Primary Dev)          Linux (ROXY Sandbox)           GitHub
    │                                │                              │
    ├── Direct push to main ──────────▶│       main (protected)      │
    │                                │                              │
    │                                ├── ~/mindsong-juke-hub ────▶ roxy/* branches
    │                                │   (sshfs or https)           │
    │                                │                              │
    │                                └── Cron: git sync ──────────────── fetch main
```

**Working Repo:** `~/mindsong-juke-hub`

---

## Core Rules

### ALLOWED
- `git fetch origin` - Read latest
- `git checkout -b roxy/{task-name}` - Create branch  
- `git add / git commit` - Commit work
- `git push -u origin roxy/{branch}` - Push branch

### FORBIDDEN (Blocked by Hooks)
- `git push origin main` - BLOCKED by pre-push hook
- `git push --force` - BLOCKED by pre-push hook

---

## Pre-push Hook
Location: `~/mindsong-juke-hub/.git/hooks/pre-push`

---

## Workflow

### Before Work
```bash
cd ~/mindsong-juke-hub
git fetch origin
git checkout -b roxy/your-task-name
```

### After Work
```bash
git push -u origin roxy/your-task-name
gh pr create
```

---

**NEVER:** push main, force push
