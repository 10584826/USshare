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
  telegram_sent?: boolean;
};

type NewsItem = {
  title: string;
  summary: string;
  link: string;
  published: string;
  sentiment: "positive" | "neutral" | "negative";
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

type NewsResponse = {
  top_stories: NewsItem[];
  sentiment_summary: {
    positive: number;
    neutral: number;
    negative: number;
  };
  errors: string[];
  disclaimer: string;
};

type DashboardSnapshot = {
  generated_at: string;
  market: MarketSummary;
  watchlist: AlertsResponse;
  news: NewsResponse;
  disclaimer: string;
};

async function loadDashboardSnapshot(): Promise<DashboardSnapshot> {
  const response = await fetch("/dashboard.json", {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Unable to load dashboard snapshot");
  }

  return response.json();
}

function App() {
  const [marketSummary, setMarketSummary] =
    useState<MarketSummary | null>(null);

  const [alertsResponse, setAlertsResponse] =
    useState<AlertsResponse | null>(null);

  const [newsResponse, setNewsResponse] =
    useState<NewsResponse | null>(null);

  const [generatedAt, setGeneratedAt] =
    useState<string | null>(null);

  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function loadData() {
      try {
        const snapshot = await loadDashboardSnapshot();

        setMarketSummary(snapshot.market);
        setAlertsResponse(snapshot.watchlist);
        setNewsResponse(snapshot.news);
        setGeneratedAt(snapshot.generated_at);
      } catch {
        setError("暫時無法載入分析結果，請稍後再試。");
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

      {generatedAt && (
        <p className="updated-time">
          最近更新：{" "}
          {new Date(generatedAt).toLocaleString("zh-HK")}
        </p>
      )}

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
                      最新價格：{" "}
                      {index.latest_price ?? "暫無"}
                    </p>

                    <p>
                      今日變化：{" "}
                      {index.daily_change_percent !== null &&
                      index.daily_change_percent !== undefined
                        ? `${index.daily_change_percent}%`
                        : "暫無"}
                    </p>

                    <p>
                      50 日均線：{" "}
                      {index.sma50 ?? "資料不足"}
                    </p>

                    <p>
                      RSI：{" "}
                      {index.rsi14 ?? "資料不足"}
                    </p>

                    <p className={`status ${index.status}`}>
                      {index.status_text}
                    </p>

                    <p className="explanation">
                      {index.explanation ?? "暫無詳細說明。"}
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

        {alertsResponse?.alerts.map((alert, index) => (
          <article
            className={`alert-card ${alert.type}`}
            key={`${alert.symbol}-${alert.reason}-${index}`}
          >
            <div className="alert-header">
              <strong>{alert.symbol}</strong>
              <span>{alert.title}</span>
            </div>

            <p>{alert.message}</p>

            <small>判斷原因：{alert.reason}</small>
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

      <section className="news-section">
        <div className="section-title">
          <h2>新聞簡要</h2>

          {newsResponse && (
            <span className="demo-badge">
              正面 {newsResponse.sentiment_summary.positive}
              {" · "}
              中性 {newsResponse.sentiment_summary.neutral}
              {" · "}
              負面 {newsResponse.sentiment_summary.negative}
            </span>
          )}
        </div>

        {!newsResponse && !error && (
          <p className="info">正在載入新聞摘要...</p>
        )}

        {newsResponse?.top_stories.map((news, index) => (
          <article
            className={`news-card ${news.sentiment}`}
            key={`${news.title}-${index}`}
          >
            <div className="news-header">
              <span className={`pill ${news.sentiment}`}>
                {news.sentiment}
              </span>

              <small>{news.published || "未知時間"}</small>
            </div>

            <h3>{news.title}</h3>

            <p>{news.summary}</p>

            {news.link && (
              <a
                href={news.link}
                target="_blank"
                rel="noreferrer"
              >
                閱讀原文
              </a>
            )}
          </article>
        ))}

        {newsResponse?.top_stories.length === 0 && (
          <p className="info">目前沒有可顯示的新聞。</p>
        )}

        <p className="disclaimer">
          {newsResponse?.disclaimer}
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
            VIX：{" "}
            {marketSummary.vix.latest_price ?? "暫無"}
          </p>
        )}
      </section>

      <footer>
        <p>
          USshare v0.5.0 · 僅供參考，不構成投資建議
        </p>
      </footer>
    </main>
  );
}

export default App;
