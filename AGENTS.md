# Agents Playbook / Documentation Map

This file serves as the entry point for AI Agents exploring the repository. Use this map to load only the context you need.

## 🗺 Navigation

- **Philosophy & Goals:** `MANIFESTO.md` (Read this first to understand *why*)
- **System Design:** `ARCHITECTURE.md` (Read this to understand *how*)
- **Rules & Standards:** `CONTRIBUTING.md` (Strict rules for coding)
- **Service Registry:** `services.yml` (List of all active services)

## 📂 Service Modules

Detailed documentation for each service can be found in its respective directory. Only load these if you are working on that specific service.

- **Backend:** `services/backend/AGENTS.md`
- **Telegram Bot:** `services/tg_bot/AGENTS.md`
- **Infrastructure:** `infra/README.md` (if available)

## 🛠 Operational Commands

Agents should interact with the system primarily through `make`.

- **Check State:** `make sync-services check`
- **Scaffold:** `make sync-services create`
- **Verify:** `make lint && make tests`
- **Generate:** `make generate-from-spec`
