# Spec Optional: Known Issues

Issues found during testing of simplification plan item 3 (specs optional).

## Functional

### 1. `services/tg_bot/spec/manifest.yaml` remains in standalone

Standalone tg_bot still has `services/tg_bot/spec/manifest.yaml`. This is a dead artifact — spec infrastructure shouldn't exist when there's no backend. Need either a copier task to remove it, or make the spec dir conditional in the template.

### 2. `shared/shared/http_client.py` remains in standalone

Contains `ServiceClient` (httpx-based HTTP client) used only by `BackendClient` in full-stack mode. Dead code for standalone bot, plus pulls httpx dependency. Should be conditional on backend module.

### 3. `shared/shared/generated/schemas.py` is stale in full-stack after copier copy

Copier task runs `framework.generate` locally (not in Docker). Since `datamodel-code-generator` is only installed in the tooling Docker image, `SchemasGenerator` is skipped and `schemas.py` remains as a template placeholder (`# THIS FILE IS GENERATED...`), not actual Pydantic models. In Docker CI it gets regenerated correctly, but first local `make lint` may be confusing.

## Cosmetic (Jinja whitespace)

### 4. main.py — up to 3 consecutive blank lines

11 occurrences in standalone, 17 in full-stack. Jinja `{% if %}` blocks leave extra blank lines when their content is excluded. PEP 8 allows max 2 at top-level; ruff E303 catches triples. Fix: use `{%-` / `-%}` trimming on conditional blocks.

### 5. ARCHITECTURE.md — `shared/` section renders empty without backend

```markdown
- `shared/`:

- `templates/`: Jinja2 templates...
```

The two nested items (spec, generated) are removed and `shared/` becomes an empty bullet with a dangling dash. The whole `shared/` bullet should be conditional or restructured.

### 6. CONTRIBUTING.md — double blank lines after removed sections

Lines 33-34 after "Modifying the API" section removal, and around "Read-Only Zones". Fix: Jinja whitespace trimming.

### 7. ci.yml — triple blank line between steps

Between "Prepare environment files" and "Run linters" where spec steps were removed.

### 8. Makefile — extra blank lines around conditional sections

Around `lint:` target and between sections after removed `validate-specs` / `lint-specs` targets.
