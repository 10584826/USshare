"""
新手友善的 Alert 評分引擎。

這些規則不是投資建議，也不是價格預測。
評分只用來整理簡單技術條件，幫助使用者理解目前狀態。
"""

from __future__ import annotations

from typing import Any


def _signal_strength(score: int) -> str:
    """根據分數絕對值判斷訊號強度。"""

    absolute_score = abs(score)

    if absolute_score >= 3:
        return "high"

    if absolute_score >= 2:
        return "medium"

    return "low"


def _build_message(
    symbol: str,
    score: int,
    factors: list[str],
    alert_type: str,
) -> str:
    """建立新手容易理解的 Alert 說明。"""

    factor_text = "；".join(factors)

    if alert_type == "risk":
        return (
            f"{symbol} 目前評分為 {score}，技術條件偏弱或短線風險較高。"
            f"判斷因素：{factor_text}。"
            "這不是沽出指令，請配合新聞、估值和個人風險承受能力判斷。"
        )

    if alert_type == "attention":
        return (
            f"{symbol} 目前評分為 +{score}，有值得觀察的技術條件。"
            f"判斷因素：{factor_text}。"
            "這不是買入指令，不代表價格一定會上升。"
        )

    return (
        f"{symbol} 目前評分為 {score}，沒有形成明確方向性訊號。"
        f"判斷因素：{factor_text or '目前沒有足夠的方向性因素'}。"
        "不代表沒有風險，也不代表未來一定維持現況。"
    )


def build_alert(
    analysis: dict[str, Any],
) -> dict[str, Any] | None:
    """
    根據技術條件建立評分制 Alert。

    評分規則：
    - 價格高於 SMA50：+1
    - 價格低於或等於 SMA50：-2
    - RSI <= 35：+1，代表偏低參考區
    - RSI >= 70：-2，代表短線偏熱
    - 成交量比率 >= 1.2：+1
    - 成交量比率 <= 0.8：-1

    分數：
    - <= -2：risk
    - >= 1：attention
    - 其他：information
    """

    symbol = str(analysis.get("symbol", "UNKNOWN"))
    price = analysis.get("latest_price")
    sma50 = analysis.get("sma50")
    rsi14 = analysis.get("rsi14")
    volume_ratio = analysis.get("volume_ratio_20d")

    required_values = (price, sma50, rsi14)

    if any(value is None for value in required_values):
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
            "factors": ["價格、SMA50 或 RSI 資料不足"],
            "score": 0,
            "signal_strength": "low",
            "is_actionable": False,
        }

    score = 0
    factors: list[str] = []

    if price > sma50:
        score += 1
        factors.append("價格高於 50 日均線")
    else:
        score -= 2
        factors.append("價格低於或等於 50 日均線")

    if rsi14 <= 35:
        score += 1
        factors.append("RSI 處於偏低參考區")
    elif rsi14 >= 70:
        score -= 2
        factors.append("RSI 處於偏高參考區")
    else:
        factors.append("RSI 處於中間區域")

    if volume_ratio is not None:
        if volume_ratio >= 1.2:
            score += 1
            factors.append("成交量高於 20 日平均")
        elif volume_ratio <= 0.8:
            score -= 1
            factors.append("成交量低於 20 日平均")

    if score <= -2:
        alert_type = "risk"
        severity = "warning"
        title = f"{symbol} 風險評分偏高"
        is_actionable = True
    elif score >= 1:
        alert_type = "attention"
        severity = "info"
        title = f"{symbol} 值得觀察"
        is_actionable = True
    else:
        alert_type = "information"
        severity = "info"
        title = f"{symbol} 暫無明確訊號"
        is_actionable = False

    return {
        "symbol": symbol,
        "type": alert_type,
        "severity": severity,
        "title": title,
        "message": _build_message(
            symbol=symbol,
            score=score,
            factors=factors,
            alert_type=alert_type,
        ),
        "reason": "；".join(factors),
        "factors": factors,
        "score": score,
        "signal_strength": _signal_strength(score),
        "is_actionable": is_actionable,
    }


def build_alerts(
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """將多檔股票分析結果轉成 Alert 清單。"""

    alerts: list[dict[str, Any]] = []

    for analysis in analyses:
        alert = build_alert(analysis)

        if alert is not None:
            alerts.append(alert)

    return alerts
