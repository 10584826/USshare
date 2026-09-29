from backend.app.cron_scan import build_data_health


def test_data_health_is_ok_when_sources_are_healthy():
    health = build_data_health(
        market={
            "indices": [
                {"symbol": "SPY", "status": "bullish"},
                {"symbol": "QQQ", "status": "neutral"},
            ]
        },
        watchlist={
            "scanned_count": 2,
            "errors": [],
        },
        news={
            "top_stories": [{"title": "Market update"}],
            "errors": [],
        },
        generated_at="2026-09-29T00:00:00+00:00",
    )

    assert health["status"] == "ok"
    assert health["is_stale"] is False
    assert health["total_error_count"] == 0


def test_data_health_is_partial_when_news_fails():
    health = build_data_health(
        market={
            "indices": [
                {"symbol": "SPY", "status": "bullish"},
            ]
        },
        watchlist={
            "scanned_count": 1,
            "errors": [],
        },
        news={
            "top_stories": [],
            "errors": ["RSS unavailable"],
        },
        generated_at="2026-09-29T00:00:00+00:00",
    )

    assert health["status"] == "partial"
    assert health["is_stale"] is True
    assert health["news"]["status"] == "partial"


def test_data_health_is_error_when_all_market_data_fails():
    health = build_data_health(
        market={
            "indices": [
                {
                    "symbol": "SPY",
                    "status": "unknown",
                    "error": "provider unavailable",
                }
            ]
        },
        watchlist={
            "scanned_count": 0,
            "errors": ["SPY unavailable"],
        },
        news={
            "top_stories": [],
            "errors": [],
        },
        generated_at="2026-09-29T00:00:00+00:00",
    )

    assert health["status"] == "error"
    assert health["is_stale"] is True
    assert health["market"]["status"] == "error"
