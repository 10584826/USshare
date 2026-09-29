from backend.app.services.alerts import build_alert


def test_price_below_sma_creates_risk_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 90,
            "sma50": 100,
            "rsi14": 50,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": 0.0,
            "trend_direction": "below",
            "trend_days": 2,
        }
    )

    assert alert is not None
    assert alert["type"] == "risk"
    assert alert["score"] == -2
    assert "50 日均線" in alert["reason"]


def test_daily_positive_change_adds_positive_score():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 55,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": 2.5,
            "trend_direction": "above",
            "trend_days": 2,
        }
    )

    assert alert is not None
    assert alert["score"] == 2
    assert "單日上升 2.50%" in alert["factors"]


def test_daily_negative_change_adds_risk_score():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 95,
            "sma50": 100,
            "rsi14": 50,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": -2.5,
            "trend_direction": "below",
            "trend_days": 2,
        }
    )

    assert alert is not None
    assert alert["score"] == -3
    assert alert["type"] == "risk"
    assert "單日下跌 2.50%" in alert["factors"]


def test_long_above_sma_trend_adds_positive_score():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 55,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": 0.0,
            "trend_direction": "above",
            "trend_days": 7,
        }
    )

    assert alert is not None
    assert alert["score"] == 2
    assert alert["trend_days"] == 7
    assert "價格連續 7 天高於 50 日均線" in alert["factors"]


def test_long_below_sma_trend_adds_risk_score():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 95,
            "sma50": 100,
            "rsi14": 50,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": 0.0,
            "trend_direction": "below",
            "trend_days": 6,
        }
    )

    assert alert is not None
    assert alert["score"] == -3
    assert alert["type"] == "risk"
    assert "價格連續 6 天低於或等於 50 日均線" in alert["factors"]


def test_overbought_stock_creates_risk_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 75,
            "volume_ratio_20d": 1.0,
            "daily_change_percent": 0.0,
            "trend_direction": "above",
            "trend_days": 2,
        }
    )

    assert alert is not None
    assert alert["type"] == "risk"
    assert alert["score"] == -2
    assert alert["signal_strength"] == "medium"


def test_missing_required_data_creates_information_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": None,
            "sma50": 100,
            "rsi14": 55,
            "daily_change_percent": None,
            "trend_direction": "unknown",
            "trend_days": 0,
        }
    )

    assert alert is not None
    assert alert["type"] == "information"
    assert alert["score"] == 0
    assert alert["signal_strength"] == "low"
    assert alert["is_actionable"] is False
