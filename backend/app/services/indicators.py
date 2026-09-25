"""
簡單技術指標計算。

本檔案只處理數學計算，不負責：
- 呼叫外部 API
- 儲存資料
- 發送通知

這樣可以讓資料抓取和分析邏輯分開，方便測試。
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


def calculate_sma(
    prices: pd.Series,
    window: int = 50,
) -> Optional[float]:
    """
    計算簡單移動平均線 Simple Moving Average。

    如果資料少於 window 筆，暫時無法計算完整均線，
    因此回傳 None。
    """

    if len(prices) < window:
        return None

    value = prices.rolling(window=window).mean().iloc[-1]

    if pd.isna(value):
        return None

    return round(float(value), 2)


def calculate_rsi(
    prices: pd.Series,
    window: int = 14,
) -> Optional[float]:
    """
    計算 RSI。

    使用簡化版 Wilder RSI 概念：
    1. 計算每日價格變化
    2. 分開計算平均上升和平均下跌
    3. 轉換成 0 到 100 的 RSI

    RSI 越低不代表一定會上升，RSI 越高也不代表一定會下跌。
    它只是其中一項參考資料。
    """

    if len(prices) < window + 1:
        return None

    delta = prices.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(window=window).mean()
    average_loss = losses.rolling(window=window).mean()

    latest_gain = average_gain.iloc[-1]
    latest_loss = average_loss.iloc[-1]

    if pd.isna(latest_gain) or pd.isna(latest_loss):
        return None

    # 如果最近沒有下跌，RSI 可視為非常強。
    if latest_loss == 0:
        return 100.0

    relative_strength = latest_gain / latest_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return round(float(rsi), 2)


def calculate_volume_ratio(
    volumes: pd.Series,
    window: int = 20,
) -> Optional[float]:
    """
    計算最新成交量相對於過去平均成交量的比例。

    例如：
    - 1.00 = 接近平均
    - 1.50 = 約為平均的 1.5 倍
    - 0.50 = 約為平均的一半
    """

    if len(volumes) < window + 1:
        return None

    historical_average = volumes.iloc[-(window + 1):-1].mean()
    latest_volume = volumes.iloc[-1]

    if historical_average <= 0:
        return None

    ratio = latest_volume / historical_average

    return round(float(ratio), 2)


def determine_market_status(
    price: Optional[float],
    sma50: Optional[float],
    rsi14: Optional[float],
) -> tuple[str, str]:
    """
    將數值轉成新手容易理解的市場狀態。

    這不是買賣建議，只是簡化分類：
    - bullish: 偏多
    - neutral: 中性
    - bearish: 偏空
    """

    if price is None or sma50 is None or rsi14 is None:
        return "unknown", "資料不足"

    if price > sma50 and 40 <= rsi14 <= 70:
        return "bullish", "偏多"

    if price < sma50 and rsi14 < 45:
        return "bearish", "偏空"

    return "neutral", "中性"
