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
    ruff==0.1.6 \
    mypy==1.7.1 \
    pytest==7.4.3 \
    types-PyYAML \
    PyYAML \
    datamodel-code-generator[http] \
    jinja2 \
    poetry

COPY services/backend/pyproject.toml services/backend/poetry.lock /tmp/backend/
RUN cd /tmp/backend \
    && poetry install --with dev --no-root

COPY services/tg_bot/pyproject.toml services/tg_bot/poetry.lock /tmp/tg_bot/
RUN cd /tmp/tg_bot \
    && poetry install --with dev --no-root

CMD ["bash"]
