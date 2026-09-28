"""
GitHub Actions / 定時任務入口。

目標：
- 讀取 watchlist
- 取回市場資料
- 計算技術指標
- 產生 alert
- 發送 Telegram（如果已設定）
- 輸出 JSON 給前端或後續處理

這不是前端 API，而是定時任務腳本。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from backend.app.config import get_watchlist
from backend.app.services.alert_notifier import maybe_send_telegram
from backend.app.services.alerts import build_alert
from backend.app.services.market_data import get_symbol_analysis

load_dotenv()

OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "alerts.json"


def ensure_output_dir() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def save_alerts(alerts: list[dict]) -> None:
    ensure_output_dir()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alerts": alerts,
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> int:
    symbols = get_watchlist()
    alerts: list[dict] = []

    for symbol in symbols:
        try:
            analysis = get_symbol_analysis(symbol)
            alert = build_alert(analysis)

            if alert is not None:
                if os.getenv("DRY_RUN", "false").lower() == "true":
                    telegram_result = {
                        "sent": False,
                        "reason": "dry run mode",
                    }
                else:
                    telegram_result = maybe_send_telegram(alert)

                alert["telegram_sent"] = telegram_result.get("sent", False)
                alert["telegram_reason"] = telegram_result.get(
                    "reason",
                    "",
                )
                alerts.append(alert)

        except Exception as exc:
            # 若單一股票失敗，不讓整個 cron 任務整個中斷
            alerts.append(
                {
                    "symbol": symbol,
                    "type": "information",
                    "severity": "info",
                    "title": f"{symbol} 資料異常",
                    "message": str(exc),
                    "reason": "掃描時發生錯誤",
                    "is_actionable": False,
                    "telegram_sent": False,
                }
            )

    save_alerts(alerts)
    print(f"Generated {len(alerts)} alerts from {len(symbols)} symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
