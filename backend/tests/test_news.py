from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app.services.news import (
    _build_news_item,
    _deduplicate_items,
)


def test_build_news_item_includes_source_and_time():
    item = SimpleNamespace(
        title="Technology stocks rally after strong earnings",
        summary="Markets react positively to company results.",
        link="https://example.com/story",
        published="Tue, 29 Sep 2026 12:00:00 GMT",
    )

    result = _build_news_item(item, "Test Source")

    assert result is not None
    assert result["source"] == "Test Source"
    assert result["published_at"] is not None
    assert result["age_hours"] is not None
    assert result["sentiment"] == "positive"


def test_irrelevant_news_is_filtered():
    item = SimpleNamespace(
        title="Celebrity announces a new project",
        summary="Entertainment news and lifestyle update.",
        link="https://example.com/entertainment",
        published="Tue, 29 Sep 2026 12:00:00 GMT",
    )

    result = _build_news_item(item, "Test Source")

    assert result is None


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


def test_duplicate_titles_are_removed():
    items = [
        {
            "title": "Market rally",
            "link": "https://example.com/one",
        },
        {
            "title": "Market rally",
            "link": "https://example.com/two",
        },
    ]

    result = _deduplicate_items(items)

    assert len(result) == 1
