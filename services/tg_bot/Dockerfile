FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip poetry

# Copy only shared metadata and create minimal package structure for editable install
COPY shared/pyproject.toml ./shared/pyproject.toml
# Create minimal package structure so poetry can install in editable mode
RUN mkdir -p ./shared/shared && touch ./shared/shared/__init__.py

COPY services/tg_bot/pyproject.toml services/tg_bot/poetry.lock ./services/tg_bot/
ARG INSTALL_DEV_DEPS="false"
RUN cd services/tg_bot \
    && poetry config virtualenvs.create false \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then \
    poetry install --with dev --no-root; \
    else \
    poetry install --without dev --no-root; \
    fi

# Copy actual shared code after dependency installation (changes won't invalidate poetry install cache)
COPY shared/shared ./shared/shared
COPY services/tg_bot ./services/tg_bot

CMD ["python", "services/tg_bot/src/main.py"]
