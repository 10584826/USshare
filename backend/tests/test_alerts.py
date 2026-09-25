from backend.app.services.alerts import build_alert


def test_price_below_sma_creates_risk_alert():
    analysis = {
        "symbol": "TEST",
        "latest_price": 90,
        "sma50": 100,
        "rsi14": 50,
    }

    alert = build_alert(analysis)

    assert alert is not None
    assert alert["type"] == "risk"
    assert "50 日均線" in alert["reason"]


def test_oversold_creates_attention_alert():
    analysis = {
        "symbol": "TEST",
        "latest_price": 105,
        "sma50": 100,
        "rsi14": 30,
    }

    alert = build_alert(analysis)

    assert alert is not None
    assert alert["type"] == "attention"
    assert "RSI" in alert["reason"]


def test_overbought_creates_risk_alert():
    analysis = {
        "symbol": "TEST",
        "latest_price": 105,
        "sma50": 100,
        "rsi14": 75,
    }

    alert = build_alert(analysis)

    assert alert is not None
    assert alert["type"] == "risk"


def test_stable_stock_creates_positive_attention_alert():
    analysis = {
        "symbol": "TEST",
        "latest_price": 105,
        "sma50": 100,
        "rsi14": 55,
    }

    alert = build_alert(analysis)

    assert alert is not None
    assert alert["type"] == "attention"
    assert alert["severity"] == "info"
