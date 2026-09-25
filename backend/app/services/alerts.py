"""
新手友善的 Alert 引擎。

重要：
這些規則不是投資建議，也不是預測工具。
它們只根據幾個簡單條件，將市場資料轉成容易理解的提醒。

Alert 類型：
- attention：值得留意
- risk：風險提醒
- information：一般資訊
"""

from __future__ import annotations

from typing import Any


def build_alert(
    analysis: dict[str, Any],
) -> dict[str, Any] | None:
    """
    根據單一股票分析結果建立一個簡單 Alert。

    優先順序：
    1. 價格跌破 50 日均線：風險提醒
    2. RSI 超買：留意短線過熱
    3. RSI 超賣：可能值得觀察，但不是買入訊號
    4. 價格在均線之上且 RSI 正常：偏正面觀察
    """

    symbol = analysis["symbol"]
    price = analysis.get("latest_price")
    sma50 = analysis.get("sma50")
    rsi14 = analysis.get("rsi14")

    if price is None or sma50 is None or rsi14 is None:
        return {
            "symbol": symbol,
            "type": "information",
            "severity": "info",
            "title": f"{symbol} 資料不足",
            "message": (
                "目前未有足夠的價格、均線或 RSI 資料，"
                "暫時不產生方向性提醒。"
            ),
            "reason": "技術指標資料不足",
            "is_actionable": False,
        }

    if price < sma50:
        return {
            "symbol": symbol,
            "type": "risk",
            "severity": "warning",
            "title": f"{symbol} 需要留意下行風險",
            "message": (
                f"{symbol} 現價低於 50 日均線。"
                "這表示近期價格動能較弱，應留意風險，"
                "不代表必然會繼續下跌。"
            ),
            "reason": "價格低於 50 日均線",
            "is_actionable": True,
        }

    if rsi14 >= 70:
        return {
            "symbol": symbol,
            "type": "risk",
            "severity": "warning",
            "title": f"{symbol} 短線可能偏熱",
            "message": (
                f"{symbol} 的 RSI 約為 {rsi14}，進入常見超買參考區。"
                "這不是沽出指令，只表示短線波動和回調風險值得留意。"
            ),
            "reason": "RSI 高於或等於 70",
            "is_actionable": True,
        }

    if rsi14 <= 35:
        return {
            "symbol": symbol,
            "type": "attention",
            "severity": "info",
            "title": f"{symbol} 可能值得觀察",
            "message": (
                f"{symbol} 的 RSI 約為 {rsi14}，進入偏低參考區。"
                "低 RSI 不代表一定反彈，只表示可以加入觀察清單。"
            ),
            "reason": "RSI 低於或等於 35",
            "is_actionable": True,
        }

    if price > sma50 and 35 < rsi14 < 70:
        return {
            "symbol": symbol,
            "type": "attention",
            "severity": "info",
            "title": f"{symbol} 技術面相對穩定",
            "message": (
                f"{symbol} 價格在 50 日均線之上，"
                f"RSI 約為 {rsi14}。目前可視為偏正面觀察，"
                "但仍需配合新聞、估值和個人風險承受能力判斷。"
            ),
            "reason": "價格高於 50 日均線，RSI 未達超買區",
            "is_actionable": True,
        }

    return {
        "symbol": symbol,
        "type": "information",
        "severity": "info",
        "title": f"{symbol} 暫無明顯訊號",
        "message": (
            "目前技術指標沒有符合預設提醒條件，"
            "不代表沒有風險或一定會維持現況。"
        ),
        "reason": "沒有符合預設條件",
        "is_actionable": False,
    }


def build_alerts(
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    將多檔股票分析結果轉成 Alert 清單。
    """

    alerts: list[dict[str, Any]] = []

    for analysis in analyses:
        alert = build_alert(analysis)

        if alert is not None:
            alerts.append(alert)

    return alerts
