# Spec Optional: Known Issues

Issues found during testing of simplification plan item 3 (specs optional).

## Functional

### ~~1. `services/tg_bot/spec/manifest.yaml` remains in standalone~~ FIXED

Added `rm -rf services/*/spec` to copier `_tasks` for standalone projects.

### ~~2. `shared/shared/http_client.py` remains in standalone~~ FIXED

Added `rm -f shared/shared/http_client.py` to copier `_tasks` for standalone projects.

### ~~3. `shared/shared/generated/schemas.py` is stale in full-stack after copier copy~~ FIXED

Added explicit warning in `generate.py` when `datamodel-code-generator` is unavailable: "schemas.py may be stale. Run `make generate-from-spec` in Docker to regenerate."

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
