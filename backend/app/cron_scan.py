"""
GitHub Actions / 定時任務入口。

產生完整 dashboard snapshot：
- 市場摘要
- Watchlist 分析
- Alert
- RSS 新聞
- 產生時間

這個 JSON 可以直接被靜態前端讀取。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from backend.app.config import get_watchlist
from backend.app.services.alert_notifier import maybe_send_telegram
from backend.app.services.alerts import build_alert
from backend.app.services.market_data import (
    get_market_summary,
    get_symbol_analysis,
)
from backend.app.services.news import get_market_news

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "dashboard.json"


def save_dashboard(payload: dict[str, Any]) -> None:
    """將完整分析結果寫入 JSON。"""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = OUTPUT_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    # 先寫 temporary file，再以 replace 取代正式檔案，
    # 避免前端讀到只寫了一半的 JSON。
    temporary_path.replace(OUTPUT_PATH)


def scan_watchlist() -> dict[str, Any]:
    """逐檔掃描 watchlist。"""

    symbols = get_watchlist()
    analyses: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for symbol in symbols:
        try:
            analysis = get_symbol_analysis(symbol)
            analyses.append(analysis)

            alert = build_alert(analysis)

            if alert is not None:
                if os.getenv("DRY_RUN", "false").lower() == "true":
                    notification_result = {
                        "sent": False,
                        "reason": "dry run mode",
                    }
                else:
                    notification_result = maybe_send_telegram(alert)

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

    watchlist = scan_watchlist()

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
            "disclaimer": (
                "新聞資料暫時無法取得，請稍後重試。"
            ),
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

    print(
        "Dashboard generated: "
        f"{watchlist['scanned_count']} stocks, "
        f"{len(watchlist['alerts'])} alerts"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
