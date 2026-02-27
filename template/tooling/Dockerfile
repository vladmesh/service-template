# syntax=docker/dockerfile:1.7
FROM python:3.11-slim AS tooling

# Accept build args for user/group IDs to match host user
ARG USER_ID=1000
ARG GROUP_ID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PATH="/home/appuser/.local/bin:${PATH}"

# Install system dependencies including Docker CLI for integration tests
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    make \
    curl \
    ca-certificates \
    gnupg && \
    # Add Docker's official GPG key and repository
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# Create user with matching UID/GID to host user
RUN groupadd -g ${GROUP_ID} appuser && \
    useradd -m -u ${USER_ID} -g appuser appuser

WORKDIR /workspace

RUN pip install --no-cache-dir --root-user-action=ignore --disable-pip-version-check \
    ruff==0.14.5 \
    xenon==0.9.1 \
    mypy==1.10.0 \
    pytest==8.2.0 \
    pytest-cov==4.1.0 \
    types-PyYAML \
    PyYAML \
    datamodel-code-generator[http] \
    jinja2 \
    copier==9.4.1

# Switch to non-root user
USER appuser

CMD ["bash"]
