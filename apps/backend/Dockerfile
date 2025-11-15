# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip poetry

COPY apps/backend/pyproject.toml apps/backend/poetry.lock ./apps/backend/

ARG INSTALL_DEV_DEPS="false"
RUN cd apps/backend \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --without dev --no-root; \
    fi

COPY README.md ./
COPY apps ./apps
COPY tests ./tests

EXPOSE 8000
CMD ["uvicorn", "apps.backend.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
