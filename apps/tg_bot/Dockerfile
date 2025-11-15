FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip poetry

COPY apps/tg_bot/pyproject.toml apps/tg_bot/poetry.lock ./apps/tg_bot/
ARG INSTALL_DEV_DEPS="false"
RUN cd apps/tg_bot \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --without dev --no-root; \
    fi

COPY apps/tg_bot ./apps/tg_bot

CMD ["python", "apps/tg_bot/main.py"]
