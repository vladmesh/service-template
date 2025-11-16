FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip poetry

COPY services/tg_bot/pyproject.toml services/tg_bot/poetry.lock ./services/tg_bot/
ARG INSTALL_DEV_DEPS="false"
RUN cd services/tg_bot \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
        poetry install --with dev --no-root; \
    else \
        poetry install --without dev --no-root; \
    fi

COPY services/tg_bot ./services/tg_bot

CMD ["python", "services/tg_bot/src/main.py"]
