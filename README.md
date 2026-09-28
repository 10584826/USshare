# USshare

面向新手的美股市場分析與提醒 Web App。網站內容僅供參考，不構成投資建議；投資涉及風險，過往表現不代表未來結果。

## 線上網站

網站部署在 GitHub Pages：

https://10584826.github.io/USshare/

GitHub Pages 設定：

- Source: `Deploy from a branch`
- Branch: `gh-pages`
- Folder: `/ (root)`

## 專案架構

```text
Codespaces
    │
    ├── FastAPI 本地開發 API
    ├── React + TypeScript 前端
    └── Python 技術指標與 Alert 引擎

GitHub Actions（每 30 分鐘）
    │
    ├── 取得市場資料
    ├── 計算 SMA50 / RSI14 / 成交量比例
    ├── 抓取 RSS 新聞
    ├── 產生 Dashboard JSON
    ├── 發送 Telegram Alert
    └── 保存 Alert 去重狀態

GitHub Pages
    └── 顯示 frontend/public/dashboard.json
```

## 開發環境

所有開發與測試以 GitHub Codespaces 為主。

```bash
cd /workspaces/USshare
source .venv/bin/activate

python --version
node --version
npm --version
```

執行後端：

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

執行前端：

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

前端測試網址通常是：

```text
http://localhost:5173
```

## Telegram Bot 設定

Telegram 通知是可選功能。沒有設定 Telegram Secrets 時，市場掃描仍可執行，但不會發送通知。

### 1. 建立 Bot

1. 在 Telegram 搜尋 `@BotFather`。
2. 傳送 `/newbot`。
3. 依照指示設定 Bot 名稱和 username。
4. BotFather 會提供一個 Bot Token。

Token 只應保存於密碼管理器或 GitHub Actions Secrets，**不要提交到 Git、README、聊天訊息或前端程式碼**。

### 2. 啟動 Bot

在 Telegram 搜尋新 Bot，按 **Start**，或傳送：

```text
/start
```

### 3. 取得 Chat ID

在 Codespaces Terminal 暫時輸入 Token：

```bash
read -rsp "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
echo
```

查詢 Bot 更新：

```bash
curl -sS \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
```

在 JSON 中尋找：

```json
"chat": {
  "id": 123456789
}
```

`id` 的值就是 `TELEGRAM_CHAT_ID`。

如果使用群組：

1. 把 Bot 加入群組。
2. 在群組傳送一則訊息。
3. 再執行 `getUpdates`。
4. 群組 Chat ID 通常是負數，例如 `-1001234567890`。

測試完成後清除本機變數：

```bash
unset TELEGRAM_BOT_TOKEN
```

### 4. 直接測試 Telegram API

```bash
read -rsp "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
echo
read -rp "Telegram Chat ID: " TELEGRAM_CHAT_ID

export TELEGRAM_BOT_TOKEN
export TELEGRAM_CHAT_ID

curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  --data "$(python - <<'PY'
import json
import os

print(json.dumps({
    "chat_id": os.environ["TELEGRAM_CHAT_ID"],
    "text": (
        "USshare Telegram 測試成功。\\n"
        "僅供參考，不構成投資建議。"
    ),
}))
PY
)"

unset TELEGRAM_BOT_TOKEN
unset TELEGRAM_CHAT_ID
```

成功時應看到：

```json
"ok": true
```

## GitHub CLI 設定

如果 Codespace 顯示 `gh: command not found`，先安裝 GitHub CLI：

```bash
sudo apt-get update
sudo apt-get install -y gh
```

確認版本：

```bash
gh --version
```

登入：

```bash
gh auth login
```

選擇：

```text
GitHub.com
HTTPS
Login with a web browser
```

確認登入帳號和 Repository 權限：

```bash
gh auth status
gh repo view 10584826/USshare
```

## 設定 GitHub Actions Secrets

請在 Codespaces Terminal 使用隱藏輸入，不要把 Secret 寫在指令本身：

```bash
read -rsp "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
echo
read -rp "Telegram Chat ID: " TELEGRAM_CHAT_ID
```

設定 Repository Secrets：

```bash
printf '%s' "$TELEGRAM_BOT_TOKEN" | \
  gh secret set TELEGRAM_BOT_TOKEN \
  --repo 10584826/USshare

printf '%s' "$TELEGRAM_CHAT_ID" | \
  gh secret set TELEGRAM_CHAT_ID \
  --repo 10584826/USshare

printf '%s' "SPY,QQQ,DIA,IWM" | \
  gh secret set WATCHLIST_SYMBOLS \
  --repo 10584826/USshare

unset TELEGRAM_BOT_TOKEN
unset TELEGRAM_CHAT_ID
```

確認 Secret 名稱存在：

```bash
gh secret list --repo 10584826/USshare
```

GitHub 只會顯示 Secret 名稱，不會顯示 Secret 實際內容，這是正常的。預期至少包括：

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
WATCHLIST_SYMBOLS
```

也可以在 GitHub 網頁設定：

```text
Repository
→ Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

## 手動執行 Stock Scan

Workflow 檔案：

```text
.github/workflows/stock-scan.yml
```

正式 GitHub Actions 應使用：

```yaml
DRY_RUN: "false"
```

使用 GitHub CLI 執行：

```bash
gh workflow run stock-scan.yml \
  --repo 10584826/USshare \
  --ref main
```

查看最近執行：

```bash
gh run list \
  --repo 10584826/USshare \
  --workflow stock-scan.yml \
  --limit 5
```

等待最新執行完成：

```bash
RUN_ID=$(gh run list \
  --repo 10584826/USshare \
  --workflow stock-scan.yml \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')

gh run watch "$RUN_ID" \
  --repo 10584826/USshare \
  --exit-status
```

不用 GitHub CLI 時，也可以在 GitHub 網頁執行：

```text
Actions
→ Stock Scan
→ Run workflow
→ Branch: main
→ Run workflow
```

## 第一次 Telegram 通知測試

Workflow 成功後，拉取 GitHub Actions 產生的 commit：

```bash
git fetch origin
git merge --no-ff origin/main -m "merge: sync generated dashboard data"
```

如果沒有本機 commit 分叉，也可以使用：

```bash
git pull --ff-only
```

查看 Dashboard 中的通知結果：

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(
    Path("data/dashboard.json").read_text(encoding="utf-8")
)

for alert in payload["watchlist"]["alerts"]:
    print(
        alert["symbol"],
        "| telegram_sent=",
        alert.get("telegram_sent"),
        "| telegram_reason=",
        alert.get("telegram_reason"),
    )
PY
```

第一次成功發送時，至少一個 Alert 應顯示：

```text
telegram_sent=True
```

同時 Telegram 應收到 `USshare Alert` 訊息。

查看通知去重狀態：

```bash
cat data/alert-state.json
```

成功發送的 Alert 會保留在狀態檔，例如：

```json
{
  "DIA|risk|價格低於 50 日均線": {
    "symbol": "DIA",
    "type": "risk",
    "reason": "價格低於 50 日均線",
    "last_sent_at": 1790000000.0,
    "last_sent_at_iso": "2026-09-28T00:00:00+00:00"
  }
}
```

## 第二次去重測試

立即再次執行相同 workflow：

```bash
gh workflow run stock-scan.yml \
  --repo 10584826/USshare \
  --ref main
```

等待完成、拉取結果後，再執行：

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(
    Path("data/dashboard.json").read_text(encoding="utf-8")
)

for alert in payload["watchlist"]["alerts"]:
    print(
        alert["symbol"],
        "| telegram_sent=",
        alert.get("telegram_sent"),
        "| telegram_reason=",
        alert.get("telegram_reason"),
    )
PY
```

相同股票、相同 Alert 類型和相同原因，在 24 小時冷卻時間內應顯示：

```text
telegram_sent=False
telegram_reason=cooldown active
```

Telegram 不應收到第二則相同通知。

### 去重規則

- 新 Alert：發送通知。
- 相同股票、類型和原因：24 小時內不重複發送。
- Alert 原因改變：視為新 Alert，可以發送。
- Telegram 發送失敗：不記錄為成功，下次可以重試。
- `DRY_RUN=true`：不發送 Telegram，也不更新成功發送狀態。

## 本機 Dry Run 測試

本機測試請使用 Dry Run，避免意外發送 Telegram：

```bash
cd /workspaces/USshare
source .venv/bin/activate

DRY_RUN=true python -m backend.app.cron_scan
```

查看結果：

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(
    Path("data/dashboard.json").read_text(encoding="utf-8")
)

for alert in payload["watchlist"]["alerts"]:
    print(alert["symbol"], alert.get("telegram_reason"))
PY
```

預期顯示：

```text
dry run mode
```

這代表本機沒有發送 Telegram，是正常結果。

## 測試與建置

```bash
source .venv/bin/activate
pytest -q
python -m compileall backend
npm --prefix frontend run build
```

## 常見問題

### `gh: command not found`

```bash
sudo apt-get update
sudo apt-get install -y gh
gh auth login
```

### `401 Unauthorized`

Bot Token 無效或已失效。請到 `@BotFather` 重新取得 Token，然後覆蓋 `TELEGRAM_BOT_TOKEN` Secret。

### `chat not found`

請確認：

- 已對私人 Bot 按 `/start`。
- Bot 已加入目標群組。
- `TELEGRAM_CHAT_ID` 沒有多餘空白。
- 群組 Chat ID 通常是負數。

### 沒有收到通知，但 Workflow 成功

查看 Dashboard：

```bash
python - <<'PY'
import json
from pathlib import Path

payload = json.loads(
    Path("data/dashboard.json").read_text(encoding="utf-8")
)

print("alerts:", len(payload["watchlist"]["alerts"]))
print("errors:", payload["watchlist"]["errors"])
PY
```

如果 `alerts` 是 `0`，代表這次沒有符合 Alert 條件，不一定是 Telegram 設定錯誤。

### `telegram_reason=dry run mode`

你查看的是本機 Dry Run 結果，或 workflow 的 `DRY_RUN` 仍是 `true`。正式 GitHub Actions 應為：

```yaml
DRY_RUN: "false"
```

### `git pull --ff-only` 失敗

GitHub Actions 可能已經推送新 commit，而 Codespace 本地也有 commit，導致分支分叉。先執行：

```bash
git fetch origin
git status
git merge --no-ff origin/main -m "merge: sync generated dashboard data"
```

處理衝突時，對 `dashboard.json` 和 `alert-state.json` 優先保留 GitHub Actions 最新生成版本；對 Python 或 workflow 程式碼則需要人工檢查。

## 安全注意事項

- 不要把 Telegram Token 提交到 Git。
- 不要把 Token 放在 React 前端或 `frontend/public/`。
- 不要把真實 Token 貼到聊天、Issue 或公開 log。
- `.env` 不應提交；只提交 `.env.example`。
- GitHub Actions Secret 只用於 workflow，不應輸出到 log。
- Alert 只供參考，不是買入、沽出或減倉指令。
