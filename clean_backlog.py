import re

with open('docs/backlog.md', 'r') as f:
    content = f.read()

# Split by headers (### )
parts = re.split(r'(?=\n### )', content)

new_parts = []
for part in parts:
    if part.strip() == '':
        continue
        
    # Check if the section contains **Status**: DONE
    if '**Status**: DONE' in part:
        print(f"Removing: {part.strip().split('\n')[0]}")
        continue
    new_parts.append(part)

new_content = "".join(new_parts)

# Add new tasks
new_tasks = """
## Infrastructure Audit Fixes

### Reduce Docker Build Context with .dockerignore

**Status**: TODO
**Priority**: HIGH

**Description**: Create a `.dockerignore` file in the root to prevent copying unnecessary files (like `.venv`, `__pycache__`, `.git`) into the Docker build context. This will significantly reduce the build context size from ~50MB to ~5MB.

### Update Frontend Dockerfile to use npm ci

**Status**: TODO
**Priority**: MEDIUM

**Description**: Replace `npm install` with `npm ci` in `services/frontend/Dockerfile` to ensure strict installation from `package-lock.json` and avoid unintentional dependency updates during build.

### Remove poetry lock from Backend Dockerfile

**Status**: TODO
**Priority**: HIGH

**Description**: The current `services/backend/Dockerfile` runs `poetry lock`, which can generate different lock files upon each build if dependencies update. This breaks build reproducibility. We should use the existing lock file and just run `poetry install`.

### Add Cache Mounts to Dockerfiles

**Status**: TODO
**Priority**: LOW

**Description**: Use `--mount=type=cache,target=/root/.cache/pip` and `/root/.cache/pypoetry` in Tooling and Backend Dockerfiles to speed up rebuilds.

### Audit Scaffold Templates

**Status**: TODO
**Priority**: LOW

**Description**: Review templates in `framework/templates/scaffold/services/` to ensure they use the latest best practices adopted by main services.

## Simplification & Unification Tasks

### Tooling Removal: Migrate to uv and Run Tools Natively

**Status**: TODO
**Priority**: HIGH

**Description**: As discussed in `brainstorm-tooling-removal.md`, remove the `tooling` container to avoid Docker-in-Docker complexities for agents. 
- Migrate `pyproject.toml` from Poetry to `uv` (PEP 621).
- Run linters (`ruff`, `mypy`) and unit tests natively without docker using `uv run`.
- Update Makefile and CI workflows accordingly.

### Unified Handlers: Error Handling Strategy

**Status**: TODO
**Priority**: MEDIUM

**Description**: Formulate a strategy for handling errors in event handlers. Should we use Dead Letter Queues (DLQ), publish an error event (`events.publish_on_error`), or implement retries with exponential backoff?

### Unified Handlers: Transactional Outbox Pattern

**Status**: IDEA
**Priority**: LOW

**Description**: Currently, events are published directly after DB writes. Consider implementing the Transactional Outbox pattern to avoid the dual write problem and ensure reliable event publishing.

### Unified Handlers: Event Channel Naming Convention

**Status**: TODO
**Priority**: LOW

**Description**: Standardize the format for event channel names (e.g., `<entity>.<action>` like `user.created`).
"""

new_content += new_tasks

with open('docs/backlog.md', 'w') as f:
    f.write(new_content)
