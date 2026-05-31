# GenTwin — TwinGuard Dynamics

Enterprise industrial AI platform: landing page, operator SCADA, analytics, demo, docs, deploy wizard, and Telegram alert backend.

## Quick start

Open in browser (no build step):

- [index.html](index.html) — Marketing landing
- [operator.html](operator.html) — Operator SCADA
- [demo.html](demo.html) — Interactive pipeline demo
- [analytics.html](analytics.html) — Admin dashboard

## Telegram alerts (optional)

```bash
cd backend
cp .env.example .env   # add TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8787
```

Message [@TwinGuardian_Bot](https://t.me/TwinGuardian_Bot) with `/start`, then:

```bash
python scripts/test_alert.py --preset pwf
```

## Files

| Path | Description |
|------|-------------|
| `index.html` | Main landing page |
| `operator.html` | Plant operator UI |
| `demo.html` | Fault injection demo |
| `analytics.html` | Management KPIs |
| `docs.html` | Technical documentation |
| `simulator.html` | Deep simulation lab |
| `deploy.html` | Deployment config wizard |
| `paper.html` | Research paper viewer |
| `backend/` | FastAPI alert API + Telegram |

**Do not commit `backend/.env`** — copy from `.env.example` locally.
