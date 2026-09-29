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
LAST_GOOD_OUTPUT_PATH = (
    ROOT_DIR / "data" / "dashboard-last-good.json"
)

# 相同 Alert 24 小時內只發送一次。
ALERT_COOLDOWN_SECONDS = 24 * 60 * 60


def build_data_health(
    market: dict[str, Any],
    watchlist: dict[str, Any],
    news: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """
    建立 Dashboard 資料健康狀態。

    status:
    - ok：主要資料來源正常
    - partial：部分來源失敗
    - error：市場主要資料無法取得
    """

    market_indices = market.get("indices", [])

    market_errors = [
        item
        for item in market_indices
        if item.get("error") or item.get("status") == "unknown"
    ]

    watchlist_errors = watchlist.get("errors", [])
    news_errors = news.get("errors", [])

    market_unavailable = (
        len(market_indices) == 0
        or len(market_errors) == len(market_indices)
    )

    total_error_count = (
        len(market_errors)
        + len(watchlist_errors)
        + len(news_errors)
    )

    if market_unavailable:
        status = "error"
    elif total_error_count > 0:
        status = "partial"
    else:
        status = "ok"

    return {
        "status": status,
        "is_stale": total_error_count > 0,
        "generated_at": generated_at,
        "market": {
            "status": (
                "error"
                if market_unavailable
                else "partial"
                if market_errors
                else "ok"
            ),
            "successful_count": len(market_indices) - len(market_errors),
            "failed_count": len(market_errors),
        },
        "watchlist": {
            "status": "partial" if watchlist_errors else "ok",
            "scanned_count": watchlist.get("scanned_count", 0),
            "failed_count": len(watchlist_errors),
        },
        "news": {
            "status": "partial" if news_errors else "ok",
            "article_count": len(news.get("top_stories", [])),
            "failed_count": len(news_errors),
        },
        "total_error_count": total_error_count,
        "message": (
            "所有主要資料來源正常。"
            if status == "ok"
            else
            "部分資料來源暫時失敗，頁面內容可能不完整。"
            if status == "partial"
            else
            "市場主要資料無法取得，請不要根據目前頁面作出判斷。"
        ),
    }


def remove_private_alert_fields(
    watchlist: dict[str, Any],
) -> dict[str, Any]:
    """移除不應公開給瀏覽器的 Telegram 內部欄位。"""

    public_watchlist = dict(watchlist)
    public_alerts = []

    for alert in watchlist.get("alerts", []):
        public_alert = dict(alert)
        public_alert.pop("telegram_sent", None)
        public_alert.pop("telegram_reason", None)
        public_alerts.append(public_alert)

    public_watchlist["alerts"] = public_alerts
    return public_watchlist

def load_json_file(path: Path) -> dict[str, Any] | None:
    """讀取 JSON 檔案；檔案不存在或損壞時回傳 None。"""

    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        return payload if isinstance(payload, dict) else None

    except (OSError, json.JSONDecodeError):
        return None

def save_last_good_dashboard(
    payload: dict[str, Any],
) -> None:
    """保存最近一次市場資料正常的 Dashboard。"""

    LAST_GOOD_OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = LAST_GOOD_OUTPUT_PATH.with_suffix(".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    temporary_path.replace(LAST_GOOD_OUTPUT_PATH)

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

    public_watchlist = remove_private_alert_fields(watchlist)

    health = build_data_health(
        market=market,
        watchlist=watchlist,
        news=news,
        generated_at=generated_at,
    )

    current_payload = {
        "generated_at": generated_at,
        "data_updated_at": generated_at,
        "health": health,
        "market": market,
        "watchlist": public_watchlist,
        "news": news,
        "disclaimer": (
            "所有資料僅供參考，不構成投資建議。"
            "投資涉及風險，請自行判斷。"
        ),
    }

    last_good_payload = load_json_file(
        LAST_GOOD_OUTPUT_PATH
    )

    if health["status"] == "error" and last_good_payload:
        previous_generated_at = last_good_payload.get(
            "data_updated_at",
            last_good_payload.get("generated_at"),
        )

        payload = {
            **last_good_payload,
            "generated_at": generated_at,
            "data_updated_at": previous_generated_at,
            "health": {
                **health,
                "fallback_used": True,
                "message": (
                    "目前市場資料暫時無法取得，"
                    "以下顯示上一份正常資料。"
                ),
            },
        }
    else:
        payload = current_payload

        if health["status"] in {"ok", "partial"}:
            save_last_good_dashboard(payload)

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
