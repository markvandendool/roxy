# ROXY Vault — Secrets Management

**WARNING: This directory contains sensitive credentials.**

## Structure

```
vault/
├── .age-key          # Master encryption key (NEVER COMMIT)
├── .age-key.pub      # Public key
├── api_keys/         # Platform API keys
├── tokens/           # Auth tokens
│   └── roxy_secret.token
├── creds/            # Service credentials
│   ├── monetization_credentials.json
│   └── automation_credentials.json
└── secrets/          # Age-encrypted secrets
    └── .index.age
```

## Security Rules

1. **NEVER** commit this directory to git
2. **NEVER** echo, cat, or print credentials
3. **NEVER** share credentials in logs or output
4. Use `age` for encryption: `age -e -R .age-key.pub < secret.txt > secret.age`
5. Decrypt with: `age -d -i .age-key < secret.age`

## Backup

Credentials are backed up to age-encrypted format in `secrets/`

## Original Locations (Kept for Compatibility)

The following files still exist at original locations for testing:
- `~/.roxy/secret.token` (symlinked)
- `~/.roxy/workshops/monetization/.credentials.json`
- `~/.roxy/workshops/monetization/automation/.credentials.json`

**DO NOT DELETE** originals until migration is verified.

---
*Generated: 2026-01-10 by Project SKYBEAM*
