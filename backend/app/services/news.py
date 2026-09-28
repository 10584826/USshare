"""
新聞抓取與簡單情緒分析。

這一層會使用免費的 RSS Feed 來源，例如：
- Yahoo Finance Top Stories
- Reuters business / market RSS
- MarketWatch RSS

目標：
- 只抓取少量重要新聞
- 做簡單正/中/負情緒分類
- 不對新聞做過度解讀
"""

from __future__ import annotations

import re
import time
from typing import Any

import feedparser
import requests


RSS_FEEDS = [
    "https://finance.yahoo.com/rss/topstories",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://feeds.reuters.com/reuters/businessNews",
]

REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 15 * 60
_cache: dict[str, dict[str, Any]] = {}


def clean_text(text: str | None) -> str:
    if not text:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = cleaned.replace("&amp;", "&")
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = cleaned.strip()

    return cleaned


def classify_sentiment(title: str, summary: str = "") -> str:
    """
    用「關鍵字」做基本情緒分類。
    不追求真實語意理解，只做簡單且可控的分類。
    """

    combined = f"{title} {summary}".lower()

    positive_keywords = [
        "rally",
        "surge",
        "jump",
        "upgrade",
        "beat",
        "strong",
        "gain",
        "growth",
        "bullish",
        "boost",
        "improve",
        "higher",
        "positive",
    ]

    negative_keywords = [
        "drop",
        "plunge",
        "selloff",
        "warning",
        "downgrade",
        "miss",
        "weak",
        "loss",
        "pressure",
        "bearish",
        "slump",
        "concern",
        "lower",
        "negative",
        "risk",
    ]

    positive_score = sum(1 for keyword in positive_keywords if keyword in combined)
    negative_score = sum(1 for keyword in negative_keywords if keyword in combined)

    if negative_score > positive_score:
        return "negative"

    if positive_score > negative_score:
        return "positive"

    return "neutral"


def fetch_rss_feed(url: str) -> list[dict[str, Any]]:
    """
    抓取單一 RSS Feed，回傳前 10 篇文章摘要。
    """

    response = requests.get(
        url,
        headers={
            "User-Agent": "USshare/0.2 beginner-stock-analysis-app",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)

    entries: list[dict[str, Any]] = []

    for item in feed.entries[:10]:
        title = clean_text(getattr(item, "title", ""))
        summary = clean_text(getattr(item, "summary", ""))
        link = getattr(item, "link", "")
        published = getattr(item, "published", "")
        sentiment = classify_sentiment(title, summary)

        if not title:
            continue

        entries.append(
            {
                "title": title,
                "summary": summary[:220] if summary else "No summary available.",
                "link": link,
                "published": published,
                "sentiment": sentiment,
            }
        )

    return entries


def get_market_news(limit: int = 6) -> dict[str, Any]:
    """
    取得市場新聞摘要，採用非常保守的免費 RSS 來源。

    返回：
    - top_stories: 文章列表
    - sentiment_summary: 正面 / 中性 / 負面比率
    - disclaimer: 風險提醒
    """

    now = time.time()
    cache_key = "market_news"

    if cache_key in _cache:
        cached = _cache[cache_key]
        if now - cached["timestamp"] < CACHE_TTL_SECONDS:
            return cached["data"]

    all_items: list[dict[str, Any]] = []
    errors: list[str] = []

    for feed_url in RSS_FEEDS:
        try:
            items = fetch_rss_feed(feed_url)
            all_items.extend(items)
        except Exception as error:
            errors.append(f"{feed_url}: {error}")

    # 去重：同標題只保留一篇
    seen = set()
    unique_items: list[dict[str, Any]] = []

    for item in all_items:
        title_key = item.get("title", "").strip().lower()
        if not title_key or title_key in seen:
            continue
        seen.add(title_key)
        unique_items.append(item)

    unique_items = sorted(
        unique_items,
        key=lambda item: item.get("published", ""),
        reverse=True,
    )[:limit]

    sentiment_summary = {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }

    for item in unique_items:
        label = item.get("sentiment", "neutral")
        if label in sentiment_summary:
            sentiment_summary[label] += 1

    result = {
        "top_stories": unique_items,
        "sentiment_summary": sentiment_summary,
        "errors": errors,
        "disclaimer": (
            "新聞情緒僅為簡單摘要，不能代表市場趨勢，"
            "請與技術分析、個人風險承受能力一起看。"
        ),
    }

    _cache[cache_key] = {
        "timestamp": now,
        "data": result,
    }

    return result
