"""
新聞抓取與簡單情緒分析。

新聞資料只作為市場背景參考，不代表投資建議。
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import requests


RSS_FEEDS = [
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/rss/topstories",
    },
    {
        "name": "MarketWatch",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
    },
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
    },
]

REQUEST_TIMEOUT_SECONDS = 10
CACHE_TTL_SECONDS = 15 * 60
DEFAULT_MAX_AGE_HOURS = 72

# 只保留較可能與金融市場相關的文章。
RELEVANCE_KEYWORDS = (
    "stock",
    "stocks",
    "shares",
    "market",
    "markets",
    "earnings",
    "revenue",
    "profit",
    "loss",
    "guidance",
    "forecast",
    "fed",
    "interest rate",
    "inflation",
    "economy",
    "economic",
    "investor",
    "nasdaq",
    "s&p",
    "dow",
    "nyse",
    "ipo",
    "merger",
    "acquisition",
    "upgrade",
    "downgrade",
    "etf",
    "bond",
    "treasury",
)

_cache: dict[str, dict[str, Any]] = {}


def clean_text(text: str | None) -> str:
    """移除 HTML 和多餘空白。"""

    if not text:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = cleaned.replace("&amp;", "&")
    cleaned = cleaned.replace("&nbsp;", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def classify_sentiment(title: str, summary: str = "") -> str:
    """用可控關鍵字做簡單情緒分類。"""

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

    positive_score = sum(
        1 for keyword in positive_keywords if keyword in combined
    )
    negative_score = sum(
        1 for keyword in negative_keywords if keyword in combined
    )

    if negative_score > positive_score:
        return "negative"

    if positive_score > negative_score:
        return "positive"

    return "neutral"


def _get_max_age_hours() -> int:
    value = os.getenv(
        "NEWS_MAX_AGE_HOURS",
        str(DEFAULT_MAX_AGE_HOURS),
    )

    try:
        parsed = int(value)
    except ValueError:
        return DEFAULT_MAX_AGE_HOURS

    return max(1, parsed)


def _parse_published_datetime(item: Any) -> datetime | None:
    """解析 RSS 的 published 或 updated 時間。"""

    parsed_time = getattr(item, "published_parsed", None)

    if parsed_time:
        try:
            return datetime(
                parsed_time.tm_year,
                parsed_time.tm_mon,
                parsed_time.tm_mday,
                parsed_time.tm_hour,
                parsed_time.tm_min,
                parsed_time.tm_sec,
                tzinfo=timezone.utc,
            )
        except (AttributeError, TypeError, ValueError):
            pass

    raw_values = [
        getattr(item, "published", ""),
        getattr(item, "updated", ""),
    ]

    for raw_value in raw_values:
        if not raw_value:
            continue

        try:
            parsed = parsedate_to_datetime(raw_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue

    return None


def _is_relevant(title: str, summary: str) -> bool:
    combined = f"{title} {summary}".lower()
    return any(keyword in combined for keyword in RELEVANCE_KEYWORDS)


def _build_news_item(
    item: Any,
    source_name: str,
) -> dict[str, Any] | None:
    title = clean_text(getattr(item, "title", ""))
    summary = clean_text(getattr(item, "summary", ""))
    link = str(getattr(item, "link", "") or "").strip()

    if not title:
        return None

    if not _is_relevant(title, summary):
        return None

    published_datetime = _parse_published_datetime(item)
    now = datetime.now(timezone.utc)

    if published_datetime:
        age_hours = round(
            max(
                0.0,
                (now - published_datetime).total_seconds() / 3600,
            ),
            2,
        )
        published_at = published_datetime.isoformat()
        published_display = published_datetime.strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    else:
        age_hours = None
        published_at = None
        published_display = "時間未知"

    return {
        "title": title,
        "summary": summary[:220] if summary else "No summary available.",
        "link": link,
        "source": source_name,
        "published": published_display,
        "published_at": published_at,
        "age_hours": age_hours,
        "sentiment": classify_sentiment(title, summary),
    }


def fetch_rss_feed(
    feed_url: str,
    source_name: str,
) -> list[dict[str, Any]]:
    """抓取單一 RSS Feed。"""

    response = requests.get(
        feed_url,
        headers={
            "User-Agent": "USshare/0.5 beginner-stock-analysis-app",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    entries: list[dict[str, Any]] = []

    for item in feed.entries[:20]:
        news_item = _build_news_item(item, source_name)

        if news_item is not None:
            entries.append(news_item)

    return entries


def _deduplicate_items(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """依 URL，再依標題去重。"""

    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    unique_items: list[dict[str, Any]] = []

    for item in items:
        link = item.get("link", "").strip().lower()
        title = item.get("title", "").strip().lower()

        if link and link in seen_links:
            continue

        if title and title in seen_titles:
            continue

        if link:
            seen_links.add(link)

        if title:
            seen_titles.add(title)

        unique_items.append(item)

    return unique_items


def get_market_news(limit: int = 6) -> dict[str, Any]:
    """
    取得市場新聞摘要。

    預設只保留最近 72 小時內、較可能與金融市場相關的新聞。
    可用 NEWS_MAX_AGE_HOURS 調整。
    """

    now = time.time()
    cache_key = "market_news"

    if cache_key in _cache:
        cached = _cache[cache_key]

        if now - cached["timestamp"] < CACHE_TTL_SECONDS:
            return cached["data"]

    all_items: list[dict[str, Any]] = []
    errors: list[str] = []

    max_age_hours = _get_max_age_hours()

    for feed in RSS_FEEDS:
        try:
            items = fetch_rss_feed(
                feed_url=feed["url"],
                source_name=feed["name"],
            )
            all_items.extend(items)
        except Exception as error:
            errors.append(f"{feed['name']}: {error}")

    fresh_items: list[dict[str, Any]] = []
    unknown_age_items: list[dict[str, Any]] = []

    for item in all_items:
        age_hours = item.get("age_hours")

        if age_hours is None:
            unknown_age_items.append(item)
        elif age_hours <= max_age_hours:
            fresh_items.append(item)

    unique_items = _deduplicate_items(
        fresh_items + unknown_age_items
    )

    unique_items.sort(
        key=lambda item: (
            item.get("age_hours") is None,
            item.get("age_hours")
            if item.get("age_hours") is not None
            else 999999,
        )
    )

    unique_items = unique_items[:limit]

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
        "max_age_hours": max_age_hours,
        "filtered_count": max(0, len(all_items) - len(fresh_items)),
        "disclaimer": (
            "新聞情緒僅為簡單摘要，不能代表市場趨勢。"
            "新聞時間和內容可能不完整，請閱讀原文核對。"
        ),
    }

    _cache[cache_key] = {
        "timestamp": now,
        "data": result,
    }

    return result
