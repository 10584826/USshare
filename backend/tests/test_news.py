from types import SimpleNamespace

from backend.app.services.news import (
    _build_news_item,
    _classify_sentiment,
    _deduplicate_items,
)


def test_stock_news_gets_symbol_relevance():
    item = SimpleNamespace(
        title="Apple reports strong earnings growth",
        summary="Apple revenue beats expectations.",
        link="https://example.com/apple",
        published="Tue, 29 Sep 2026 12:00:00 GMT",
    )

    result = _build_news_item(
        item,
        "Test Source",
        symbols=["AAPL"],
    )

    assert result is not None
    assert result["related_symbols"] == ["AAPL"]
    assert result["relevance_score"] >= 3
    assert result["sentiment"] == "positive"


def test_personal_finance_article_is_filtered():
    item = SimpleNamespace(
        title=(
            "I have $400,000 in equity: should I sell my house "
            "because of dangerous stairs?"
        ),
        summary=(
            "The advice says not to sell because I have "
            "a low-interest-rate mortgage."
        ),
        link="https://example.com/personal-finance",
        published="Wed, 30 Sep 2026 01:00:00 GMT",
    )

    result = _build_news_item(
        item,
        "Test Source",
        symbols=["SPY", "QQQ"],
    )

    assert result is None


def test_generic_personal_finance_text_is_not_positive():
    sentiment, reason = _classify_sentiment(
        "I am 80. Should I sell my house?",
        "My mortgage rate is low.",
    )

    assert sentiment == "neutral"
    assert reason == "沒有明確方向性市場訊號"


def test_market_news_can_be_neutral():
    item = SimpleNamespace(
        title="Markets await the Federal Reserve rate decision",
        summary="Investors are watching the next policy announcement.",
        link="https://example.com/fed",
        published="Tue, 29 Sep 2026 12:00:00 GMT",
    )

    result = _build_news_item(
        item,
        "Test Source",
        symbols=["SPY"],
    )

    assert result is not None
    assert result["sentiment"] == "neutral"
    assert result["relevance_score"] >= 1


def test_duplicate_links_are_removed():
    items = [
        {
            "title": "Market rally",
            "link": "https://example.com/story",
        },
        {
            "title": "Market rally updated",
            "link": "https://example.com/story",
        },
    ]

    result = _deduplicate_items(items)

    assert len(result) == 1
