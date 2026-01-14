# ROXY Rebuild Runbook (SSD Loss / Fresh Host)

**Audience:** Ops, Chief, automation agents
**Goal:** Rebuild a Linux ROXY host to a known-good, reproducible state

## Assumptions
- You have access to the roxy.git repo.
- You have a secure backup of `$ROXY_ROOT/etc` and `$ROXY_ROOT/var`.
- You can run user systemd services.

## Canonical Layout
```
$ROXY_ROOT/
  src/   # Git repo (roxy.git)
  etc/   # Config + secrets (not Git)
  var/   # Runtime data (not Git)
  log/   # Logs (optional)
```

Default Linux root: `/home/mark/.roxy`

## 0) Bootstrap host prerequisites
Install required packages and runtime dependencies.

If you already have a bootstrap script:
```
$ROXY_ROOT/src/ops/bootstrap.sh
```

If not, follow your standard OS provisioning checklist (Python, Bun, systemd user services, GPU drivers, etc.).

## 1) Create ROXY root layout
```
mkdir -p /home/mark/.roxy/{src,etc,var,log}
```

## 2) Restore code (Git)
```
git clone https://github.com/markvandendool/roxy.git /home/mark/.roxy/src
```

Optional: checkout tagged release for production:
```
cd /home/mark/.roxy/src
git checkout <tag>
```

## 3) Restore config + secrets
Restore encrypted backup into `$ROXY_ROOT/etc`:
```
rsync -a /backup/roxy/etc/ /home/mark/.roxy/etc/
```

Do **not** commit these files.

## 4) Restore runtime data
Restore runtime data into `$ROXY_ROOT/var`:
```
rsync -a /backup/roxy/var/ /home/mark/.roxy/var/
```

If no runtime backup exists, the system can still boot, but RAG indexes and memory will need regeneration.

## 5) Align systemd to ROXY_ROOT
Ensure all units reference `$ROXY_ROOT/src` and load env from `$ROXY_ROOT/etc`.

Example env drop-in:
```
mkdir -p ~/.config/systemd/user/roxy-core.service.d
cat > ~/.config/systemd/user/roxy-core.service.d/00-root.conf <<'EOT'
[Service]
Environment=ROXY_ROOT=/home/mark/.roxy
EnvironmentFile=/home/mark/.roxy/etc/roxy.env
WorkingDirectory=/home/mark/.roxy/src
EOT
```

Reload and start services:
```
systemctl --user daemon-reload
systemctl --user enable --now roxy-core
```

## 6) Health gates
Run the doctor command:
```
/home/mark/.roxy/src/scripts/stack_doctor.sh
```

For automation:
```
/home/mark/.roxy/src/scripts/stack_doctor.sh --json --fast > /tmp/stack_doctor.json
```

## 7) Optional: Rebuild RAG index
If runtime data was not restored:
```
source /home/mark/.roxy/src/venv/bin/activate
python /home/mark/.roxy/src/bootstrap_rag.py /home/mark/.roxy/src/brain
```

## 8) Verify services
- `curl http://127.0.0.1:8766/ready`
- `curl http://127.0.0.1:3847/health/orchestrator`
- `ss -ltnp | rg ':11434|:11435|:3847'`

## Appendix: Backup Strategy
- Code: Git tags.
- Config: encrypted backups of `$ROXY_ROOT/etc`.
- Runtime: periodic backups of `$ROXY_ROOT/var`.

