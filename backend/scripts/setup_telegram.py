#!/usr/bin/env python3
"""Discover Telegram chat_id after user messages @TwinGuardian_Bot."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    print("Set TELEGRAM_BOT_TOKEN in backend/.env")
    sys.exit(1)

print("1. Open https://t.me/TwinGuardian_Bot on your phone/desktop")
print("2. Tap START (or send /start)")
print("3. Re-run this script\n")

r = httpx.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=15)
data = r.json()
if not data.get("ok"):
    print("API error:", data)
    sys.exit(1)

updates = data.get("result", [])
if not updates:
    print("No messages yet. Message the bot first, then run again.")
    sys.exit(0)

for u in updates[-5:]:
    msg = u.get("message") or u.get("channel_post") or {}
    chat = msg.get("chat", {})
    cid = chat.get("id")
    name = chat.get("first_name") or chat.get("title") or "?"
    print(f"  chat_id={cid}  type={chat.get('type')}  name={name}")

latest = updates[-1]
chat_id = (latest.get("message") or {}).get("chat", {}).get("id")
if chat_id:
    print(f"\nAdd to backend/.env:\nTELEGRAM_CHAT_ID={chat_id}")
