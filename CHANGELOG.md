# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Restructuring Complete**: Clear separation between framework and product abstraction levels
  - Created `docs/` directory for framework internal documentation
  - Created `template/` directory containing all product templates
  - Created `.framework/` directory in generated products (hidden, contains framework runtime)
  - Created `template/tests/` with product test scaffolding (`conftest.py.jinja`, `integration/`)
  - Created `scripts/sync-framework-to-template.sh` for framework synchronization
  - Created `scripts/check-framework-sync.sh` for CI verification
  - Added `make check-sync` command to verify framework/template synchronization
  - Added CI check to ensure framework code is synced before merging

### Changed
- **Root README.md**: Now clearly separates framework development from product usage workflows
- **Makefile**: Updated with `check-sync` command and improved help documentation
- **docs/ARCHITECTURE.md**: Updated to reflect `.framework/` structure in generated products
- **GitHub Actions CI**: Added framework sync verification step
- **docs/RESTRUCTURING_PLAN.md**: Marked as COMPLETED (all 10 phases done)

### Fixed
- Framework tests are no longer copied to generated products (copier `_subdirectory` ensures clean separation)

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
