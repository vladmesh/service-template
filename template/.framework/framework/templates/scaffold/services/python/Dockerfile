# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Копируйте сюда lock/requirements перед сборкой, когда появятся зависимости.
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY tests/ ./tests/

# TODO: Добавьте установку зависимостей/entrypoint.
CMD ["python", "-m", "src.app"]
