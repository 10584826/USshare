"""
USshare FastAPI 後端入口。
"""

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .services.market_data import (
    MarketDataError,
    get_market_summary,
    get_symbol_analysis,
)


app = FastAPI(
    title="USshare API",
    description="面向新手的美股分析與提醒 API",
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict:
    """確認後端服務是否正常運行。"""

    return {
        "status": "ok",
        "service": "USshare API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/market-summary")
def market_summary() -> dict:
    """
    回傳 SPY、QQQ、DIA、IWM 和 VIX 的技術指標摘要。
    """

    return get_market_summary()


@app.get("/api/stock/{symbol}")
def stock_analysis(symbol: str) -> dict:
    """
    回傳指定股票的技術分析。

    目前只允許少量預先設定的代號，
    避免初期任意掃描大量股票。
    """

    try:
        return get_symbol_analysis(symbol)

    except MarketDataError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    except Exception as error:
        # 不把完整 traceback 或敏感內部資訊回傳給前端。
        raise HTTPException(
            status_code=500,
            detail="分析股票時發生未預期錯誤。",
        ) from error
