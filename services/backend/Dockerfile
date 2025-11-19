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
COPY shared ./shared
COPY services/backend/pyproject.toml services/backend/poetry.lock ./services/backend/
RUN cd services/backend \
    && poetry config virtualenvs.create false \
    && poetry lock \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    poetry install --with dev --no-root; \
    else \
    poetry install --without dev --no-root; \
    fi

FROM base AS runtime
COPY --from=deps /usr/local /usr/local
COPY services/backend ./services/backend
COPY services/backend/README.md ./README.md
COPY shared ./shared

EXPOSE 8000
CMD ["uvicorn", "services.backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
