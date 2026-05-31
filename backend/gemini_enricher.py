"""Optional Gemini enrichment for alert narratives."""

from __future__ import annotations

import json
import logging
import os

import httpx

from alert_contract import GenTwinAlert

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def enrich_with_gemini(alert: GenTwinAlert, api_key: str, model=None):
    """Return a short operator-facing narrative, or None on failure."""
    if not alert.anomaly_detected:
        return None

    model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    prompt = f"""You are GenTwin industrial safety AI for TwinGuard Dynamics.
Write a concise alert for a plant operator (max 120 words).
Include: what failed, why, immediate actions, one prevention tip.
Use plain language. Do not invent sensor values.

Alert JSON:
{json.dumps(alert.model_dump(), indent=2)}
"""

    try:
        url = GEMINI_URL.format(model=model) + f"?key={api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256},
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            return parts[0].get("text", "").strip()
    except Exception as exc:
        logger.warning("Gemini enrichment failed: %s", exc)
        return None
