# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY src/ ./src/
COPY tests/ ./tests/

EXPOSE 8000

LABEL service="__SERVICE_NAME__"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
