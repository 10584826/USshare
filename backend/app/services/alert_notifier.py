"""
簡單 Alert 通知管線。

1. 先判斷 alert 類型
2. 若是 risk / attention，才發送 Telegram
3. 若環境未設定 token，直接跳過
"""

from __future__ import annotations

from typing import Any

from .telegram import build_alert_message, send_telegram_alert


def maybe_send_telegram(alert: dict[str, Any]) -> dict[str, Any]:
    """
    只在風險或關注警示時發送，不對所有內容發訊息。
    """

    alert_type = alert.get("type", "information")

    if alert_type not in {"risk", "attention"}:
        return {
            "sent": False,
            "reason": "non-actionable alert",
        }

    message = build_alert_message(alert)
    sent = send_telegram_alert(message)

    return {
        "sent": sent,
        "reason": "risk or attention alert",
    }
