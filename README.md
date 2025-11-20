# Service Template Framework

A rigid, spec-first, modular framework for building AI-Agent-ready microservices.

> **Start here:** Read the [MANIFESTO](MANIFESTO.md) to understand the philosophy behind this project.

## 🚀 Quick Start

1.  **Clone & Setup**
    ```bash
    cp .env.example .env
    make dev-start
    ```

2.  **Development Workflow**
    - **Add Service:** Edit `services.yml` -> `make sync-services create`
    - **Update API:** Edit `shared/spec/*.yaml` -> `make generate-from-spec`
    - **Test:** `make tests`

## 📚 Documentation

- **[MANIFESTO.md](MANIFESTO.md)**: The core philosophy.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: How it works under the hood.
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Coding standards and rules.
- **[AGENTS.md](AGENTS.md)**: Navigation guide for AI agents.

## 🔮 Roadmap

We are evolving from a simple template to a comprehensive agent-native ecosystem.

1.  **Current:** "Clone & Own" — simple git-based workflow.
2.  **Near Future:** **Updatable Template** — switch to `copier` to allow pulling infrastructure updates from upstream.
3.  **Vision:** **Agent-First Interface** — an MCP (Model Context Protocol) server that allows agents to scaffold, update, and manage services via high-level API calls.

## 🛠 Tech Stack

- **Core:** Python 3.11, Docker Compose
- **API:** FastAPI, Pydantic (Spec-First)
- **Data:** PostgreSQL, SQLAlchemy, Alembic
- **Quality:** Ruff, Mypy, Pytest

## License

Open Source. Use it, fork it, build agents with it.
