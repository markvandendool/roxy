# Agent Rules (Non-Negotiable)

> ⚠️ **DEPRECATED — ERA 1 GOVERNANCE**
>
> This document is no longer authoritative.
> All agents MUST follow [`docs/governance/CANONICAL_GOVERNANCE.md`](./governance/CANONICAL_GOVERNANCE.md).
>
> **Key changes in Era 3:**
> - Agents MAY commit within L2 limits (100 files max)
> - Override requires exact `FORCE PUSH — GOVERNANCE OVERRIDE` protocol
> - Time pressure NEVER escalates authority tier
>
> **Deprecated:** 2025-12-18 (Era 3 governance reconciliation)

---

**Effective Date:** 2025-12-13
**Status:** ~~LOCKED~~ DEPRECATED — Superseded by Era 3 governance

---

## 🚫 FORBIDDEN Operations

Agents **MUST NOT**:

1. **Run tasks** (no `npm run`, `pnpm`, `vite`, etc.)
2. **Commit changes** (no `git commit`)
3. **Switch branches** (no `git checkout`, `git switch`)
4. **Push to remote** (no `git push`)
5. **Merge branches** (no `git merge` without explicit user approval)
6. **Create branches** (no `git branch` or `git checkout -b`)

---

## ✅ ALLOWED Operations

Agents **MAY**:

1. **Read files** (read_file, grep, codebase_search)
2. **Propose diffs** (search_replace, write with user approval)
3. **Write tests** (create test files)
4. **Explain failures** (analyze errors, debug)
5. **Suggest fixes** (propose code changes)

---

## 🎯 Execution Model

**All execution requires manual user approval.**

- User reviews proposed changes
- User executes git operations
- User runs tasks/tests
- User approves merges

This matches **Chief Mode** and actual working style.

---

## 📝 Rationale

Previous agent autonomy led to:
- Task runner chaos
- Branch churn
- VS Code workspace corruption
- Uncontrolled commits

**Lockdown prevents repeat incidents.**

---

## 🔄 Review Process

To modify these rules:
1. Propose change to Chief
2. Get explicit approval
3. Update this document
4. Announce to all agents

**No exceptions without Chief approval.**























