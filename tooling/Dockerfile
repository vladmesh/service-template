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

CMD ["bash"]
