"""
USshare 後端入口。

目前只提供健康檢查 API。
後續會在這裡加入：
- 股票資料 API
- 技術指標分析
- Alert 引擎
- Telegram 通知
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="USshare API",
    description="面向新手的美股分析與提醒 API",
    version="0.1.0",
)


# 開發階段允許前端從 localhost:5173 呼叫後端。
# 部署到正式環境時，應改成指定的正式網域。
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
    暫時提供示範用市場狀態。

    這些不是即時資料，只是讓前端先有固定格式可以顯示。
    後續會改為由市場資料服務計算。
    """

    return {
        "is_demo": True,
        "message": "目前為示範資料，尚未連接即時市場數據。",
        "indices": [
            {
                "symbol": "SPY",
                "name": "S&P 500 ETF",
                "status": "neutral",
                "status_text": "中性",
            },
            {
                "symbol": "QQQ",
                "name": "Nasdaq 100 ETF",
                "status": "neutral",
                "status_text": "中性",
            },
            {
                "symbol": "DIA",
                "name": "Dow Jones ETF",
                "status": "neutral",
                "status_text": "中性",
            },
            {
                "symbol": "IWM",
                "name": "Russell 2000 ETF",
                "status": "neutral",
                "status_text": "中性",
            },
        ],
        "vix": {
            "value": None,
            "status": "unknown",
            "message": "VIX 尚未連接，即將加入。",
        },
    }
