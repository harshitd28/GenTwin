"""Telegram delivery for GenTwin alerts via @TwinGuardian_Bot."""

from __future__ import annotations

import html
import logging
from typing import Any

import httpx

from alert_contract import GenTwinAlert

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def format_alert_message(alert: GenTwinAlert) -> str:
    """Rich HTML message for Telegram (parse_mode=HTML)."""
    if not alert.anomaly_detected:
        return (
            f"✅ <b>GenTwin — Normal</b>\n"
            f"🏭 {_esc(alert.plant_name)}\n"
            f"🕐 {_esc(alert.timestamp_utc)}\n"
            f"ID: <code>{_esc(alert.alert_id)}</code>\n\n"
            f"All sensors nominal. No operator action required."
        )

    prio_icon = {1: "ℹ️", 2: "⚠️", 3: "🛑"}.get(alert.safety_priority, "⚠️")
    hazop_icon = "✅" if alert.hazop_status == "PASS" else "❌"

    lines = [
        f"{prio_icon} <b>GenTwin ANOMALY ALERT</b>",
        f"🏭 <b>Plant:</b> {_esc(alert.plant_name)}",
        f"🕐 <b>Time:</b> {_esc(alert.timestamp_utc)}",
        f"🆔 <code>{_esc(alert.alert_id)}</code>",
        "",
        f"<b>━━ FAULT ━━</b>",
        f"• <b>Code:</b> <code>{_esc(alert.fault_code)}</code>",
        f"• <b>Type:</b> {_esc(alert.fault_name)}",
        f"• <b>Severity:</b> {_esc(alert.severity_label)} (P{alert.safety_priority})",
        f"• <b>Component:</b> {_esc(alert.affected_component)}",
        "",
        f"<b>━━ ROOT CAUSE ━━</b>",
        _esc(alert.root_cause),
        "",
        f"<b>━━ SENSOR SNAPSHOT ━━</b>",
        f"PS1 {_esc(alert.sensors.PS1)} bar · PS2 {_esc(alert.sensors.PS2)} bar",
        f"TS1 {_esc(alert.sensors.TS1)} K · TS2 {_esc(alert.sensors.TS2)} K",
        f"Torque {_esc(alert.sensors.Torque)} Nm · Speed {_esc(alert.sensors.Speed)} rpm · Wear {_esc(alert.sensors.Wear)} min",
    ]

    for _key, detail in alert.sensor_analysis.items():
        lines.append(f"↳ {_esc(detail)}")

    lines.extend(
        [
            "",
            f"<b>━━ HAZOP (Layer 4) ━━</b>",
            f"{hazop_icon} <b>{_esc(alert.hazop_status)}</b> — {_esc(alert.hazop_detail)}",
        ]
    )

    if alert.artifact:
        a = alert.artifact
        lines.extend(
            [
                "",
                f"<b>━━ RECOVERY ARTIFACT ━━</b>",
                f"• Action: <code>{_esc(a.action)}</code>",
                f"• Target PS1: {a.target_pressure_ps1:.0f} bar",
                f"• Confidence: {a.confidence:.0%}",
                f"• Source: {_esc(a.source_doc)}",
            ]
        )

    if alert.sop_steps:
        lines.append("")
        lines.append("<b>━━ OPERATOR SOP — DO THIS NOW ━━</b>")
        for step in alert.sop_steps:
            lines.append(f"{step.step}. {_esc(step.instruction)}")

    if alert.prevention:
        lines.append("")
        lines.append("<b>━━ PREVENT RECURRENCE ━━</b>")
        for p in alert.prevention:
            lines.append(f"• {_esc(p)}")

    if alert.cascade:
        c = alert.cascade
        lines.extend(
            [
                "",
                f"<b>━━ CASCADE RISK ━━</b>",
                _esc(c.summary),
            ]
        )
        if c.probability_bearing_to_shaft is not None:
            lines.append(
                f"• Bearing B2 → Drive Shaft: <b>{c.probability_bearing_to_shaft:.0%}</b>"
            )
        if c.probability_shaft_to_motor is not None:
            lines.append(f"• Drive Shaft → Kiln Motor: <b>{c.probability_shaft_to_motor:.0%}</b>")
        if c.estimated_downtime_usd:
            lines.append(f"• Est. downtime exposure: <b>${c.estimated_downtime_usd:,}</b>")

    if alert.latency_ms:
        total = alert.latency_ms.get("total_ms", 0)
        lines.extend(
            [
                "",
                f"<b>━━ PIPELINE ━━</b>",
                f"End-to-end: <b>{total:.0f} ms</b> · Source: {_esc(alert.source)}",
            ]
        )

    if alert.narrative:
        lines.extend(["", "<b>━━ AI SUMMARY ━━</b>", _esc(alert.narrative)])

    lines.append("")
    lines.append("<i>TwinGuard Dynamics · GenTwin Immunosystem</i>")
    lines.append("🤖 @TwinGuardian_Bot")

    return "\n".join(lines)


class TelegramAlertService:
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        self.chat_id = str(chat_id)
        self.enabled = enabled

    async def send_alert(self, alert: GenTwinAlert) -> dict[str, Any]:
        if not self.enabled:
            logger.info("Alerts disabled; skipping Telegram send for %s", alert.alert_id)
            return {"ok": True, "skipped": True}

        text = format_alert_message(alert)
        return await self._send_message(text)

    async def send_text(self, text: str) -> dict[str, Any]:
        return await self._send_message(text)

    async def _send_message(self, text: str) -> dict[str, Any]:
        url = TELEGRAM_API.format(token=self.bot_token, method="sendMessage")
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4096],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if not resp.is_success or not data.get("ok"):
                logger.error("Telegram API error: %s", data)
                err = data.get("description", "")
                if "chat not found" in err.lower():
                    raise RuntimeError(
                        "Telegram chat not found. Open https://t.me/TwinGuardian_Bot "
                        "and tap START, then retry. Chat ID must match the account that messaged the bot."
                    )
                raise RuntimeError(f"Telegram send failed: {data}")
            logger.info("Telegram message sent message_id=%s", data.get("result", {}).get("message_id"))
            return data

    def send_alert_sync(self, alert: GenTwinAlert) -> dict[str, Any]:
        import asyncio

        return asyncio.run(self.send_alert(alert))
