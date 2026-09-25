"""
Watchlist 掃描服務。

採用逐檔、低頻率掃描：
- 不使用平行大量請求
- 單一股票由 market_data 的 15 分鐘快取保護
- 其中一檔失敗不會令整個清單失敗
"""

from __future__ import annotations

from typing import Any

from ..config import get_watchlist
from .alerts import build_alert
from .market_data import MarketDataError, get_symbol_analysis


def scan_watchlist(
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """
    掃描 watchlist 並產生提醒。
    """

    selected_symbols = symbols or get_watchlist()

    analyses: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for symbol in selected_symbols[:30]:
        try:
            analysis = get_symbol_analysis(symbol)
            analyses.append(analysis)

            alert = build_alert(analysis)

            if alert is not None:
                alerts.append(alert)

        except MarketDataError as error:
            errors.append(
                {
                    "symbol": symbol,
                    "error": str(error),
                }
            )

    return {
        "watchlist": selected_symbols[:30],
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
