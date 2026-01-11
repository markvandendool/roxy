# Git Authentication Standard

**Version:** 1.0
**Last Updated:** 2026-01-10

This document defines the standard authentication method for git operations across all machines and agents.

---

## Required Auth Method: SSH

SSH authentication is the standard for all machines. This bypasses OAuth scope limitations and works consistently for all operations including workflow file pushes.

### Initial Setup (Per Machine)

```bash
# 1. Generate SSH key (if not exists)
ssh-keygen -t ed25519 -C "roxy@$(hostname)" -f ~/.ssh/id_ed25519 -N ""

# 2. Start SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 3. Display public key (add to GitHub)
cat ~/.ssh/id_ed25519.pub
```

### Add Key to GitHub

1. Go to https://github.com/settings/keys
2. Click "New SSH key"
3. Paste the public key from step 3 above
4. Name it after the machine (e.g., "roxy-workstation")

### Convert Remotes to SSH

```bash
# Check current remote
git remote -v

# Switch from HTTPS to SSH
git remote set-url origin git@github.com:OWNER/REPO.git

# Example for ROXY
git remote set-url origin git@github.com:markvandendool/roxy.git
```

### Verification

```bash
# Test SSH connection
ssh -T git@github.com
# Expected: "Hi username! You've successfully authenticated..."

# Test push
git push origin main
```

---

## Alternative: GitHub CLI with Workflow Scope

If SSH is not available, use gh CLI with proper scopes:

```bash
# Add workflow scope
gh auth refresh -h github.com -s workflow

# Verify scopes
gh auth status
# Must show: workflow in token scopes

# Ensure git uses gh credentials
gh auth setup-git
```

**Note:** The `workflow` scope is required to push `.github/workflows/*` files.

---

## Credential Rotation

### SSH Keys

```bash
# Generate new key
ssh-keygen -t ed25519 -C "roxy@$(hostname)" -f ~/.ssh/id_ed25519_new -N ""

# Add new key to GitHub
cat ~/.ssh/id_ed25519_new.pub
# Add via https://github.com/settings/keys

# Replace old key
mv ~/.ssh/id_ed25519 ~/.ssh/id_ed25519_old
mv ~/.ssh/id_ed25519.pub ~/.ssh/id_ed25519_old.pub
mv ~/.ssh/id_ed25519_new ~/.ssh/id_ed25519
mv ~/.ssh/id_ed25519_new.pub ~/.ssh/id_ed25519.pub

# Test
ssh -T git@github.com

# Remove old key from GitHub after verification
```

### GitHub CLI Token

```bash
gh auth logout
gh auth login
# Select: SSH protocol, authenticate via browser
```

---

## Nested Repository / Submodule Handling

### Prevention

A pre-commit hook detects nested `.git` directories:

```bash
# Located at: .git/hooks/pre-commit
# Installed automatically by: scripts/install-git-hooks.sh
```

### When Detected

If git warns about "adding embedded git repository":

1. **Option A - Ignore it** (recommended for third-party clones):
   ```bash
   echo "path/to/nested/repo/" >> .gitignore
   git rm --cached path/to/nested/repo
   ```

2. **Option B - Make it a submodule** (if you need version tracking):
   ```bash
   git submodule add <url> path/to/nested/repo
   ```

3. **Option C - Flatten it** (remove nested git):
   ```bash
   rm -rf path/to/nested/repo/.git
   git add path/to/nested/repo
   ```

### Current Ignored Nested Repos

- `gesture-control/midiGesture-base/` - Third-party midiGesture clone

---

## Workflow Push Requirements

GitHub treats `.github/workflows/*` modifications as privileged operations.

| Auth Method | Can Push Workflows? |
|-------------|---------------------|
| SSH Key | Yes |
| gh CLI with `workflow` scope | Yes |
| OAuth token without `workflow` | **No** |
| Classic PAT with `repo` only | **No** |

### Testing Workflow Push Capability

```bash
git checkout -b test-workflow-push
echo "name: test" > .github/workflows/test.yml
git add .github/workflows/test.yml
git commit -m "test: workflow push"
git push -u origin test-workflow-push
# If this fails, auth lacks workflow permission
git checkout main
git branch -D test-workflow-push
```

---

## Machine Checklist

For each machine that needs to push:

- [ ] SSH key generated (`~/.ssh/id_ed25519`)
- [ ] Public key added to GitHub account
- [ ] Remote URLs use SSH format (`git@github.com:...`)
- [ ] `ssh -T git@github.com` succeeds
- [ ] Pre-commit hook installed
- [ ] Test push to main succeeds

---

## Troubleshooting

### "Permission denied (publickey)"

```bash
# Check ssh-agent is running
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Verify key is loaded
ssh-add -l

# Check key is on GitHub
cat ~/.ssh/id_ed25519.pub
# Compare with https://github.com/settings/keys
```

### "refusing to allow an OAuth App to create or update workflow"

Auth lacks `workflow` scope. Either:
1. Switch to SSH (recommended)
2. Run `gh auth refresh -h github.com -s workflow`

### "adding embedded git repository"

See "Nested Repository / Submodule Handling" above.
