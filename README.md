# Crypto Price Alert Bot (Telegram)

A production-ready Telegram bot that sends **price alerts** for crypto assets.
Built with **aiogram 3**, **aiohttp**, **SQLite (aiosqlite)** and a background
worker that polls CoinGecko — no paid APIs, no external database.

> Want to see it running? Message me and I'll send a live demo bot link.

## Features

- `/price btc` — instant price lookup (12 majors pre-mapped)
- `/alert eth above 4200` — one-off alert that fires once and deactivates itself
- `/alerts`, `/del <id>`, `/delall` — full alert management
- Background worker batches all active symbols into **one** HTTP request per cycle
  (fewer rate-limit issues, cheap to run)
- Per-user alert limit, input validation, graceful network failure handling
- Docker + SQLite, so it runs on a $3 VPS, Railway, Fly.io or Render

## How it works

```
Telegram ──► aiogram Router ──► SQLite (alerts)
                                   ▲
        background worker ─────────┘
              │ every CHECK_INTERVAL
              ▼
        CoinGecko /simple/price  ──► trigger ──► bot.send_message()
```

The worker fetches **one** batched price response for all active alerts instead of
one request per alert, which keeps the bot inside CoinGecko's free rate limits.

## Quick start

```bash
git clone https://github.com/rez9414/telegram-price-alert-bot.git && cd telegram-price-alert-bot
python -m venv .venv
# Windows: .venv\Scripts\activate    |  Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then put your @BotFather token in BOT_TOKEN
python bot.py
```

## Deploy

**Docker**

```bash
docker build -t price-alert-bot .
docker run -d --restart unless-stopped --env-file .env \
  -v $(pwd)/data:/app/data --name price-alert-bot price-alert-bot
```

**systemd (VPS)**

```ini
[Unit]
Description=Crypto Price Alert Bot
After=network-online.target

[Service]
WorkingDirectory=/opt/price-alert-bot
ExecStart=/opt/price-alert-bot/.venv/bin/python bot.py
Restart=always
EnvironmentFile=/opt/price-alert-bot/.env

[Install]
WantedBy=multi-user.target
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token from @BotFather |
| `CHECK_INTERVAL` | `90` | Seconds between price checks (keep ≥ 60) |
| `MAX_ALERTS` | `10` | Active alerts allowed per chat |
| `DB_PATH` | `alerts.db` | SQLite file path |

## Extending it

- Swap CoinGecko for Binance/Bybit WebSocket for real-time triggers
- Add inline-keyboard buttons for one-tap alert creation
- Add a subscriptions table and a paid tier (`/upgrade`) — Stripe or crypto payments
- Move SQLite to Postgres when you pass a few thousand alerts

## Tech

Python 3.12 · aiogram 3 · aiohttp · aiosqlite · Docker

---

Built by **Reza Alipour** ([CodeStormX](https://t.me/OstadCodex)) — MIT licensed, use it however you like.
Need a custom version (exchange APIs, whale alerts, admin panel)? Open an issue or message me.
