"""
TwinGuard Dynamics — GenTwin Alert API
Telegram: @TwinGuardian_Bot

Run: uvicorn main:app --reload --port 8787
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from alert_contract import GenTwinAlert, SensorSnapshot
from gemini_enricher import enrich_with_gemini
from gentwin_engine import FAKE_PRESETS, run_pipeline
from telegram_service import TelegramAlertService

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gentwin.alerts")


def _settings() -> dict[str, Any]:
    return {
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "plant_name": os.getenv("PLANT_NAME", "JK Cement — Rotary Kiln Line 2"),
        "alerts_enabled": os.getenv("ALERTS_ENABLED", "true").lower() in ("1", "true", "yes"),
        "gemini_key": os.getenv("GEMINI_API_KEY", ""),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    }


telegram: Optional[TelegramAlertService] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global telegram
    cfg = _settings()
    if cfg["bot_token"] and cfg["chat_id"]:
        telegram = TelegramAlertService(
            bot_token=cfg["bot_token"],
            chat_id=cfg["chat_id"],
            enabled=cfg["alerts_enabled"],
        )
        logger.info("Telegram wired chat_id=%s enabled=%s", cfg["chat_id"], cfg["alerts_enabled"])
    else:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing — alerts will not send")
    yield


app = FastAPI(
    title="GenTwin Alert API",
    description="TwinGuard Dynamics anomaly alerts → Telegram",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TelemetryRequest(BaseModel):
    PS1: float
    PS2: float
    TS1: float
    TS2: float
    Torque: float
    Speed: float
    Wear: float
    plant_name: Optional[str] = None
    send_telegram: bool = True
    use_gemini: bool = False


class PresetRequest(BaseModel):
    preset: str = Field(..., description="normal|hdf|pwf|osf|twf|hazop_violation")
    send_telegram: bool = True
    use_gemini: bool = False


class AlertResponse(BaseModel):
    alert: GenTwinAlert
    telegram: Optional[dict[str, Any]] = None


@app.get("/health")
def health():
    cfg = _settings()
    return {
        "status": "ok",
        "telegram_configured": bool(cfg["bot_token"] and cfg["chat_id"]),
        "alerts_enabled": cfg["alerts_enabled"],
        "gemini_configured": bool(cfg["gemini_key"]),
        "bot": "https://t.me/TwinGuardian_Bot",
    }


@app.post("/api/v1/alerts/evaluate", response_model=AlertResponse)
async def evaluate_alert(body: TelemetryRequest):
    cfg = _settings()
    plant = body.plant_name or cfg["plant_name"]
    telemetry = body.model_dump(exclude={"plant_name", "send_telegram", "use_gemini"})
    alert = run_pipeline(telemetry, plant_name=plant)

    if body.use_gemini and cfg["gemini_key"] and alert.anomaly_detected:
        narrative = enrich_with_gemini(alert, cfg["gemini_key"], cfg["gemini_model"])
        if narrative:
            alert.narrative = narrative
            alert.source = "hybrid"

    tg_result = None
    if body.send_telegram:
        if not telegram:
            raise HTTPException(503, "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        if alert.anomaly_detected:
            tg_result = await telegram.send_alert(alert)

    return AlertResponse(alert=alert, telegram=tg_result)


@app.post("/api/v1/alerts/test-fake", response_model=AlertResponse)
async def test_fake(body: PresetRequest):
    preset = body.preset.lower()
    if preset not in FAKE_PRESETS:
        raise HTTPException(400, f"Unknown preset. Choose from: {list(FAKE_PRESETS.keys())}")
    cfg = _settings()
    alert = run_pipeline(FAKE_PRESETS[preset], plant_name=cfg["plant_name"])

    if body.use_gemini and cfg["gemini_key"] and alert.anomaly_detected:
        narrative = enrich_with_gemini(alert, cfg["gemini_key"], cfg["gemini_model"])
        if narrative:
            alert.narrative = narrative
            alert.source = "hybrid"

    tg_result = None
    if body.send_telegram:
        if not telegram:
            raise HTTPException(503, "Telegram not configured")
        tg_result = await telegram.send_alert(alert)

    return AlertResponse(alert=alert, telegram=tg_result)


@app.post("/api/v1/alerts/telegram-test")
async def telegram_ping():
    """Send a short connectivity test to configured chat."""
    if not telegram:
        raise HTTPException(503, "Telegram not configured")
    cfg = _settings()
    result = await telegram.send_text(
        "🔔 <b>TwinGuard Dynamics — GenTwin</b>\n"
        "Telegram alert channel is <b>online</b>.\n"
        f"🏭 {cfg['plant_name']}\n"
        "🤖 @TwinGuardian_Bot"
    )
    return {"ok": True, "telegram": result}
