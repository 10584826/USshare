from backend.app.services.alerts import build_alert


def test_price_below_sma_creates_risk_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 90,
            "sma50": 100,
            "rsi14": 50,
            "volume_ratio_20d": 1.0,
        }
    )

    assert alert is not None
    assert alert["type"] == "risk"
    assert alert["score"] == -2
    assert alert["signal_strength"] == "medium"
    assert "50 日均線" in alert["reason"]


def test_oversold_stock_can_create_attention_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 30,
            "volume_ratio_20d": 1.0,
        }
    )

    assert alert is not None
    assert alert["type"] == "attention"
    assert alert["score"] == 2
    assert alert["signal_strength"] == "medium"
    assert "RSI" in alert["reason"]


def test_overbought_stock_creates_risk_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 75,
            "volume_ratio_20d": 1.0,
        }
    )

    assert alert is not None
    assert alert["type"] == "risk"
    assert alert["score"] == -1
    assert alert["signal_strength"] == "low"


def test_high_volume_increases_score():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": 105,
            "sma50": 100,
            "rsi14": 55,
            "volume_ratio_20d": 1.5,
        }
    )

    assert alert is not None
    assert alert["type"] == "attention"
    assert alert["score"] == 2
    assert "成交量高於 20 日平均" in alert["factors"]


def test_missing_required_data_creates_information_alert():
    alert = build_alert(
        {
            "symbol": "TEST",
            "latest_price": None,
            "sma50": 100,
            "rsi14": 55,
        }
    )

    assert alert is not None
    assert alert["type"] == "information"
    assert alert["score"] == 0
    assert alert["signal_strength"] == "low"
    assert alert["is_actionable"] is False
