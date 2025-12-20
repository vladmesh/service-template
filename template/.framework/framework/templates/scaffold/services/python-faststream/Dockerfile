# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/

LABEL service="__SERVICE_NAME__"

CMD ["python", "src/main.py"]
