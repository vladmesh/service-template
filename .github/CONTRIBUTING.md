# Contributing & CI/CD

This repository ships with container-first developer tooling. The sections below document the
quality gates that run locally and in CI, together with the GitHub Secrets required by the
workflows.

## Local quality gates

The `Makefile` exposes a conventional set of commands:

```bash
make install  # pip install -e .[dev]
make lint     # ruff check .
make test     # pytest
```

For full fidelity with CI run the docker-compose test stack:

```bash
docker compose \
  -f infra/compose.base.yml \
  -f infra/compose.test.yml \
  --profile test \
  run --rm backend pytest -q
```

## GitHub Actions workflows

### `.github/workflows/pr.yml`

Runs on every pull request against `main` (and manually via `workflow_dispatch`). The job:

1. Copies `.env.example` to `.env` so that services referencing `env_file` boot without extra setup.
2. Builds the backend test image defined in `infra/compose.test.yml`.
3. Executes `ruff check` and `pytest` inside the backend container from the Compose test profile.
4. Tears down the stack to ensure clean layers for the next run.

### `.github/workflows/main.yml`

Triggered on pushes to `main` and on manual dispatch. The pipeline performs:

1. Matrix builds for the backend (mandatory) and the optional `frontend`/`tg-bot` images. Optional
   images are skipped automatically unless a Dockerfile is present.
2. Pushes tags `<IMAGE_PREFIX>-<service>:{latest,commit_sha}` to the configured registry.
3. (Optional) SSHes into the target server and runs `docker compose pull && docker compose up -d`
   using the compose files supplied through secrets.

Leave the deployment secrets empty to skip the remote step during experimentation.

## Required GitHub Secrets

| Secret | Required | Description |
| --- | :---: | --- |
| `REGISTRY_HOST` | ✅ | Registry hostname passed to `docker/login-action` (e.g. `ghcr.io`). |
| `REGISTRY_USERNAME` | ✅ | Username (or service account) that can push images. |
| `REGISTRY_PASSWORD` | ✅ | Token/password for the registry user. |
| `REGISTRY_IMAGE_PREFIX` | ✅ | Full image prefix (e.g. `ghcr.io/my-org/service-template`). The workflows append `-backend`, `-frontend`, etc. |
| `DEPLOY_HOST` | ⛔️* | SSH host for the deployment server. Leave empty to skip the deploy job. |
| `DEPLOY_PORT` | ⛔️ | SSH port; defaults to `22` if omitted. |
| `DEPLOY_USER` | ⛔️* | SSH username. |
| `DEPLOY_SSH_KEY` | ⛔️* | Private key with access to the server. |
| `DEPLOY_PROJECT_PATH` | ⛔️* | Absolute path on the server that contains the compose files. |
| `DEPLOY_COMPOSE_FILES` | ⛔️* | Space-separated list of compose files (e.g. `infra/compose.base.yml infra/compose.prod.yml`). |

`⛔️*` means the secret is required only when you want to run the deployment step. When
configuring the server remember to set environment variables such as `BACKEND_IMAGE` so that the
production stack pulls the freshly published tags.
