"""
應用程式設定。

股票清單可以透過 .env 的 WATCHLIST_SYMBOLS 修改。
初期限制最多 30 檔，避免免費資料來源被大量請求。
"""

from __future__ import annotations

import os


DEFAULT_WATCHLIST = [
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
]


def get_watchlist() -> list[str]:
    """
    讀取 WATCHLIST_SYMBOLS。

    例如：
    WATCHLIST_SYMBOLS=SPY,QQQ,MSFT,AAPL,NVDA
    """

    raw_symbols = os.getenv("WATCHLIST_SYMBOLS", "")

    if not raw_symbols.strip():
        return DEFAULT_WATCHLIST.copy()

    symbols: list[str] = []

    for raw_symbol in raw_symbols.split(","):
        symbol = raw_symbol.strip().upper()

        if symbol and symbol not in symbols:
            symbols.append(symbol)

    # 免費資料源與低頻掃描策略下，最多監控 30 檔。
    return symbols[:30]
