# Changelog

All notable changes to ROXY will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive test suite with pytest
- Prometheus metrics integration
- Grafana dashboards for monitoring
- Type hints throughout codebase
- mypy configuration for type checking
- Resource limits for Docker services
- Health check script
- Backup and restore scripts
- Automated backup scheduling
- Retry logic with exponential backoff
- Circuit breaker pattern implementation
- API versioning support (/v1/* endpoints)
- OpenAPI 3.0 specification
- Comprehensive documentation (architecture, runbooks, API docs)
- Disaster recovery procedures

### Changed
- Authentication now mandatory (fail-fast if no token)
- Rate limiting enabled by default
- Security modules fail secure instead of silent
- Observability errors now logged properly (not silent)
- Enhanced error handling throughout

### Fixed
- ChromaDB healthcheck (uses Python instead of curl)
- n8n database initialization
- Silent error handling in security modules
- Duplicate function definitions in observability.py
- Mutable default arguments in function signatures

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
