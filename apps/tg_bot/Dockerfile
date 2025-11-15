FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip poetry

COPY apps/tg_bot/pyproject.toml apps/tg_bot/poetry.lock ./apps/tg_bot/
RUN cd apps/tg_bot \
    && poetry config virtualenvs.create false \
    && poetry install --no-root

COPY apps/tg_bot ./apps/tg_bot

CMD ["python", "apps/tg_bot/main.py"]
