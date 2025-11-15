# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY tests ./tests

RUN pip install --upgrade pip \
    && pip install -e .[dev]

EXPOSE 8000
CMD ["uvicorn", "apps.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
