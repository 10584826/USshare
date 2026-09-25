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

type AlertItem = {
  symbol: string;
  type: "attention" | "risk" | "information";
  severity: "info" | "warning";
  title: string;
  message: string;
  reason: string;
  is_actionable: boolean;
};

type MarketSummary = {
  is_demo: boolean;
  indices: StockAnalysis[];
  vix: StockAnalysis;
};

type AlertsResponse = {
  watchlist: string[];
  analyses: StockAnalysis[];
  alerts: AlertItem[];
  errors: Array<{
    symbol: string;
    error: string;
  }>;
  scanned_count: number;
  failed_count: number;
  disclaimer: string;
};

function App() {
  const [marketSummary, setMarketSummary] =
    useState<MarketSummary | null>(null);
  const [alertsResponse, setAlertsResponse] =
    useState<AlertsResponse | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function loadData() {
      try {
        const [marketResponse, alertsResponse] = await Promise.all([
          fetch("/api/market-summary"),
          fetch("/api/alerts"),
        ]);

        if (!marketResponse.ok || !alertsResponse.ok) {
          throw new Error("API response error");
        }

        const marketData: MarketSummary = await marketResponse.json();
        const alertData: AlertsResponse = await alertsResponse.json();

        setMarketSummary(marketData);
        setAlertsResponse(alertData);
      } catch {
        setError(
          "暫時無法連接後端，請確認 Port 8000 的 API 正在運行。",
        );
      }
    }

    loadData();
  }, []);

  return (
    <main className="page">
      <header className="header">
        <p className="eyebrow">USshare</p>
        <h1>美股新手分析助手</h1>
        <p className="subtitle">
          用簡單方式了解市場狀態，不追求預測每一次升跌。
        </p>
      </header>

      <section className="warning">
        <strong>重要風險提示</strong>
        <p>
          本網站內容僅供參考，不構成投資建議。
          投資涉及風險，過往表現不代表未來結果。
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      <section>
        <div className="section-title">
          <h2>市場概況</h2>
          <span className="demo-badge">
            {marketSummary?.is_demo ? "示範資料" : "資料可能延遲"}
          </span>
        </div>

        {!marketSummary && !error && (
          <p className="info">正在載入市場資料...</p>
        )}

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
                      {index.latest_price ?? "暫無"}
                    </p>

                    <p>
                      今日變化：
                      {index.daily_change_percent !== null &&
                      index.daily_change_percent !== undefined
                        ? `${index.daily_change_percent}%`
                        : "暫無"}
                    </p>

                    <p>
                      50 日均線：
                      {index.sma50 ?? "資料不足"}
                    </p>

                    <p>
                      RSI：
                      {index.rsi14 ?? "資料不足"}
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

      <section className="alerts-section">
        <div className="section-title">
          <h2>最新提醒</h2>
          {alertsResponse && (
            <span className="demo-badge">
              已掃描 {alertsResponse.scanned_count} 檔
            </span>
          )}
        </div>

        {!alertsResponse && !error && (
          <p className="info">正在產生提醒...</p>
        )}

        {alertsResponse?.alerts.map((alert) => (
          <article
            className={`alert-card ${alert.type}`}
            key={`${alert.symbol}-${alert.reason}`}
          >
            <div className="alert-header">
              <strong>{alert.symbol}</strong>
              <span>{alert.title}</span>
            </div>

            <p>{alert.message}</p>

            <small>
              判斷原因：{alert.reason}
            </small>
          </article>
        ))}

        {alertsResponse?.alerts.length === 0 && (
          <p className="info">目前沒有符合條件的提醒。</p>
        )}

        {alertsResponse?.failed_count ? (
          <p className="error">
            有 {alertsResponse.failed_count} 檔股票暫時無法取得資料。
          </p>
        ) : null}

        <p className="disclaimer">
          {alertsResponse?.disclaimer}
        </p>
      </section>

      <section className="vix-card">
        <h2>VIX 波動風險參考</h2>

        {!marketSummary?.vix ? (
          <p>載入中...</p>
        ) : marketSummary.vix.error ? (
          <p className="error">{marketSummary.vix.error}</p>
        ) : (
          <p>
            VIX：
            {marketSummary.vix.latest_price ?? "暫無"}
          </p>
        )}
      </section>

      <footer>
        <p>USshare v0.3.0 · 僅供參考，不構成投資建議</p>
      </footer>
    </main>
  );
}

export default App;
