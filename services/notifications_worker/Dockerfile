# syntax=docker/dockerfile:1.7
ARG INSTALL_DEV_DEPS="false"

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

FROM base AS deps
ARG INSTALL_DEV_DEPS
RUN pip install --no-cache-dir poetry

COPY services/notifications_worker/pyproject.toml services/notifications_worker/poetry.lock* ./services/notifications_worker/
RUN cd services/notifications_worker \
    && poetry config virtualenvs.create false \
    && if [ -f poetry.lock ]; then poetry lock; fi \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    poetry install --with dev --no-root; \
    else \
    poetry install --without dev --no-root; \
    fi

FROM base AS runtime
COPY --from=deps /usr/local /usr/local
COPY services/notifications_worker ./services/notifications_worker

CMD ["python", "-m", "services.notifications_worker.src.app"]
