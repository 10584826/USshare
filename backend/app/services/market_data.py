"""
市場資料服務。

資料來源：
Yahoo Finance Chart JSON endpoint。

注意：
- 這是非官方資料介面。
- 只在低頻率、少量股票的前提下使用。
- 不要在每次前端重新整理時都呼叫外部 API。
- 目前加入簡單記憶體快取，避免短時間重複請求。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from .indicators import (
    calculate_rsi,
    calculate_sma,
    calculate_volume_ratio,
    determine_market_status,
)


YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
)

# 只允許安全的美股代號格式。
# 例：AAPL、MSFT、BRK-B、^VIX
MAX_SYMBOL_LENGTH = 10

REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 15 * 60
MAX_RETRIES = 2


@dataclass
class CacheEntry:
    """單一股票資料的記憶體快取項目。"""

    created_at: float
    data: dict[str, Any]


_cache: dict[str, CacheEntry] = {}


class MarketDataError(Exception):
    """市場資料取得或解析失敗。"""


def validate_symbol(symbol: str) -> str:
    """
    驗證股票代號，避免任意字串被拿去組合外部 URL。
    """

    normalized = symbol.strip().upper()

    import re

    if len(normalized) > MAX_SYMBOL_LENGTH:
        raise MarketDataError(
            f"股票代號過長：{normalized}"
        )

    if not re.fullmatch(r"\^?[A-Z][A-Z0-9.-]*", normalized):
        raise MarketDataError(
            f"股票代號格式不正確：{normalized}"
        )

    return normalized


def _request_chart_data(symbol: str) -> dict[str, Any]:
    """
    從 Yahoo Finance 取得日線資料。

    使用 6 個月日線資料：
    - 足夠計算 50 日均線
    - 請求量比即時資料低
    """

    url = YAHOO_CHART_URL.format(symbol=symbol)

    params = {
        "range": "6mo",
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }

    headers = {
        "User-Agent": "USshare/0.1 beginner-stock-analysis-app",
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, dict):
                raise MarketDataError("Yahoo 回傳格式不是 JSON object")

            return payload

        except (requests.RequestException, ValueError) as error:
            last_error = error

            # 指數退避：第 1 次失敗等 1 秒，第 2 次失敗等 2 秒。
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)

    raise MarketDataError(
        f"無法取得 {symbol} 的市場資料：{last_error}"
    )


def _payload_to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    """
    將 Yahoo Chart JSON 轉成 pandas DataFrame。
    """

    chart = payload.get("chart", {})
    results = chart.get("result")

    if not results:
        error_info = chart.get("error")
        raise MarketDataError(
            f"Yahoo 沒有回傳有效資料：{error_info}"
        )

    result = results[0]

    timestamps = result.get("timestamp")
    indicators = result.get("indicators", {})
    quote_items = indicators.get("quote", [])

    if not timestamps or not quote_items:
        raise MarketDataError("Yahoo 回傳資料缺少 timestamp 或 quote")

    quote = quote_items[0]

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        }
    )

    dataframe["date"] = pd.to_datetime(
        dataframe["timestamp"],
        unit="s",
        utc=True,
    )

    dataframe = dataframe.dropna(
        subset=["close", "volume"]
    ).reset_index(drop=True)

    if dataframe.empty:
        raise MarketDataError("清理後沒有有效的市場資料")

    return dataframe


def _build_analysis(symbol: str, dataframe: pd.DataFrame) -> dict[str, Any]:
    """
    對單一股票建立分析結果。
    """

    closes = dataframe["close"].astype(float)
    volumes = dataframe["volume"].astype(float)

    latest_price = round(float(closes.iloc[-1]), 2)
    previous_price = (
        round(float(closes.iloc[-2]), 2)
        if len(closes) >= 2
        else None
    )

    price_change_percent = None

    if previous_price and previous_price != 0:
        price_change_percent = round(
            ((latest_price - previous_price) / previous_price) * 100,
            2,
        )

    sma50 = calculate_sma(closes, window=50)
    rsi14 = calculate_rsi(closes, window=14)
    volume_ratio = calculate_volume_ratio(volumes, window=20)

    status, status_text = determine_market_status(
        price=latest_price,
        sma50=sma50,
        rsi14=rsi14,
    )

    explanation_parts: list[str] = []

    if sma50 is not None:
        if latest_price >= sma50:
            explanation_parts.append("價格在 50 日均線之上")
        else:
            explanation_parts.append("價格在 50 日均線之下")

    if rsi14 is not None:
        if rsi14 < 35:
            explanation_parts.append("RSI 顯示可能偏超賣")
        elif rsi14 > 70:
            explanation_parts.append("RSI 顯示可能偏超買")
        else:
            explanation_parts.append("RSI 位於相對中間區域")

    explanation = "；".join(explanation_parts)

    return {
        "symbol": symbol,
        "latest_price": latest_price,
        "previous_close": previous_price,
        "daily_change_percent": price_change_percent,
        "sma50": sma50,
        "rsi14": rsi14,
        "volume_ratio_20d": volume_ratio,
        "status": status,
        "status_text": status_text,
        "explanation": explanation or "目前資料不足，暫時無法解釋。",
        "data_points": len(dataframe),
        "data_source": "Yahoo Finance Chart endpoint",
    }


def get_symbol_analysis(symbol: str) -> dict[str, Any]:
    """
    取得單一股票分析結果，並套用 15 分鐘快取。
    """

    normalized_symbol = validate_symbol(symbol)

    cached = _cache.get(normalized_symbol)
    now = time.time()

    if cached and now - cached.created_at < CACHE_TTL_SECONDS:
        result = dict(cached.data)
        result["from_cache"] = True
        return result

    payload = _request_chart_data(normalized_symbol)
    dataframe = _payload_to_dataframe(payload)
    result = _build_analysis(normalized_symbol, dataframe)

    _cache[normalized_symbol] = CacheEntry(
        created_at=now,
        data=result,
    )

    result["from_cache"] = False

    return result


def get_market_summary() -> dict[str, Any]:
    """
    取得主要指數摘要。

    如果其中一個代號失敗，不讓整個 API 直接崩潰；
    該代號會回傳 error，其他代號仍可顯示。
    """

    symbols = ["SPY", "QQQ", "DIA", "IWM"]
    indices: list[dict[str, Any]] = []

    for symbol in symbols:
        try:
            indices.append(get_symbol_analysis(symbol))
        except MarketDataError as error:
            indices.append(
                {
                    "symbol": symbol,
                    "status": "unknown",
                    "status_text": "暫時無法取得",
                    "error": str(error),
                }
            )

    try:
        vix = get_symbol_analysis("^VIX")
    except MarketDataError as error:
        vix = {
            "symbol": "^VIX",
            "status": "unknown",
            "status_text": "暫時無法取得",
            "error": str(error),
        }

    return {
        "is_demo": False,
        "indices": indices,
        "vix": vix,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }
