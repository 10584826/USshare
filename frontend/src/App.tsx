import { useEffect, useState } from "react";
import "./App.css";

type IndexStatus = {
  symbol: string;
  name: string;
  status: string;
  status_text: string;
};

type MarketSummary = {
  is_demo: boolean;
  message: string;
  indices: IndexStatus[];
  vix: {
    value: number | null;
    status: string;
    message: string;
  };
};

function App() {
  const [marketSummary, setMarketSummary] =
    useState<MarketSummary | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function loadMarketSummary() {
      try {
        const response = await fetch("http://localhost:8000/api/market-summary");

        if (!response.ok) {
          throw new Error("後端回應錯誤");
        }

        const data: MarketSummary = await response.json();
        setMarketSummary(data);
      } catch {
        setError("暫時無法連接後端，請確認 Port 8000 的 API 正在運行。");
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
          <span className="demo-badge">目前為示範資料</span>
        </div>

        {error && <p className="error">{error}</p>}

        {marketSummary && (
          <>
            <p className="info">{marketSummary.message}</p>

            <div className="cards">
              {marketSummary.indices.map((index) => (
                <article className="market-card" key={index.symbol}>
                  <p className="symbol">{index.symbol}</p>
                  <h3>{index.name}</h3>
                  <p className={`status ${index.status}`}>
                    {index.status_text}
                  </p>
                </article>
              ))}
            </div>
          </>
        )}
      </section>

      <section className="vix-card">
        <h2>波動風險參考</h2>
        <p>{marketSummary?.vix.message ?? "載入中..."}</p>
      </section>

      <footer>
        <p>USshare v0.1.0 · 僅供參考，不構成投資建議</p>
      </footer>
    </main>
  );
}

export default App;
