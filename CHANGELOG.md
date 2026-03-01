# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-01

### Added
- `.dockerignore` in template — prevents host `.venv/` from contaminating Docker builds
- Frontend service in `compose.base.yml` — `compose.prod.yml` extends now works for full config
- Conditional broker in `lifespan.py.jinja` — backend-only no longer requires `REDIS_URL`
- 10 new regression tests in 3 classes:
  - `TestDockerReadiness`: dockerignore, login shell, lifespan broker, compose prod/dev validation, health assertion match
  - `TestCIWorkflowCorrectness`: standalone CI cleanup
  - `TestFormattingQuality`: services.yml blank lines
- Standalone tg_bot tests (`TestStandaloneGeneration`) — 7 tests for `modules=tg_bot`
- `@pytest.mark.slow` for `make setup`/`make lint` integration tests
- `make test-copier-slow` target for slow tests
- Copier tests re-enabled in pre-push hook and CI

### Fixed
- `bash -lc` → `bash -c` in `compose.dev.yml` — login shell was resetting Docker PATH
- Health integration test assertion `"healthy"` → `"ok"` to match actual endpoint
- CI Clean up step wrapped in backend conditional — no longer runs for standalone
- `services.yml.jinja` Jinja whitespace trimming — no more excessive blank lines
- Copier tests use `.venv/bin/copier` and `.venv/bin/ruff` instead of bare commands
- Copier test fixtures refactored to session-scoped (4 copier runs per session instead of ~40)

### Changed
- `lifespan.py` renamed to `lifespan.py.jinja` (now conditionally includes broker code)
- Copier tests fully rewritten — 68 fast + 5 slow tests (was 55 broken/skipped)

## [0.1.0] - Previous Version

### Added
- Initial spec-first framework with code generation
- Modular service selection (backend, tg_bot, notifications, frontend)
- Copier-based project generation
- FastAPI + PostgreSQL backend module
- Telegram bot with FastStream
- Notifications worker
- Domain operation specifications
- Client generation from manifests
- Event-driven architecture support
