"""
GitHub Actions / 定時任務入口。

產生：
- 市場摘要
- Watchlist 分析
- Alert
- RSS 新聞
- Telegram 通知
- Alert 去重狀態
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.app.services.alert_notifier import maybe_send_telegram
from backend.app.services.alerts import build_alert
from backend.app.services.market_data import (
    get_market_summary,
    get_symbol_analysis,
)
from backend.app.services.news import get_market_news
from backend.app.config import get_watchlist


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "dashboard.json"
STATE_PATH = ROOT_DIR / "data" / "alert-state.json"

# 相同 Alert 24 小時內只發送一次。
ALERT_COOLDOWN_SECONDS = 24 * 60 * 60


def save_dashboard(payload: dict[str, Any]) -> None:
    """安全寫入完整 Dashboard JSON。"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = OUTPUT_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    temporary_path.replace(OUTPUT_PATH)


def load_alert_state() -> dict[str, dict[str, Any]]:
    """讀取過往 Telegram Alert 發送狀態。"""

    if not STATE_PATH.exists():
        return {}

    try:
        with STATE_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if isinstance(payload, dict):
            return payload

    except (OSError, json.JSONDecodeError):
        pass

    # 狀態檔損壞時，不阻止整個掃描。
    return {}


def save_alert_state(
    state: dict[str, dict[str, Any]],
) -> None:
    """安全寫入 Alert 狀態。"""

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = STATE_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2)

    temporary_path.replace(STATE_PATH)


def get_alert_key(alert: dict[str, Any]) -> str:
    """
    建立 Alert 唯一識別碼。

    只有股票、Alert 類型和原因都相同，
    才會被視為同一個 Alert。
    """

    symbol = str(alert.get("symbol", "UNKNOWN"))
    alert_type = str(alert.get("type", "information"))
    reason = str(alert.get("reason", ""))

    return f"{symbol}|{alert_type}|{reason}"


def should_send_alert(
    alert: dict[str, Any],
    state: dict[str, dict[str, Any]],
    now_timestamp: float,
) -> bool:
    """判斷相同 Alert 是否已在冷卻時間內發送。"""

    alert_key = get_alert_key(alert)
    previous = state.get(alert_key)

    if not previous:
        return True

    last_sent_at = previous.get("last_sent_at")

    if not isinstance(last_sent_at, (int, float)):
        return True

    elapsed_seconds = now_timestamp - float(last_sent_at)

    return elapsed_seconds >= ALERT_COOLDOWN_SECONDS


def scan_watchlist(
    alert_state: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """逐檔掃描 watchlist 並套用 Telegram 去重。"""

    symbols = get_watchlist()
    analyses: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    now_timestamp = time.time()
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    for symbol in symbols:
        try:
            analysis = get_symbol_analysis(symbol)
            analyses.append(analysis)

            alert = build_alert(analysis)

            if alert is None:
                continue

            alert_key = get_alert_key(alert)

            if dry_run:
                notification_result = {
                    "sent": False,
                    "reason": "dry run mode",
                }

            elif should_send_alert(
                alert=alert,
                state=alert_state,
                now_timestamp=now_timestamp,
            ):
                notification_result = maybe_send_telegram(alert)

                # 只有真正成功發送，才記錄冷卻時間。
                if notification_result.get("sent", False):
                    alert_state[alert_key] = {
                        "symbol": alert.get("symbol", ""),
                        "type": alert.get("type", ""),
                        "reason": alert.get("reason", ""),
                        "last_sent_at": now_timestamp,
                        "last_sent_at_iso": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }

            else:
                notification_result = {
                    "sent": False,
                    "reason": "cooldown active",
                }

            alert["telegram_sent"] = notification_result.get(
                "sent",
                False,
            )
            alert["telegram_reason"] = notification_result.get(
                "reason",
                "",
            )

            alerts.append(alert)

        except Exception as error:
            errors.append(
                {
                    "symbol": symbol,
                    "error": str(error),
                }
            )

    return {
        "watchlist": symbols,
        "analyses": analyses,
        "alerts": alerts,
        "errors": errors,
        "scanned_count": len(analyses),
        "failed_count": len(errors),
        "disclaimer": (
            "Alert 僅根據簡化技術條件產生，"
            "不構成投資建議或買賣指令。"
        ),
    }


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    alert_state = load_alert_state()

    try:
        market = get_market_summary()
    except Exception as error:
        market = {
            "is_demo": False,
            "indices": [],
            "vix": {
                "symbol": "^VIX",
                "status": "unknown",
                "status_text": "暫時無法取得",
                "error": str(error),
            },
        }

    watchlist = scan_watchlist(alert_state)

    try:
        news = get_market_news()
    except Exception as error:
        news = {
            "top_stories": [],
            "sentiment_summary": {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
            },
            "errors": [str(error)],
            "disclaimer": "新聞資料暫時無法取得，請稍後重試。",
        }

    payload = {
        "generated_at": generated_at,
        "market": market,
        "watchlist": watchlist,
        "news": news,
        "disclaimer": (
            "所有資料僅供參考，不構成投資建議。"
            "投資涉及風險，請自行判斷。"
        ),
    }

    save_dashboard(payload)
    save_alert_state(alert_state)

    print(
        "Dashboard generated: "
        f"{watchlist['scanned_count']} stocks, "
        f"{len(watchlist['alerts'])} alerts"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
