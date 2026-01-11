# Changelog

All notable changes to ROXY will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0-rc2] - 2026-01-10

### Fixed
- Remediation hint in /ready endpoint now provides actionable guidance
  - Fixed invalid string join syntax
  - Lists all unreachable pools with their ports
  - References RUNBOOK.md section 3 for remediation steps

### Changed
- Updated RUNBOOK.md and gateA contract to match runtime behavior

### Removed
- 217 stale files: transient reports, legacy/quarantined code

## [1.0.0-rc1] - 2026-01-10

### Added
- `/ready` endpoint for production readiness (200 if all pools OK, 503 with error details)
- `/version` endpoint with git SHA, build time, platform info
- `wait-for-ready.sh` script (replaces manual sleeps)
- `prod_deploy.sh` Gate0 one-command deploy script
- Gate scripts: gateA_resilience, gateB_overload, gateE_observability
- Prometheus metrics: `roxy_pool_reachable`, `roxy_pool_latency_ms`, `roxy_ready_checks_total`
- RUNBOOK.md operator documentation
- PROD_CUTOVER_PLAN.md with SLOs and gate definitions
- Pool identity module (`pool_identity.py`) - single source of truth for pool config
- Deprecation warnings for BIG/FAST pool aliases

### Changed
- `/health` vs `/ready` semantics clarified (health=alive, ready=production-ready)
- Benchmark service uses canonical pool names from pool_identity module

## [1.0.0] - 2026-01-02

### Added
- Initial release
- ROXY Core HTTP IPC service
- Command routing (git, OBS, RAG, system)
- Security hardening (input sanitization, PII detection)
- Rate limiting
- Basic observability
- ChromaDB integration for RAG
- Ollama integration for LLM
- Docker Compose infrastructure
- Systemd service configuration

[Unreleased]: https://github.com/yourusername/roxy/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/roxy/releases/tag/v1.0.0
