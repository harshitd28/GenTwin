#!/usr/bin/env python3
"""CLI test: send GenTwin fake anomaly alerts to Telegram."""

import argparse
import json
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from gentwin_engine import FAKE_PRESETS, run_pipeline
from telegram_service import TelegramAlertService
import os


def main():
    parser = argparse.ArgumentParser(description="Test GenTwin Telegram alerts")
    parser.add_argument(
        "--preset",
        default="pwf",
        choices=list(FAKE_PRESETS.keys()),
        help="Fake fault scenario",
    )
    parser.add_argument("--ping", action="store_true", help="Send connectivity ping only")
    parser.add_argument("--dry-run", action="store_true", help="Print message without sending")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("ERROR: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in backend/.env")
        sys.exit(1)

    svc = TelegramAlertService(token, chat_id)
    plant = os.getenv("PLANT_NAME", "JK Cement — Rotary Kiln Line 2")

    if args.ping:
        from telegram_service import format_alert_message

        if args.dry_run:
            print("Would send ping to Telegram")
            return
        result = svc.send_alert_sync(
            run_pipeline(FAKE_PRESETS["normal"], plant_name=plant)
        )
        # Actually send ping text
        import asyncio

        result = asyncio.run(
            svc.send_text(
                "🔔 <b>TwinGuard Dynamics — GenTwin</b>\n"
                "Telegram test OK.\n"
                f"🏭 {plant}\n"
                "🤖 @TwinGuardian_Bot"
            )
        )
        print("Ping sent:", json.dumps(result, indent=2)[:500])
        return

    alert = run_pipeline(FAKE_PRESETS[args.preset], plant_name=plant)
    from telegram_service import format_alert_message

    msg = format_alert_message(alert)
    print("--- Message preview ---\n")
    print(msg.replace("<b>", "**").replace("</b>", "**").replace("<code>", "`").replace("</code>", "`"))
    print("\n--- JSON contract ---\n")
    print(json.dumps(alert.model_dump(), indent=2))

    if args.dry_run:
        print("\n(dry-run: not sent)")
        return

    result = svc.send_alert_sync(alert)
    print("\nTelegram OK:", result.get("ok"), "message_id:", result.get("result", {}).get("message_id"))


if __name__ == "__main__":
    main()
