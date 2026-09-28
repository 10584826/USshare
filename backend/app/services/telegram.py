"""
Telegram Bot 通知模組。

使用方式：
- 建立 Telegram Bot：https://t.me/BotFather
- 取得 BOT_TOKEN
- 建立私人群組/頻道，加入 Bot 後取得 chat_id
- 在 .env 中設定：
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...

注意：
- 這不是必要功能，但能幫你實現免費通知。
- 若 TOKEN 或 chat_id 沒設定，函數直接回傳 False，不會讓應用崩潰。
"""

from __future__ import annotations

import os
from typing import Any

import requests


TELEGRAM_API_URL = "https://api.telegram.org/bot8884228114:AAEBZGUzhAJuaObHBJiCpwtm7gzwHSdsD54/sendMessage"


def send_telegram_alert(message: str) -> bool:
    """
    發送訊息到 Telegram。
    如果未設定 token 或 chat_id，直接返回 False。
    """

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        return False

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(
            TELEGRAM_API_URL.format(token=token),
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def build_alert_message(alert: dict[str, Any]) -> str:
    """
    把 Alert 轉成 Telegram 可用的簡短格式。
    保持簡單，避免過長。
    """

    symbol = alert.get("symbol", "UNKNOWN")
    title = alert.get("title", "USshare Alert")
    reason = alert.get("reason", "No reason available")
    message = alert.get("message", "No message")

    text = (
        f"<b>USshare Alert</b>\n"
        f"<b>{symbol}</b> - {title}\n"
        f"原因：{reason}\n"
        f"{message}\n"
        f"<i>僅供參考，不構成投資建議</i>"
    )

    return text
