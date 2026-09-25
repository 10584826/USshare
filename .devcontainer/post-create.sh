#!/usr/bin/env bash

set -e

echo "Initializing Stock Alert App development environment..."

# 建立 Python 虛擬環境
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

# 啟用虛擬環境並更新 pip
source .venv/bin/activate
python -m pip install --upgrade pip

# 建立基本 Python 套件清單，稍後會再擴充
if [ ! -f "requirements.txt" ]; then
  touch requirements.txt
fi

# 如果未來存在 package.json，則自動安裝 Node.js 套件
if [ -f "package.json" ]; then
  npm install
fi

echo "Development environment is ready."
