# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS tooling

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /workspace

RUN pip install --no-cache-dir \
    ruff==0.14.5 \
    xenon==0.9.1 \
    mypy==1.10.0 \
    pytest==8.2.0 \
    types-PyYAML \
    PyYAML \
    datamodel-code-generator[http] \
    jinja2 \
    poetry

# Copy only shared metadata and create minimal package structure for editable install
COPY shared/pyproject.toml /shared/pyproject.toml
# Create minimal package structure so poetry can install in editable mode
RUN mkdir -p /shared/shared && touch /shared/shared/__init__.py

COPY services/backend/pyproject.toml services/backend/poetry.lock /tmp/backend/
RUN cd /tmp/backend \
    && poetry lock \
    && poetry install --with dev --no-root

COPY services/tg_bot/pyproject.toml services/tg_bot/poetry.lock /tmp/tg_bot/
RUN cd /tmp/tg_bot \
    && poetry install --with dev --no-root

# Copy actual shared code after all dependency installations (changes won't invalidate poetry install cache)
COPY shared/shared /shared/shared

CMD ["bash"]
