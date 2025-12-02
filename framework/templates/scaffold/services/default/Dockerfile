# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE=debian:stable-slim

FROM ${BASE_IMAGE} AS runtime
WORKDIR /app

# Копируем исходники (по умолчанию только src/). Расширьте при необходимости.
COPY src/ ./src/
COPY tests/ ./tests/

# TODO: установить зависимости сервиса. Для python/node/go замените инструкции ниже.
RUN echo "Configure build steps for __SERVICE_NAME__" && \
    mkdir -p /opt/__SERVICE_NAME__

# Переопределите команду запуска под конкретный стек.
CMD ["/bin/sh", "-c", "echo 'Define CMD for __SERVICE_NAME__' && sleep infinity"]
