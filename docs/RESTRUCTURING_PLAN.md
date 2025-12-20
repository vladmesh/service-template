# Restructuring Plan: Separation of Abstraction Levels

> **Status**: COMPLETED  
> **Created**: 2025-12-20  
> **Completed**: 2025-12-20  
> **Goal**: Clear separation between framework internals, framework interface, and generated product code

---

## Problem Statement

Current project structure mixes several abstraction levels in the root directory:
- Framework documentation (MANIFESTO.md, ARCHITECTURE.md)
- Product templates (README.md.jinja, AGENTS.md.jinja)
- Framework code (framework/)
- Product modules (services/)
- Framework configs (ruff.toml, mypy.ini) that also serve as product templates

This creates confusion for both framework developers and framework users.

---

## Abstraction Levels

### Level 1: Framework Internals
**Audience**: Framework developers only

Includes:
- Framework source code (generators, spec loaders)
- Framework tests (unit tests for generators, copier integration tests)
- Internal documentation (MANIFESTO, ARCHITECTURE, backlog)
- Framework CI/CD (.github/workflows for testing the template)
- Framework linter configs

**Should NOT go into generated products.**

### Level 2: Framework Interface
**Audience**: Framework users (product developers)

Includes:
- README with usage instructions (`copier copy`, `copier update`)
- Available modules list
- Makefile commands for template development

**Lives in framework repo root, NOT copied to products.**

### Level 3: Product Template
**Audience**: Product developers (via Copier)

Includes:
- Product README template
- Product Makefile template
- Product CI/CD templates
- Product linter configs
- Product test scaffolding

**Copied into generated products.**

### Level 4: Modules (Batteries)
**Audience**: Both framework devs and product developers

Includes:
- backend (FastAPI + PostgreSQL)
- tg_bot (Telegram bot + FastStream)
- notifications_worker (Event-driven worker)
- frontend (Node.js placeholder)

**Special case**: Lives in framework repo for development, copied as part of product template. These are pre-built, tested service implementations that ship with generated projects.

---

## Target Structure

### Framework Repository

```
service-template/
│
├── README.md                       # Level 2: Framework usage docs
│                                   # "How to create a project with Copier"
│                                   # "How to update infrastructure"
│
├── copier.yml                      # Copier config (points to template/)
│
├── docs/                           # Level 1: Framework internal docs
│   ├── MANIFESTO.md                # Philosophy
│   ├── ARCHITECTURE.md             # How the framework works
│   ├── DEVELOPMENT.md              # How to develop the framework
│   ├── RESTRUCTURING_PLAN.md       # This document
│   └── backlog.md                  # Framework roadmap
│
├── framework/                      # Level 1: Framework source code
│   ├── __init__.py
│   ├── generators/                 # Code generators
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── routers.py
│   │   ├── clients.py
│   │   ├── events.py
│   │   └── protocols.py
│   ├── templates/codegen/          # Jinja templates for code generation
│   │   ├── schemas.py.j2
│   │   ├── router.py.j2
│   │   ├── client.py.j2
│   │   └── ...
│   ├── spec/                       # Spec loaders and validators
│   │   ├── loader.py
│   │   └── operations.py
│   ├── lib/                        # Utilities
│   ├── openapi/                    # OpenAPI generator
│   ├── sync_services.py            # Service scaffolding
│   └── generate.py                 # Main entry point
│
├── tests/                          # Level 1: Framework tests
│   ├── unit/                       # Unit tests for generators
│   │   └── test_generators.py
│   ├── copier/                     # Copier integration tests
│   │   └── test_template_generation.py
│   └── conftest.py
│
├── Makefile                        # Framework Makefile
│                                   # make test, make lint, make test-template
├── ruff.toml                       # Framework linter config
├── mypy.ini                        # Framework type checker config
├── pytest.ini                      # Framework test config
│
├── .github/                        # Level 1: Framework CI
│   └── workflows/
│       ├── ci.yml                  # Test framework code
│       └── test-template.yml       # Test template generation
│
└── template/                       # Level 3 + 4: Product template
    │
    ├── README.md.jinja             # → product README.md
    ├── AGENTS.md.jinja             # → product AGENTS.md
    ├── CONTRIBUTING.md.jinja       # → product CONTRIBUTING.md
    ├── Makefile.jinja              # → product Makefile
    ├── services.yml.jinja          # → product services.yml
    ├── .env.example.jinja          # → product .env.example
    │
    ├── ruff.toml                   # → product ruff.toml (may differ from framework)
    ├── mypy.ini                    # → product mypy.ini
    ├── pytest.ini                  # → product pytest.ini
    ├── .coveragerc                 # → product .coveragerc
    │
    ├── .github/                    # → product CI
    │   └── workflows/
    │       └── ci.yml.jinja
    │
    ├── .framework/                 # → product .framework/ (hidden)
    │   ├── __init__.py
    │   ├── generators/             # Copy of framework/generators/
    │   ├── templates/codegen/      # Copy of framework/templates/codegen/
    │   ├── spec/                   # Copy of framework/spec/
    │   ├── lib/
    │   ├── openapi/
    │   ├── sync_services.py
    │   └── generate.py
    │
    ├── shared/
    │   ├── spec/                   # Example specs
    │   │   ├── models.yaml
    │   │   └── events.yaml
    │   └── shared/
    │       └── generated/          # Generated schemas, events
    │
    ├── services/                   # Level 4: Modules
    │   ├── backend/
    │   │   ├── AGENTS.md
    │   │   ├── Dockerfile
    │   │   ├── spec/
    │   │   │   ├── users.yaml
    │   │   │   └── manifest.yaml
    │   │   └── src/
    │   │       ├── app/
    │   │       ├── controllers/
    │   │       └── generated/
    │   ├── tg_bot/
    │   ├── notifications_worker/
    │   └── frontend/
    │
    ├── infra/
    │   ├── docker-compose.yml.jinja
    │   └── ...
    │
    └── tests/                      # Product test scaffolding
        ├── conftest.py.jinja
        └── integration/
```

### Generated Product

After `copier copy gh:org/service-template ./my-project`:

```
my-project/
│
├── README.md                       # From README.md.jinja
├── AGENTS.md                       # From AGENTS.md.jinja
├── CONTRIBUTING.md
├── Makefile                        # Product commands
├── services.yml
├── .env.example
│
├── ruff.toml                       # Product linter config
├── mypy.ini
├── pytest.ini
├── .coveragerc
│
├── .github/workflows/ci.yml        # Product CI
│
├── .framework/                     # Hidden from user
│   ├── generators/
│   ├── templates/codegen/
│   ├── spec/
│   └── generate.py
│
├── shared/
│   ├── spec/                       # 👀 User edits specs here
│   │   ├── models.yaml
│   │   └── events.yaml
│   └── shared/generated/           # Auto-generated
│
├── services/
│   ├── backend/
│   │   ├── spec/                   # 👀 User edits domain specs
│   │   └── src/
│   │       ├── controllers/        # 👀 User writes business logic
│   │       └── generated/          # Auto-generated
│   └── ...
│
├── infra/
└── tests/                          # 👀 User writes tests
```

---

## Future Enhancement: CLI Wrapper

Currently, `make generate-from-spec` calls Python scripts directly. Future goal is to wrap this in a Django-style CLI:

```bash
# Current
make generate-from-spec

# Future (aspirational)
stf generate          # Generate all code from specs
stf sync-services     # Sync services.yml with compose files
stf new-service       # Interactive service creation
stf validate-specs    # Validate YAML specs
```

This CLI would be installed via pip (`pip install service-template-framework`) or bundled in `.framework/cli.py`.

**Note**: This is a separate initiative, tracked in backlog. Current plan focuses on structure only.

---

## Implementation Plan

### Phase 1: Create docs/ Directory Structure
**Complexity**: Low  
**Risk**: None

- [x] Create `docs/` directory
- [x] Move `MANIFESTO.md` → `docs/MANIFESTO.md`
- [x] Move `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- [x] Move `INFRA_AUDIT.md` → `docs/INFRA_AUDIT.md`
- [x] Move `backlog.md` → `docs/backlog.md`
- [x] Create `docs/DEVELOPMENT.md` with framework development instructions
- [x] Update all internal cross-references

### Phase 2: Create template/ Directory
**Complexity**: Medium  
**Risk**: Medium (Copier paths change)

- [x] Create `template/` directory
- [x] Move all `.jinja` template files into `template/`:
  - `README.md.jinja` → `template/README.md.jinja`
  - `AGENTS.md.jinja` → `template/AGENTS.md.jinja`
  - `ARCHITECTURE.md.jinja` → `template/ARCHITECTURE.md.jinja`
  - `CONTRIBUTING.md` → `template/CONTRIBUTING.md`
  - `Makefile.jinja` → `template/Makefile.jinja`
  - `services.yml.jinja` → `template/services.yml.jinja`
  - `.env.example.jinja` → `template/.env.example.jinja`
  - `{{ _copier_conf.answers_file }}.jinja` → `template/`
- [x] Move/copy linter configs to `template/`:
  - Copy `ruff.toml` → `template/ruff.toml`
  - Copy `mypy.ini` → `template/mypy.ini`
  - Copy `pytest.ini` → `template/pytest.ini`
  - Copy `.coveragerc` → `template/.coveragerc`
- [x] Update `copier.yml`:
  - Add `_subdirectory: template`
  - Update all path references
- [x] Run copier tests to verify generation still works

### Phase 3: Move Modules to template/
**Complexity**: Medium  
**Risk**: Medium (affects current development workflow)

- [x] Move `services/` → `template/services/`
- [x] Move `shared/` → `template/shared/`
- [x] Move `infra/` → `template/infra/`
  - *Note*: Converted `compose.*.yml` to Jinja templates (`.yml.jinja`) to eliminate dependency on `sync-services` script during project generation.
- [x] Move `tooling/` → `template/tooling/`
- [x] Update all paths in:
  - `copier.yml` (tasks, skip patterns)
  - Test files
  - GitHub workflows
- [x] Run full test suite

### Phase 4: Create .framework/ in template
**Complexity**: High  
**Risk**: High (core functionality)

- [x] Create `template/.framework/` directory
- [x] Copy framework code to template:
  - `framework/generators/` → `template/.framework/generators/`
  - `framework/templates/codegen/` → `template/.framework/templates/codegen/`
  - `framework/spec/` → `template/.framework/spec/`
  - `framework/lib/` → `template/.framework/lib/`
  - `framework/openapi/` → `template/.framework/openapi/`
  - `framework/sync_services.py` → `template/.framework/sync_services.py`
  - `framework/generate.py` → `template/.framework/generate.py`
  - `framework/compose_sync.py` → `template/.framework/compose_sync.py`
  - `framework/enforce_spec_compliance.py` → `template/.framework/enforce_spec_compliance.py`
- [x] Update `template/Makefile.jinja` to call `.framework/` instead of `framework/`
- [x] Ensure Python imports work with `.framework/` path
- [x] Run copier tests with generated project
- [x] Verify `make generate-from-spec` works in generated project

### Phase 5: Create Product CI Templates
**Complexity**: Medium  
**Risk**: Low

- [x] Create `template/.github/` directory
- [x] Move/adapt CI workflows:
  - Create `template/.github/workflows/ci.yml.jinja` for product CI
  - Keep `.github/workflows/` in root for framework CI
- [x] Update workflow templates to use correct paths
- [x] Add test for CI workflow generation

### Phase 6: Create Product Test Scaffolding
**Complexity**: Low  
**Risk**: Low

- [x] Create `template/tests/` directory structure
- [x] Create `template/tests/conftest.py.jinja`
- [x] Create `template/tests/integration/` placeholder
- [x] Ensure copier doesn't copy framework's `tests/` to product

### Phase 7: Update Framework Root
**Complexity**: Low  
**Risk**: Low

- [x] Rewrite root `README.md` as framework interface documentation:
  - Quick start with Copier
  - Available modules
  - Link to `docs/` for internals
- [x] Update root `Makefile` for framework-specific commands:
  - `make test` → run framework tests
  - `make lint` → lint framework code
  - `make test-template` → test copier generation
  - Remove product-specific commands
- [x] Update `.github/workflows/` for framework CI only
- [x] Clean up root directory (remove any remaining template files)

### Phase 8: Sync Script for .framework/
**Complexity**: Medium  
**Risk**: Low

Since `framework/` and `template/.framework/` will have identical code, create a sync mechanism:

- [x] Create `scripts/sync-framework-to-template.sh`
- [x] Add `make sync-framework` command
- [x] Add CI check that `framework/` and `template/.framework/` are in sync
- [x] Document in `docs/DEVELOPMENT.md`

Alternative approach: Use symlinks (not recommended due to Git/Copier compatibility issues)

### Phase 9: Update Documentation
**Complexity**: Low  
**Risk**: None

- [x] Update `docs/ARCHITECTURE.md` with new structure
- [x] Update `template/AGENTS.md.jinja` to reflect `.framework/` location
- [x] Update `template/README.md.jinja` with product-specific instructions
- [x] Create `docs/DEVELOPMENT.md` for framework contributors
- [x] Update this plan with "COMPLETED" status

### Phase 10: Final Verification
**Complexity**: Low  
**Risk**: None

- [x] Run full framework test suite
- [x] Run copier generation tests
- [x] Manually test `copier copy . /tmp/test-project`
- [x] Verify generated project:
  - `make lint` works
  - `make test` works
  - `make generate-from-spec` works
  - `make dev-start` works
- [x] Update CHANGELOG/release notes

---

## Migration Considerations

### Breaking Changes

1. **Copier update for existing projects**: Projects generated before this change will have `framework/` instead of `.framework/`. Need migration guide or Copier migration task.

2. **Path changes in Makefile**: Product Makefile will reference `.framework/` instead of `framework/`.

3. **Import paths**: If any product code imports from `framework`, it will break. Need to audit and update.

### Rollback Plan

If issues arise:
1. Revert the `template/` directory creation
2. Keep framework code in root
3. Document the attempt in backlog for future iteration

---

## Success Criteria

- [x] Framework repo clearly separates internal docs from user-facing docs
- [x] `template/` directory contains everything that goes into generated products
- [x] Generated products have `.framework/` directory (hidden)
- [x] All tests pass (framework + copier)
- [x] Generated project `make generate-from-spec` works
- [x] No confusion about which files are for framework vs product

---

## Open Questions

1. **Symlinks vs Copy**: Should `template/.framework/` be a symlink to `framework/` or a copy? 
   - **Decision**: Copy with sync script (safer for Git/Copier)

2. **Framework updates**: When framework code changes, how do existing products update `.framework/`?
   - **Current**: `copier update` should handle this
   - **Future**: Could add `make update-framework` command

3. **CLI wrapper priority**: Should we implement CLI before or after restructure?
   - **Decision**: After. Structure first, CLI is separate initiative.

4. **Naming**: Is `.framework/` the best name? Alternatives:
   - `.stf/` (service-template-framework)
   - `.codegen/`
   - `.tooling/`
   - **Decision**: `.framework/` is clear and self-documenting

---

## References

- [Current backlog](./backlog.md)
- [MANIFESTO](./MANIFESTO.md) - Philosophy driving these decisions
- [ARCHITECTURE](./ARCHITECTURE.md) - Current technical architecture
