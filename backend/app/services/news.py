"""
新聞抓取與保守的市場相關性／情緒分析。

新聞只作為市場背景參考，不代表投資建議。
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

# 只保留較明確的金融／市場字眼。
MARKET_KEYWORDS = (
    "stock",
    "stocks",
    "shares",
    "market",
    "markets",
    "earnings",
    "revenue",
    "profit",
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
    "wall street",
    "quarter",
    "quarterly",
    "analyst",
)

POSITIVE_KEYWORDS = (
    "rally",
    "surge",
    "jump",
    "upgrade",
    "beat estimates",
    "beat expectations",
    "strong earnings",
    "revenue growth",
    "profit growth",
    "bullish",
    "boost",
    "improve",
    "higher guidance",
    "raised forecast",
    "outperform",
)

NEGATIVE_KEYWORDS = (
    "plunge",
    "selloff",
    "warning",
    "downgrade",
    "miss estimates",
    "miss expectations",
    "weak earnings",
    "revenue decline",
    "profit decline",
    "bearish",
    "slump",
    "concern",
    "lower guidance",
    "cut forecast",
    "underperform",
    "layoffs",
    "investigation",
    "lawsuit",
    "bankruptcy",
)

# 這些字眼通常代表個人理財／生活文章，
# 不應只因為出現 finance、equity 或 positive 就列為股票新聞。
PERSONAL_FINANCE_PATTERNS = (
    "sell my house",
    "selling my house",
    "mortgage",
    "credit card debt",
    "social security",
    "retirement income",
    "retire comfortably",
    "paycheck",
    "my salary",
    "my pension",
    "personal finance",
    "house renovation",
    "renovating my house",
    "inheritance",
    "should i sell",
    "am i crazy",
    "living paycheck to paycheck",
)

# 常見 watchlist 代號的公司名稱。
# 未列出的股票仍會使用代號直接匹配。
SYMBOL_ALIASES = {
    "AAPL": ("apple",),
    "MSFT": ("microsoft",),
    "NVDA": ("nvidia",),
    "AMZN": ("amazon",),
    "GOOGL": ("alphabet", "google"),
    "META": ("meta", "facebook"),
    "TSLA": ("tesla",),
    "SPY": ("spy", "s&p 500", "sp 500"),
    "QQQ": ("qqq", "nasdaq 100", "nasdaq-100"),
    "DIA": ("dia", "dow jones"),
    "IWM": ("iwm", "russell 2000"),
}

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


def _normalise_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _build_symbol_aliases(
    symbols: list[str] | None,
) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, tuple[str, ...]] = {}

    for raw_symbol in symbols or []:
        symbol = _normalise_symbol(raw_symbol)
        configured_aliases = SYMBOL_ALIASES.get(symbol, ())
        aliases[symbol] = tuple(
            dict.fromkeys((symbol.lower(), *configured_aliases))
        )

    return aliases


def _find_related_symbols(
    title: str,
    summary: str,
    symbols: list[str] | None,
) -> list[str]:
    combined = f"{title} {summary}".lower()
    aliases = _build_symbol_aliases(symbols)

    related: list[str] = []

    for symbol, symbol_aliases in aliases.items():
        if any(
            re.search(
                rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
                combined,
            )
            for alias in symbol_aliases
        ):
            related.append(symbol)

    return related


def _has_personal_finance_pattern(
    title: str,
    summary: str,
) -> bool:
    combined = f"{title} {summary}".lower()
    return any(
        pattern in combined
        for pattern in PERSONAL_FINANCE_PATTERNS
    )


def _calculate_relevance(
    title: str,
    summary: str,
    related_symbols: list[str],
) -> tuple[int, list[str]]:
    combined = f"{title} {summary}".lower()
    reasons: list[str] = []
    score = 0

    if related_symbols:
        score += 3
        reasons.append(
            f"匹配 watchlist：{', '.join(related_symbols)}"
        )

    keyword_matches = [
        keyword
        for keyword in MARKET_KEYWORDS
        if keyword in combined
    ]

    if keyword_matches:
        score += 1
        reasons.append(
            f"包含市場關鍵字：{', '.join(keyword_matches[:3])}"
        )

    if not reasons:
        reasons.append("沒有足夠的市場相關內容")

    return score, reasons


def _classify_sentiment(
    title: str,
    summary: str = "",
) -> tuple[str, str]:
    """
    標題權重高於摘要。

    只在出現較明確的市場語句時分類；
    一般生活或個人理財字眼不會直接判定為正面。
    """

    title_lower = title.lower()
    summary_lower = summary.lower()

    positive_title = sum(
        2 for keyword in POSITIVE_KEYWORDS
        if keyword in title_lower
    )
    positive_summary = sum(
        1 for keyword in POSITIVE_KEYWORDS
        if keyword in summary_lower
    )

    negative_title = sum(
        2 for keyword in NEGATIVE_KEYWORDS
        if keyword in title_lower
    )
    negative_summary = sum(
        1 for keyword in NEGATIVE_KEYWORDS
        if keyword in summary_lower
    )

    positive_score = positive_title + positive_summary
    negative_score = negative_title + negative_summary

    if negative_score > positive_score:
        return "negative", "市場負面關鍵字較多"

    if positive_score > negative_score:
        return "positive", "市場正面關鍵字較多"

    return "neutral", "沒有明確方向性市場訊號"


def _build_news_item(
    item: Any,
    source_name: str,
    symbols: list[str] | None = None,
) -> dict[str, Any] | None:
    title = clean_text(getattr(item, "title", ""))
    summary = clean_text(getattr(item, "summary", ""))
    link = str(getattr(item, "link", "") or "").strip()

    if not title:
        return None

    related_symbols = _find_related_symbols(
        title=title,
        summary=summary,
        symbols=symbols,
    )

    relevance_score, relevance_reasons = _calculate_relevance(
        title=title,
        summary=summary,
        related_symbols=related_symbols,
    )

    is_personal_finance = _has_personal_finance_pattern(
        title,
        summary,
    )

    # 個人理財文章必須有明確 watchlist 股票／指數匹配，
    # 否則不列入市場新聞。
    if is_personal_finance and not related_symbols:
        return None

    if relevance_score < 1:
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

    sentiment, sentiment_reason = _classify_sentiment(
        title,
        summary,
    )

    return {
        "title": title,
        "summary": (
            summary[:220]
            if summary
            else "No summary available."
        ),
        "link": link,
        "source": source_name,
        "published": published_display,
        "published_at": published_at,
        "age_hours": age_hours,
        "sentiment": sentiment,
        "sentiment_reason": sentiment_reason,
        "relevance_score": relevance_score,
        "relevance_reasons": relevance_reasons,
        "related_symbols": related_symbols,
    }


def fetch_rss_feed(
    feed_url: str,
    source_name: str,
    symbols: list[str] | None = None,
) -> list[dict[str, Any]]:
    """抓取單一 RSS Feed。"""

    response = requests.get(
        feed_url,
        headers={
            "User-Agent": "USshare/0.6 beginner-stock-analysis-app",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    entries: list[dict[str, Any]] = []

    for item in feed.entries[:20]:
        news_item = _build_news_item(
            item=item,
            source_name=source_name,
            symbols=symbols,
        )

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


def get_market_news(
    limit: int = 6,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    """
    取得市場新聞摘要。

    只保留：
    - 最近 NEWS_MAX_AGE_HOURS 小時新聞
    - 市場相關文章
    - 或明確匹配 watchlist 股票／指數的文章
    """

    now = time.time()
    normalized_symbols = tuple(
        _normalise_symbol(symbol)
        for symbol in symbols or []
    )
    cache_key = f"market_news:{','.join(normalized_symbols)}"

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
                symbols=list(normalized_symbols),
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
            -int(item.get("relevance_score", 0)),
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
        "watchlist_symbols": list(normalized_symbols),
        "filtered_count": max(
            0,
            len(all_items) - len(fresh_items),
        ),
        "disclaimer": (
            "新聞相關性和情緒只作為簡單摘要，"
            "不能代表市場趨勢或買賣建議。"
            "請閱讀原文並自行核對。"
        ),
    }

    _cache[cache_key] = {
        "timestamp": now,
        "data": result,
    }

    return result
