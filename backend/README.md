# GenTwin Alert System — TwinGuard Dynamics

Telegram bot: [@TwinGuardian_Bot](https://t.me/TwinGuardian_Bot)

Sends full anomaly alerts (fault code, root cause, sensors, HAZOP, SOP steps, prevention, cascade risk) from the **contract backend**. Optional Gemini narrative when `GEMINI_API_KEY` is set.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit tokens — never commit .env
```

## Run API

```bash
uvicorn main:app --reload --port 8787
```

- `GET /health` — config status
- `POST /api/v1/alerts/evaluate` — telemetry JSON → alert + Telegram
- `POST /api/v1/alerts/test-fake` — preset scenario (`pwf`, `hdf`, `osf`, `twf`, `hazop_violation`)
- `POST /api/v1/alerts/telegram-test` — connectivity ping

## CLI test

```bash
python scripts/test_alert.py --preset pwf
python scripts/test_alert.py --ping
```

## Security

- Store `TELEGRAM_BOT_TOKEN` only in `.env` (gitignored).
- If a token was exposed in chat, revoke it via [@BotFather](https://t.me/BotFather) and issue a new token.

## Operator UI

`operator.html` calls `http://127.0.0.1:8787/api/v1/alerts/evaluate` when faults are injected (toggle in top bar).
