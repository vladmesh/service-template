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

## Docker compose overlay

The `infra/compose.tg.yml` overlay registers this service under the `tg`
profile so you can toggle it alongside the rest of the stack:

```bash
docker compose -f infra/compose.dev.yml -f infra/compose.tg.yml \
  --profile tg up --build tg_bot
```

Feel free to add additional handlers, background tasks, or persistence
layers as needed.
