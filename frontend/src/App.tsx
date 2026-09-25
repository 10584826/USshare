import { useEffect, useState } from "react";
import "./App.css";

type StockAnalysis = {
  symbol: string;
  latest_price?: number;
  daily_change_percent?: number | null;
  sma50?: number | null;
  rsi14?: number | null;
  volume_ratio_20d?: number | null;
  status: string;
  status_text: string;
  explanation?: string;
  error?: string;
};

type MarketSummary = {
  is_demo: boolean;
  indices: StockAnalysis[];
  vix: StockAnalysis;
};

function App() {
  const [marketSummary, setMarketSummary] =
    useState<MarketSummary | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function loadMarketSummary() {
      try {
        const response = await fetch(
          "http://localhost:8000/api/market-summary",
        );

        if (!response.ok) {
          throw new Error("後端回應錯誤");
        }

        const data: MarketSummary = await response.json();
        setMarketSummary(data);
      } catch {
        setError("暫時無法連接後端，請確認 Port 8000 正在運行。");
      }
    }

    loadMarketSummary();
  }, []);

  return (
    <main className="page">
      <header className="header">
        <div>
          <p className="eyebrow">USshare</p>
          <h1>美股新手分析助手</h1>
          <p className="subtitle">
            用簡單方式了解市場狀態，不追求預測每一次升跌。
          </p>
        </div>
      </header>

      <section className="warning">
        <strong>重要風險提示</strong>
        <p>
          本網站內容僅供參考，不構成投資建議。投資涉及風險，過往表現不代表未來結果。
        </p>
      </section>

      <section>
        <div className="section-title">
          <h2>市場概況</h2>
          <span className="demo-badge">
            {marketSummary?.is_demo ? "示範資料" : "即時資料可能延遲"}
          </span>
        </div>

        {error && <p className="error">{error}</p>}

        {!marketSummary && !error && <p className="info">正在載入市場資料...</p>}

        {marketSummary && (
          <div className="cards">
            {marketSummary.indices.map((index) => (
              <article className="market-card" key={index.symbol}>
                <p className="symbol">{index.symbol}</p>

                {index.error ? (
                  <p className="error">{index.error}</p>
                ) : (
                  <>
                    <h3>{index.status_text}</h3>

                    <p>
                      最新價格：
                      {index.latest_price !== undefined
                        ? ` ${index.latest_price}`
                        : " 暫無"}
                    </p>

                    <p>
                      今日變化：
                      {index.daily_change_percent !== null &&
                      index.daily_change_percent !== undefined
                        ? ` ${index.daily_change_percent}%`
                        : " 暫無"}
                    </p>

                    <p>
                      50 日均線：
                      {index.sma50 !== null && index.sma50 !== undefined
                        ? ` ${index.sma50}`
                        : " 資料不足"}
                    </p>

                    <p>
                      RSI：
                      {index.rsi14 !== null && index.rsi14 !== undefined
                        ? ` ${index.rsi14}`
                        : " 資料不足"}
                    </p>

                    <p className={`status ${index.status}`}>
                      {index.status_text}
                    </p>

                    <p className="explanation">
                      {index.explanation}
                    </p>
                  </>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="vix-card">
        <h2>VIX 波動風險參考</h2>

        {!marketSummary?.vix ? (
          <p>載入中...</p>
        ) : marketSummary.vix.error ? (
          <p className="error">{marketSummary.vix.error}</p>
        ) : (
          <>
            <p>
              VIX：
              {marketSummary.vix.latest_price !== undefined
                ? ` ${marketSummary.vix.latest_price}`
                : " 暫無"}
            </p>
            <p>
              這只是一項波動參考，不代表市場必然上升或下跌。
            </p>
          </>
        )}
      </section>

      <footer>
        <p>USshare v0.2.0 · 僅供參考，不構成投資建議</p>
      </footer>
    </main>
  );
}

export default App;
