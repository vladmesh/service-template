# Spec Optional: Known Issues

Issues found during testing of simplification plan item 3 (specs optional).

## Functional

### ~~1. `services/tg_bot/spec/manifest.yaml` remains in standalone~~ FIXED

Added `rm -rf services/*/spec` to copier `_tasks` for standalone projects.

### ~~2. `shared/shared/http_client.py` remains in standalone~~ FIXED

Added `rm -f shared/shared/http_client.py` to copier `_tasks` for standalone projects.

### ~~3. `shared/shared/generated/schemas.py` is stale in full-stack after copier copy~~ FIXED

Added explicit warning in `generate.py` when `datamodel-code-generator` is unavailable: "schemas.py may be stale. Run `make generate-from-spec` in Docker to regenerate."

## ~~Cosmetic (Jinja whitespace)~~ ALL FIXED

### ~~4. main.py — up to 3 consecutive blank lines~~ FIXED

Replaced `{% endif -%}` with `{% endif %}` where `-%}` destroyed indentation or spacing. Adjusted surrounding blank lines to produce correct PEP 8 output in both standalone and full-stack modes.

### ~~5. ARCHITECTURE.md — `shared/` section renders empty without backend~~ FIXED

Wrapped entire `shared/` bullet in `{% if 'backend' in modules %}`. Changed `{% endif -%}` before `## Deployment` to `{% endif %}` to preserve section separation.

### ~~6. CONTRIBUTING.md — double blank lines after removed sections~~ FIXED

Applied `{% endif -%}` trimming on markdown sections (safe at column 0). Restructured conditional blocks.

### ~~7. ci.yml — triple blank line between steps~~ FIXED

Changed `{% endif -%}` to `{% endif %}` before indented YAML step to preserve 6-space indentation. Removed blank line to compensate.

### ~~8. Makefile — extra blank lines around conditional sections~~ FIXED

Removed if/else from lint target (framework is already graceful without specs). Changed `{% endif -%}` to `{% endif %}` for validate-specs/makemigrations blocks.
