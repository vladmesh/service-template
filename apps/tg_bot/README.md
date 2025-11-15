# Telegram Bot

This directory contains a minimal python-telegram-bot application. The
`main.py` file wires a `/start` handler and can be extended with more
commands, message handlers, or background jobs as you iterate.

## Local development

1. Install the dependencies:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export your bot token (from BotFather):
   ```bash
   export TELEGRAM_BOT_TOKEN="123:abc"
   ```
3. Run the bot:
   ```bash
   python apps/tg_bot/main.py
   ```

## Docker compose integration

The base Compose stack already includes this service, so `make dev-start`
will build and start it automatically alongside the backend and database.
If you only need the bot (or want to force a rebuild), target the service
explicitly:

```bash
docker compose -f infra/compose.base.yml -f infra/compose.dev.yml \
  up --build tg_bot
```

Feel free to add additional handlers, background tasks, or persistence
layers as needed.
